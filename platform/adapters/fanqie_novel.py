"""番茄小说下载器适配器（骨架）。

上游：https://github.com/POf-L/Fanqie-novel-Downloader
对应 APK：base_6.apk（com.pofl.fanqienoveldownloader）

合规提示：
- 上游仓库根目录未附 LICENSE 文件，在作者确认授权范围前，
  按“保留所有权利”处理：不复制源码 / 资源，不二次分发安装包。
- 小说 / 漫画 / 短剧内容版权归原权利人，平台只做入口编排。
"""

from __future__ import annotations

from typing import Optional, Sequence

from platform.models import (
    Chapter,
    MediaItem,
    MediaType,
    ResolvedSource,
    SourceMeta,
    SourceStatus,
)

from .base import SourceAdapter


class FanqieNovelAdapter(SourceAdapter):
    """番茄小说下载器来源适配器。当前为骨架，授权确认前禁用对接。"""

    ADAPTER_ID = "fanqie_novel"

    def meta(self) -> SourceMeta:
        return SourceMeta(
            adapter_id=self.ADAPTER_ID,
            display_name="番茄小说下载器",
            media_types=(MediaType.NOVEL, MediaType.COMIC, MediaType.DRAMA),
            status=SourceStatus.STUB,
            upstream_repo="https://github.com/POf-L/Fanqie-novel-Downloader",
            license="未附 LICENSE，授权待作者确认",
            note="骨架：许可证确认前不实现检索 / 解析逻辑。",
        )

    def search(
        self,
        query: str,
        media_type: Optional[MediaType] = None,
        page: int = 1,
    ) -> Sequence[MediaItem]:
        raise NotImplementedError("授权待确认：暂不实现")

    def detail(self, external_id: str) -> MediaItem:
        raise NotImplementedError("授权待确认：暂不实现")

    def chapters(self, external_id: str) -> Sequence[Chapter]:
        raise NotImplementedError("授权待确认：暂不实现")

    def resolve(self, external_id: str, episode_or_chapter_id: Optional[str] = None) -> ResolvedSource:
        raise NotImplementedError("授权待确认：暂不实现")
