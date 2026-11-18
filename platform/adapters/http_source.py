"""配置驱动的通用 HTTP 适配器。

适用场景：已取得某来源的接口文档与授权，但不想为每个来源写一份 Python 适配器。
接口地址、字段映射、分页与解析路径全部来自配置（`platform/config.py`），
代码里**不硬编码任何上游地址**。

约束：
- 只支持 GET；
- base_url 的主机自动进入 HTTP 客户端白名单；
- 缺少必需端点时抛 NotImplementedError（→ SOURCE_NOT_READY），而不是猜测接口。
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from platform.config import SourceConfig, runtime_headers
from platform.errors import BadRequest, NotFound, SourceNotReady
from platform.http_client import HttpClient, pick
from platform.models import (
    Chapter,
    Episode,
    MediaItem,
    MediaType,
    ResolvedSource,
    SourceMeta,
    SourceStatus,
)

from .base import SourceAdapter

DEFAULT_FIELDS: Dict[str, str] = {
    "id": "id",
    "title": "title",
    "cover_url": "cover",
    "summary": "summary",
    "author": "author",
    "status": "status",
    "rating": "rating",
}


class ConfiguredHttpAdapter(SourceAdapter):
    """按配置对接某个来源的公开 / 已授权接口。"""

    def __init__(self, config: SourceConfig) -> None:
        self.config = config
        self.adapter_id = config.adapter_id
        self.client = HttpClient(
            allowed_hosts=[config.host],
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
            min_interval_seconds=config.min_interval_seconds,
        )
        self._headers = runtime_headers(config)
        self._fields = {**DEFAULT_FIELDS, **config.fields}

    # ---- 元信息 -----------------------------------------------------

    def meta(self) -> SourceMeta:
        # 能检索 + 能取详情即视为可用；解析能力缺失时由 resolve 单独返回 SOURCE_NOT_READY
        ready = self.config.enabled and self._has_all("search", "detail")
        return SourceMeta(
            adapter_id=self.adapter_id,
            display_name=self.config.display_name,
            media_types=tuple(MediaType(mt) for mt in self.config.media_types if mt in MediaType._value2member_map_),
            status=SourceStatus.ACTIVE if ready else SourceStatus.STUB,
            upstream_repo=self.config.upstream_repo,
            license=self.config.license_name,
            note=self.config.note
            or (
                "配置驱动；接口地址与字段映射见平台配置，不硬编码在代码中。"
                if self.config.enabled
                else "配置存在但未启用（enabled=false），确认授权后再开启。"
            ),
        )

    def _has_all(self, *names: str) -> bool:
        return all(name in self.config.endpoints for name in names)

    # ---- 请求 -------------------------------------------------------

    def _request(self, endpoint_name: str, **placeholders: object) -> object:
        endpoint = self.config.endpoints.get(endpoint_name)
        if endpoint is None:
            raise SourceNotReady(f"来源 {self.adapter_id} 未配置 {endpoint_name} 端点")
        path = endpoint.path.format(**{k: str(v) for k, v in placeholders.items()})
        params = {
            key: value.format(**{k: str(v) for k, v in placeholders.items()})
            for key, value in endpoint.params.items()
        }
        url = HttpClient.build_url(self.config.base_url, path, params)
        return self.client.get_json(url, headers=self._headers).payload

    # ---- 映射 -------------------------------------------------------

    def _to_item(self, raw: object) -> MediaItem:
        if not isinstance(raw, dict):
            raise BadRequest(f"{self.adapter_id}: 条目不是对象")
        external_id = str(pick(raw, self._fields["id"], "") or "")
        title = str(pick(raw, self._fields["title"], "") or "")
        if not external_id or not title:
            raise BadRequest(f"{self.adapter_id}: 条目缺少 id 或 title")

        rating_raw = pick(raw, self._fields["rating"])
        try:
            rating = float(rating_raw) if rating_raw is not None else None
        except (TypeError, ValueError):
            rating = None

        return MediaItem(
            source=self.adapter_id,
            external_id=external_id,
            title=title,
            media_type=MediaType(self.config.media_types[0]) if self.config.media_types else MediaType.DRAMA,
            cover_url=pick(raw, self._fields["cover_url"]),
            summary=pick(raw, self._fields["summary"]),
            author=pick(raw, self._fields["author"]),
            status=pick(raw, self._fields["status"]),
            rating=rating,
        )

    def _list(self, payload: object, path: str) -> List[object]:
        value = pick(payload, path)
        if value is None:
            return []
        if not isinstance(value, list):
            raise BadRequest(f"{self.adapter_id}: {path} 不是数组")
        return value

    # ---- 契约实现 ---------------------------------------------------

    def search(
        self,
        query: str,
        media_type: Optional[MediaType] = None,
        page: int = 1,
    ) -> Sequence[MediaItem]:
        if not query or not query.strip():
            raise BadRequest("query 不能为空", source=self.adapter_id)
        payload = self._request("search", query=query.strip(), page=page)
        return [self._to_item(raw) for raw in self._list(payload, self.config.search_items_path)]

    def detail(self, external_id: str) -> MediaItem:
        payload = self._request("detail", id=external_id)
        item_path = self.config.fields.get("detail_item_path", "data")
        node = pick(payload, item_path)
        if node is None:
            raise NotFound(f"{self.adapter_id}: 未找到 {external_id}", source=self.adapter_id)
        return self._to_item(node)

    def episodes(self, external_id: str) -> Sequence[Episode]:
        if "episodes" not in self.config.endpoints:
            raise SourceNotReady(f"来源 {self.adapter_id} 未配置 episodes 端点")
        payload = self._request("episodes", id=external_id)
        result: List[Episode] = []
        for index, raw in enumerate(self._list(payload, self.config.episodes_path), start=1):
            if not isinstance(raw, dict):
                continue
            result.append(
                Episode(
                    external_id=str(raw.get("id") or raw.get("episode_id") or index),
                    index=int(raw.get("index") or index),
                    title=str(raw.get("title") or raw.get("name") or f"第 {index} 集"),
                    duration_seconds=raw.get("duration_seconds") or raw.get("duration"),
                )
            )
        return result

    def chapters(self, external_id: str) -> Sequence[Chapter]:
        if "chapters" not in self.config.endpoints:
            raise SourceNotReady(f"来源 {self.adapter_id} 未配置 chapters 端点")
        payload = self._request("chapters", id=external_id)
        result: List[Chapter] = []
        for index, raw in enumerate(self._list(payload, self.config.chapters_path), start=1):
            if not isinstance(raw, dict):
                continue
            result.append(
                Chapter(
                    external_id=str(raw.get("id") or raw.get("chapter_id") or index),
                    index=int(raw.get("index") or index),
                    title=str(raw.get("title") or raw.get("name") or f"第 {index} 章"),
                    word_count=raw.get("word_count"),
                )
            )
        return result

    def resolve(self, external_id: str, episode_or_chapter_id: Optional[str] = None) -> ResolvedSource:
        payload = self._request("resolve", id=external_id, episode=episode_or_chapter_id or "")
        url = pick(payload, self.config.resolve_url_field)
        if not url:
            raise NotFound(f"{self.adapter_id}: 未返回可解析地址", source=self.adapter_id)
        return ResolvedSource(
            url=str(url),
            media_type=MediaType(self.config.media_types[0]) if self.config.media_types else MediaType.DRAMA,
            quality=pick(payload, "data.quality"),
            format=pick(payload, "data.format"),
            headers={},
            expires_in_seconds=pick(payload, "data.expires_in_seconds"),
            note=f"来源 {self.config.display_name} 授权接口返回。",
        )
