"""统一领域模型：跨来源归一化后的内容描述。

仅定义数据结构，不包含任何上游专有接口字段或反编译产物。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MediaType(str, Enum):
    DRAMA = "drama"      # 短剧
    VIDEO = "video"      # 影视（电影 / 长剧）
    NOVEL = "novel"      # 小说
    COMIC = "comic"      # 漫画（预留）


class SourceStatus(str, Enum):
    """适配器接入状态。"""

    ACTIVE = "active"            # 已授权 / 许可证清晰，可实现对接
    STUB = "stub"                # 骨架已留，待授权或许可证确认
    DISABLED = "disabled"        # 未授权闭源来源，禁止实现检索 / 解析


@dataclass(frozen=True)
class SourceMeta:
    """来源（适配器）元信息。"""

    adapter_id: str
    display_name: str
    media_types: tuple[MediaType, ...]
    status: SourceStatus
    upstream_repo: Optional[str] = None
    license: Optional[str] = None
    note: Optional[str] = None


@dataclass(frozen=True)
class MediaItem:
    """一部剧 / 一个视频 / 一本书的归一化描述。"""

    source: str                      # 适配器 ID
    external_id: str                  # 上游内外部 ID
    title: str
    media_type: MediaType
    cover_url: Optional[str] = None
    summary: Optional[str] = None
    author: Optional[str] = None
    status: Optional[str] = None      # 连载 / 完结 / 更新中
    rating: Optional[float] = None
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Episode:
    """短剧分集 / 影视剧集；小说对应章节见 Chapter。"""

    external_id: str
    index: int
    title: str
    duration_seconds: Optional[int] = None
    is_finished: Optional[bool] = None
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Chapter:
    """小说章节。"""

    external_id: str
    index: int
    title: str
    word_count: Optional[int] = None
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ResolvedSource:
    """解析后的可播放 / 可阅读地址。

    headers 中只存放必要的引用标识；真实令牌由服务端会话注入，不入库、不入仓库。
    """

    url: str
    media_type: MediaType
    quality: Optional[str] = None
    format: Optional[str] = None
    headers: dict = field(default_factory=dict)
    expires_in_seconds: Optional[int] = None
    note: Optional[str] = None
