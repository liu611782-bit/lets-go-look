"""真果鉴 / 红果鉴 短剧适配器（骨架）。

上游：
- 主线 [kuoluoss/zhenguojian](https://github.com/kuoluoss/zhenguojian)（GPL-3.0，
  applicationId `com.duanju.duanju_app`，红果 / 真果 / 蓝果三版本）
- 家族镜像：zhoufuweigg/guoapp 等（根目录无 LICENSE，授权待核，谨慎复用）

合规提示：
- GPL-3.0 具有传染性，与本平台代码的链接 / 衍生边界需先做合规复核；
- 仅对接公开 / 已授权接口，不绕过站源 VIP、登录或其他授权限制；
- 不解除源站的地区 / 内容访问限制。
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


class ZhenguojianAdapter(SourceAdapter):
    """真果鉴 / 红果鉴多站源短剧客户端适配器。当前为骨架。"""

    ADAPTER_ID = "zhenguojian"

    def meta(self) -> SourceMeta:
        return SourceMeta(
            adapter_id=self.ADAPTER_ID,
            display_name="真果鉴",
            media_types=(MediaType.DRAMA, MediaType.VIDEO),
            status=SourceStatus.STUB,
            upstream_repo="https://github.com/kuoluoss/zhenguojian",
            license="GPL-3.0（主线）；家族镜像分支许可证待核",
            note="骨架：GPL 边界复核并确认站源授权后，再实现 search / detail / resolve。",
        )

    def search(
        self,
        query: str,
        media_type: Optional[MediaType] = None,
        page: int = 1,
    ) -> Sequence[MediaItem]:
        raise NotImplementedError("待实现：多站源检索与结果归一化")

    def detail(self, external_id: str) -> MediaItem:
        raise NotImplementedError("待实现：详情与分集列表")

    def episodes(self, external_id: str) -> Sequence[Episode]:
        raise NotImplementedError("待实现：分集列表")

    def resolve(self, external_id: str, episode_or_chapter_id: Optional[str] = None) -> ResolvedSource:
        raise NotImplementedError("待实现：播放地址解析")
