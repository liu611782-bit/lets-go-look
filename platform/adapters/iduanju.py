"""i短剧适配器（骨架）。

上游：https://github.com/my-name-is-alan/iDuanJu （GPL-3.0）
对应 APK：base_5.apk（app.iduanju，本地 1.5.10，上游已 1.5.14-android）

合规提示：
- GPL-3.0 具有传染性；本平台与其代码的链接 / 衍生边界需经法律复核，
  建议以独立进程或明确接口隔离（见 docs/COMPLIANCE.md）。
"""

from __future__ import annotations

from typing import Optional, Sequence

from platform.models import (
    Episode,
    MediaItem,
    MediaType,
    ResolvedSource,
    SourceMeta,
    SourceStatus,
)

from .base import SourceAdapter


class IDuanjuAdapter(SourceAdapter):
    """i短剧来源适配器。当前为骨架。"""

    ADAPTER_ID = "iduanju"

    def meta(self) -> SourceMeta:
        return SourceMeta(
            adapter_id=self.ADAPTER_ID,
            display_name="i短剧",
            media_types=(MediaType.DRAMA, MediaType.VIDEO),
            status=SourceStatus.STUB,
            upstream_repo="https://github.com/my-name-is-alan/iDuanJu",
            license="GPL-3.0",
            note="骨架：GPL 边界复核后再实现接口对接。",
        )

    def search(
        self,
        query: str,
        media_type: Optional[MediaType] = None,
        page: int = 1,
    ) -> Sequence[MediaItem]:
        raise NotImplementedError("待实现：检索接口对接与结果归一化")

    def detail(self, external_id: str) -> MediaItem:
        raise NotImplementedError("待实现：详情与分集列表")

    def episodes(self, external_id: str) -> Sequence[Episode]:
        raise NotImplementedError("待实现：分集列表")

    def resolve(self, external_id: str, episode_or_chapter_id: Optional[str] = None) -> ResolvedSource:
        raise NotImplementedError("待实现：播放地址解析")
