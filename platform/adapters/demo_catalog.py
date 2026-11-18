"""本地演示目录适配器（ACTIVE）。

用途：在未接入任何真实上游的情况下，跑通「多源聚合 → 详情 → 解析」全链路，
便于验证聚合服务、HTTP 接口与前端联调。

数据来源：`platform/data/demo_catalog.json`，由本仓库自行编写的虚构目录
（CC0-1.0），不含任何真实作品、上游接口或版权内容。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from platform.errors import BadRequest, NotFound
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

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "demo_catalog.json"


@lru_cache(maxsize=1)
def _load_catalog() -> Dict[str, Any]:
    with DATA_FILE.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload.get("items"), list):
        raise ValueError("demo_catalog.json 缺少 items 列表")
    return payload


class DemoCatalogAdapter(SourceAdapter):
    """自造演示目录：只读取仓库内置 JSON，不发起任何网络请求。"""

    ADAPTER_ID = "demo_catalog"

    def meta(self) -> SourceMeta:
        payload = _load_catalog()
        return SourceMeta(
            adapter_id=self.ADAPTER_ID,
            display_name="演示目录（自造数据）",
            media_types=(MediaType.DRAMA, MediaType.VIDEO, MediaType.NOVEL),
            status=SourceStatus.ACTIVE,
            upstream_repo=None,
            license=payload.get("license", "CC0-1.0"),
            note="虚构演示数据，仅用于验证聚合主链路；不接入任何真实上游。",
        )

    # ---- 内部工具 ---------------------------------------------------

    @staticmethod
    def _items() -> List[Dict[str, Any]]:
        return _load_catalog()["items"]

    @staticmethod
    def _to_item(raw: Dict[str, Any]) -> MediaItem:
        return MediaItem(
            source=DemoCatalogAdapter.ADAPTER_ID,
            external_id=str(raw["id"]),
            title=str(raw["title"]),
            media_type=MediaType(raw["media_type"]),
            cover_url=None,
            summary=raw.get("summary"),
            author=raw.get("author"),
            status=raw.get("status"),
            rating=raw.get("rating"),
            extra={"demo": True},
        )

    def _find(self, item_id: str) -> Dict[str, Any]:
        for raw in self._items():
            if str(raw.get("id")) == str(item_id):
                return raw
        raise NotFound(f"演示目录中不存在：{item_id}", source=self.ADAPTER_ID)

    # ---- 契约实现 ---------------------------------------------------

    def search(
        self,
        query: str,
        media_type: Optional[MediaType] = None,
        page: int = 1,
    ) -> Sequence[MediaItem]:
        if not query or not query.strip():
            raise BadRequest("query 不能为空", source=self.ADAPTER_ID)
        needle = query.strip().casefold()
        matched: List[MediaItem] = []
        for raw in self._items():
            item = self._to_item(raw)
            if media_type is not None and item.media_type != media_type:
                continue
            haystack = " ".join(
                str(part) for part in (item.title, item.author, item.summary) if part
            ).casefold()
            if needle in haystack:
                matched.append(item)
        matched.sort(key=lambda i: (-(i.rating or 0.0), i.title))
        page_size = 20
        start = (page - 1) * page_size
        return matched[start : start + page_size]

    def detail(self, external_id: str) -> MediaItem:
        return self._to_item(self._find(external_id))

    def episodes(self, external_id: str) -> Sequence[Episode]:
        raw = self._find(external_id)
        return [
            Episode(
                external_id=str(ep["id"]),
                index=int(ep["index"]),
                title=str(ep["title"]),
                duration_seconds=ep.get("duration_seconds"),
                is_finished=raw.get("status") == "完结",
            )
            for ep in raw.get("episodes", [])
        ]

    def chapters(self, external_id: str) -> Sequence[Chapter]:
        raw = self._find(external_id)
        return [
            Chapter(
                external_id=str(ch["id"]),
                index=int(ch["index"]),
                title=str(ch["title"]),
                word_count=ch.get("word_count"),
            )
            for ch in raw.get("chapters", [])
        ]

    def resolve(self, external_id: str, episode_or_chapter_id: Optional[str] = None) -> ResolvedSource:
        raw = self._find(external_id)
        media_type = MediaType(raw["media_type"])
        segment = episode_or_chapter_id or "full"
        alive = {str(ep["id"]) for ep in raw.get("episodes", [])} | {
            str(ch["id"]) for ch in raw.get("chapters", [])
        }
        if episode_or_chapter_id is not None and segment not in alive:
            raise NotFound(
                f"分集 / 章节不存在：{episode_or_chapter_id}",
                source=self.ADAPTER_ID,
            )
        scheme = "m3u8" if media_type in (MediaType.DRAMA, MediaType.VIDEO) else "txt"
        return ResolvedSource(
            url=f"https://example.com/demo-media/{external_id}/{segment}.{scheme}",
            media_type=media_type,
            quality="demo" if scheme == "m3u8" else None,
            format=scheme,
            headers={},
            expires_in_seconds=0,
            note="演示占位地址，不指向任何真实内容；接入真实来源时由适配器返回上游授权地址。",
        )
