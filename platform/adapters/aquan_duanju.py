"""阿圈短剧适配器（骨架）。

上游：https://github.com/wjsqqj/aquan-duanju （Apache-2.0）
对应 APK：base_1.apk / base_2.apk / base_3.apk（com.aquan.duanju，历史版本）

合规提示：
- 复用上游代码时保留 Apache-2.0 LICENSE 与 NOTICE；
- 仅对接公开 / 已授权接口，不绕过登录、风控或加密保护。
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


class AquanDuanjuAdapter(SourceAdapter):
    """阿圈短剧来源适配器。当前为骨架，接口对接待实现。"""

    ADAPTER_ID = "aquan_duanju"

    def meta(self) -> SourceMeta:
        return SourceMeta(
            adapter_id=self.ADAPTER_ID,
            display_name="阿圈短剧",
            media_types=(MediaType.DRAMA, MediaType.VIDEO),
            status=SourceStatus.STUB,
            upstream_repo="https://github.com/wjsqqj/aquan-duanju",
            license="Apache-2.0",
            note="骨架：待按上游公开接口实现 search / detail / resolve。",
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
