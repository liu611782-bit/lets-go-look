"""适配器抽象接口：每个上游来源实现同一套契约。

实现约束（见 docs/ARCHITECTURE.md 与 docs/COMPLIANCE.md）：
- 只对接公开 / 已授权的后端接口；
- 不向上游传递仓库内的任何凭证；鉴权信息由服务端会话注入；
- 返回值必须归一化到 platform.models 中的领域模型。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence

from platform.models import Chapter, Episode, MediaItem, MediaType, ResolvedSource, SourceMeta


class SourceAdapter(ABC):
    """所有来源适配器的基类。"""

    @abstractmethod
    def meta(self) -> SourceMeta:
        """返回来源元信息与接入状态。"""

    @abstractmethod
    def search(
        self,
        query: str,
        media_type: Optional[MediaType] = None,
        page: int = 1,
    ) -> Sequence[MediaItem]:
        """按关键词检索，返回归一化后的内容列表。"""

    @abstractmethod
    def detail(self, external_id: str) -> MediaItem:
        """取详情；分集 / 分章列表通过下方 episodes / chapters 获取。"""

    def episodes(self, external_id: str) -> Sequence[Episode]:
        """短剧 / 影视分集；不支持的来源返回空序列。"""
        return ()

    def chapters(self, external_id: str) -> Sequence[Chapter]:
        """小说章节；不支持的来源返回空序列。"""
        return ()

    @abstractmethod
    def resolve(self, external_id: str, episode_or_chapter_id: Optional[str] = None) -> ResolvedSource:
        """解析出可播放 / 可阅读地址。"""
