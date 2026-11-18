"""闭源应用占位适配器（禁用）。

对应 APK：
- base.apk  小果影视    com.yingshib.xg        —— 未检索到公开上游
- base_4.apk 笔趣阁     com.qsreod.bqgcjb      —— 未检索到公开上游，疑似重打包

合规红线（见 docs/COMPLIANCE.md）：
- 未取得源码 / 接口授权前，禁止反编译、还原源码、提取私有接口或资源；
- 不得复用其包内出现的签名绕过逻辑；
- 本模块只提供元信息占位，所有业务方法直接返回禁用错误。
"""

from __future__ import annotations

from typing import Optional, Sequence

from platform.models import MediaItem, MediaType, ResolvedSource, SourceMeta, SourceStatus

from .base import SourceAdapter


class ClosedAppAdapter(SourceAdapter):
    """通用闭源占位适配器：状态固定为 DISABLED。"""

    def __init__(self, adapter_id: str, display_name: str, package: str, note: str):
        self._adapter_id = adapter_id
        self._display_name = display_name
        self._package = package
        self._note = note

    def meta(self) -> SourceMeta:
        return SourceMeta(
            adapter_id=self._adapter_id,
            display_name=self._display_name,
            media_types=(MediaType.DRAMA, MediaType.VIDEO, MediaType.NOVEL),
            status=SourceStatus.DISABLED,
            upstream_repo=None,
            license="闭源，未公开",
            note=self._note,
        )

    def search(self, query: str, media_type: Optional[MediaType] = None, page: int = 1) -> Sequence[MediaItem]:
        raise PermissionError(f"来源 {self._adapter_id} 未授权，已禁用；包名 {self._package}")

    def detail(self, external_id: str) -> MediaItem:
        raise PermissionError(f"来源 {self._adapter_id} 未授权，已禁用；包名 {self._package}")

    def resolve(self, external_id: str, episode_or_chapter_id: Optional[str] = None) -> ResolvedSource:
        raise PermissionError(f"来源 {self._adapter_id} 未授权，已禁用；包名 {self._package}")


def xiaoguo_video() -> ClosedAppAdapter:
    """小果影视占位（base.apk / com.yingshib.xg）。"""
    return ClosedAppAdapter(
        adapter_id="xiaoguo_video",
        display_name="小果影视",
        package="com.yingshib.xg",
        note="闭源二进制，未检索到公开上游；授权前保持禁用。",
    )


def biquge_reader() -> ClosedAppAdapter:
    """笔趣阁占位（base_4.apk / com.qsreod.bqgcjb）。"""
    return ClosedAppAdapter(
        adapter_id="biquge_reader",
        display_name="笔趣阁",
        package="com.qsreod.bqgcjb",
        note="闭源 / 疑似重打包；含签名绕过工具痕迹，禁止复用其逻辑。",
    )
