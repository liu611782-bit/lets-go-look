"""适配器注册表：实例缓存 + 按状态 / 内容类型筛选。

DISABLED 来源保留在注册表里以便对外展示“存在但未授权”，
但不会进入默认聚合检索，显式请求时返回 SOURCE_DISABLED。
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional, Sequence

from platform.adapters import ADAPTERS, AdapterFactory
from platform.adapters.base import SourceAdapter
from platform.errors import BadRequest, NotFound
from platform.models import MediaType, SourceMeta, SourceStatus


class Registry:
    """线程安全的适配器注册表。"""

    def __init__(self, factories: Optional[Dict[str, AdapterFactory]] = None) -> None:
        self._factories: Dict[str, AdapterFactory] = dict(ADAPTERS if factories is None else factories)
        self._instances: Dict[str, SourceAdapter] = {}
        self._lock = threading.Lock()

    # ---- 注册与获取 -------------------------------------------------

    def register(self, adapter_id: str, factory: AdapterFactory) -> None:
        if not adapter_id:
            raise BadRequest("adapter_id 不能为空")
        with self._lock:
            self._factories[adapter_id] = factory
            self._instances.pop(adapter_id, None)

    def ids(self) -> List[str]:
        with self._lock:
            return sorted(self._factories)

    def get(self, adapter_id: str) -> SourceAdapter:
        with self._lock:
            if adapter_id in self._instances:
                return self._instances[adapter_id]
            factory = self._factories.get(adapter_id)
            if factory is None:
                raise NotFound(f"未知来源：{adapter_id}")
            instance = factory()
            self._instances[adapter_id] = instance
            return instance

    def all(self) -> List[SourceAdapter]:
        return [self.get(aid) for aid in self.ids()]

    # ---- 元信息 -----------------------------------------------------

    def metas(self) -> List[SourceMeta]:
        metas = [adapter.meta() for adapter in self.all()]
        return sorted(metas, key=lambda m: (m.status != SourceStatus.ACTIVE, m.adapter_id))

    def meta(self, adapter_id: str) -> SourceMeta:
        return self.get(adapter_id).meta()

    # ---- 筛选 -------------------------------------------------------

    def enabled(
        self,
        media_type: Optional[MediaType] = None,
        include_stub: bool = True,
    ) -> List[SourceAdapter]:
        """返回可用于聚合的适配器；DISABLED 永不返回。"""
        result: List[SourceAdapter] = []
        for adapter in self.all():
            meta = adapter.meta()
            if meta.status == SourceStatus.DISABLED:
                continue
            if not include_stub and meta.status != SourceStatus.ACTIVE:
                continue
            if media_type is not None and media_type not in meta.media_types:
                continue
            result.append(adapter)
        return result

    def resolve_selection(
        self,
        sources: Optional[Sequence[str]],
        media_type: Optional[MediaType] = None,
    ) -> List[SourceAdapter]:
        """把调用方指定的 sources 解析为适配器列表；未指定时取默认可用集合。"""
        if not sources:
            return self.enabled(media_type=media_type)
        selected: List[SourceAdapter] = []
        for adapter_id in sources:
            if adapter_id not in self._factories:
                raise BadRequest(f"未知来源：{adapter_id}")
            selected.append(self.get(adapter_id))
        return selected


default_registry = Registry()
