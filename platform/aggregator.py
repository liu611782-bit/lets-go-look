"""聚合服务：多源检索合并、跨源去重、排序、详情路由与错误降级。

设计要点：
- 任一来源失败不影响整体结果，失败信息进入 `per_source`，整体标记 `degraded`；
- DISABLED 来源默认不参与聚合，显式请求时在 `per_source` 中标注 SOURCE_DISABLED；
- 检索结果按 TTL 缓存，缓存键包含关键词、类型、分页与来源集合。
"""

from __future__ import annotations

import threading
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from platform.adapters.base import SourceAdapter
from platform.bootstrap import default_registry
from platform.errors import BadRequest, SourceDisabled, normalize_exception
from platform.models import MediaItem, MediaType, ResolvedSource, SourceStatus
from platform.registry import Registry
from platform.serialization import (
    chapter_to_dict,
    episode_to_dict,
    item_to_dict,
    meta_to_dict,
    resolved_to_dict,
)

DEFAULT_PAGE_SIZE = 20


# ---------------------------------------------------------------- 缓存


class TTLCache:
    """极简线程安全 TTL 缓存，避免为骨架引入外部依赖。"""

    def __init__(self, ttl_seconds: float = 60.0, max_entries: int = 512) -> None:
        self._ttl = ttl_seconds
        self._max = max_entries
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at < time.time():
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if len(self._store) >= self._max:
                # 简单淘汰：清掉过期项，仍超限则丢掉最早插入的一项
                now = time.time()
                expired = [k for k, (exp, _) in self._store.items() if exp < now]
                for k in expired:
                    self._store.pop(k, None)
                if len(self._store) >= self._max:
                    self._store.pop(next(iter(self._store)), None)
            self._store[key] = (time.time() + self._ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


# ---------------------------------------------------------------- 数据结构


@dataclass(frozen=True)
class SourceRef:
    """聚合结果中的单个来源引用。"""

    adapter_id: str
    display_name: str
    external_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "display_name": self.display_name,
            "external_id": self.external_id,
        }


@dataclass(frozen=True)
class AggregatedItem:
    """跨源合并后的作品条目。"""

    key: str
    title: str
    media_type: MediaType
    primary: MediaItem
    sources: Tuple[SourceRef, ...]

    def to_dict(self) -> Dict[str, Any]:
        payload = item_to_dict(self.primary)
        payload["sources"] = [ref.to_dict() for ref in self.sources]
        payload["source_count"] = len(self.sources)
        return payload


@dataclass
class SearchOutcome:
    query: str
    media_type: Optional[MediaType]
    page: int
    page_size: int
    total: int
    items: List[AggregatedItem] = field(default_factory=list)
    per_source: List[Dict[str, Any]] = field(default_factory=list)
    degraded: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "media_type": self.media_type.value if self.media_type else None,
            "page": self.page,
            "page_size": self.page_size,
            "total": self.total,
            "degraded": self.degraded,
            "items": [item.to_dict() for item in self.items],
            "per_source": self.per_source,
        }


# ---------------------------------------------------------------- 去重与排序


_TITLE_NOISE = set(" \t\r\n\u3000·•－—_-:：,，.。!！?？'\u201c\u201d\u2018\u2019()（）[]【】/\\|、；;\“\u201d\u2018\u2019")


def normalize_title(title: str) -> str:
    """标题归一化：全角转半角、去标点空白、忽略大小写，用于跨源聚类。"""
    text = unicodedata.normalize("NFKC", title or "")
    return "".join(ch for ch in text if ch not in _TITLE_NOISE).casefold()


def _rank_key(item: AggregatedItem) -> Tuple[float, int, str]:
    return (-(item.primary.rating or 0.0), -len(item.sources), item.title)


# ---------------------------------------------------------------- 聚合服务


class Aggregator:
    """对外统一入口：sources / health / search / detail / resolve。"""

    def __init__(
        self,
        registry: Optional[Registry] = None,
        cache_ttl: float = 60.0,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> None:
        self.registry = registry or default_registry
        self.cache = TTLCache(ttl_seconds=cache_ttl)
        self.page_size = page_size

    # ---- 元信息 -----------------------------------------------------

    def sources(self) -> List[Dict[str, Any]]:
        return [meta_to_dict(meta) for meta in self.registry.metas()]

    def health(self) -> Dict[str, Any]:
        metas = self.registry.metas()
        counts = {status.value: 0 for status in SourceStatus}
        for meta in metas:
            counts[meta.status.value] += 1
        return {
            "status": "ok",
            "source_count": len(metas),
            "by_status": counts,
            "sources": [meta_to_dict(meta) for meta in metas],
            "disclaimer": "DISABLED 来源未授权，不会发起任何请求；STUB 来源返回 SOURCE_NOT_READY。",
        }

    # ---- 检索 -------------------------------------------------------

    def search(
        self,
        query: str,
        media_type: Optional[MediaType] = None,
        page: int = 1,
        sources: Optional[Sequence[str]] = None,
    ) -> SearchOutcome:
        if not query or not query.strip():
            raise BadRequest("query 不能为空")
        if page < 1:
            raise BadRequest("page 需为大于 0 的整数")
        if media_type is not None and not isinstance(media_type, MediaType):
            raise BadRequest(f"不支持的 media_type：{media_type}")

        cache_key = f"search|{query.strip()}|{media_type}|{page}|{','.join(sorted(sources or ())}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        selected = self.registry.resolve_selection(sources, media_type=media_type)
        records: List[Dict[str, Any]] = []
        collected: List[Tuple[str, MediaItem]] = []

        for adapter in selected:
            meta = adapter.meta()
            if meta.status == SourceStatus.DISABLED:
                records.append(
                    {
                        "adapter_id": meta.adapter_id,
                        "display_name": meta.display_name,
                        "status": meta.status.value,
                        "count": 0,
                        "error": SourceDisabled(
                            "来源未授权，已禁用", source=meta.adapter_id
                        ).to_dict(),
                    }
                )
                continue
            try:
                items = list(adapter.search(query=query, media_type=media_type, page=page))
            except Exception as exc:  # noqa: BLE001 — 逐源隔离，避免单点失败拖垮聚合
                error = normalize_exception(exc, source=meta.adapter_id)
                records.append(
                    {
                        "adapter_id": meta.adapter_id,
                        "display_name": meta.display_name,
                        "status": meta.status.value,
                        "count": 0,
                        "error": error.to_dict(),
                    }
                )
                continue
            records.append(
                {
                    "adapter_id": meta.adapter_id,
                    "display_name": meta.display_name,
                    "status": meta.status.value,
                    "count": len(items),
                    "error": None,
                }
            )
            collected.extend((meta.display_name, item) for item in items)

        grouped = self._merge(collected)
        total = len(grouped)
        start = (page - 1) * self.page_size
        page_items = grouped[start : start + self.page_size]

        outcome = SearchOutcome(
            query=query.strip(),
            media_type=media_type,
            page=page,
            page_size=self.page_size,
            total=total,
            items=page_items,
            per_source=records,
            degraded=any(record["error"] for record in records),
        )
        self.cache.set(cache_key, outcome)
        return outcome

    @staticmethod
    def _merge(entries: Sequence[Tuple[str, MediaItem]]) -> List[AggregatedItem]:
        buckets: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for display_name, item in entries:
            key = (item.media_type.value, normalize_title(item.title))
            bucket = buckets.setdefault(key, {"primary": item, "refs": []})
            if (item.rating or 0.0) > (bucket["primary"].rating or 0.0):
                bucket["primary"] = item
            bucket["refs"].append(
                SourceRef(
                    adapter_id=item.source,
                    display_name=display_name,
                    external_id=item.external_id,
                )
            )

        result: List[AggregatedItem] = []
        for (media_type_value, norm_title), bucket in buckets.items():
            refs = tuple(sorted(bucket["refs"], key=lambda r: r.adapter_id))
            primary: MediaItem = bucket["primary"]
            result.append(
                AggregatedItem(
                    key=f"{media_type_value}:{norm_title}",
                    title=primary.title,
                    media_type=primary.media_type,
                    primary=primary,
                    sources=refs,
                )
            )
        result.sort(key=_rank_key)
        return result

    # ---- 详情 -------------------------------------------------------

    def _adapter(self, source: str) -> SourceAdapter:
        adapter = self.registry.get(source)
        meta = adapter.meta()
        if meta.status == SourceStatus.DISABLED:
            raise SourceDisabled(
                f"来源 {meta.display_name} 未授权，已禁用；不提供检索 / 详情 / 解析",
                source=meta.adapter_id,
            )
        return adapter

    def detail(self, source: str, external_id: str) -> Dict[str, Any]:
        if not source or not external_id:
            raise BadRequest("source 与 id 均为必填")
        adapter = self._adapter(source)
        try:
            item = adapter.detail(external_id)
            episodes = list(adapter.episodes(external_id))
            chapters = list(adapter.chapters(external_id))
        except Exception as exc:  # noqa: BLE001
            raise normalize_exception(exc, source=source) from exc
        return {
            "source": source,
            "item": item_to_dict(item),
            "episodes": [episode_to_dict(ep) for ep in episodes],
            "chapters": [chapter_to_dict(ch) for ch in chapters],
        }

    # ---- 解析 -------------------------------------------------------

    def resolve(
        self,
        source: str,
        external_id: str,
        episode_or_chapter_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not source or not external_id:
            raise BadRequest("source 与 id 均为必填")
        adapter = self._adapter(source)
        try:
            resolved: ResolvedSource = adapter.resolve(external_id, episode_or_chapter_id)
        except Exception as exc:  # noqa: BLE001
            raise normalize_exception(exc, source=source) from exc
        payload = resolved_to_dict(resolved)
        payload["source"] = source
        payload["external_id"] = external_id
        payload["episode_or_chapter_id"] = episode_or_chapter_id
        return payload


default_aggregator = Aggregator()
