"""适配器注册表：按 adapter_id 注册工厂函数。

新增来源时在这里登记，并实现 base.SourceAdapter 契约。
"""

from __future__ import annotations

from typing import Callable, Dict

from .base import SourceAdapter
from .aquan_duanju import AquanDuanjuAdapter
from .iduanju import IDuanjuAdapter
from .fanqie_novel import FanqieNovelAdapter
from .zhenguojian import ZhenguojianAdapter
from .closed_apps import xiaoguo_video, biquge_reader

AdapterFactory = Callable[[], SourceAdapter]

ADAPTERS: Dict[str, AdapterFactory] = {
    AquanDuanjuAdapter.ADAPTER_ID: AquanDuanjuAdapter,
    IDuanjuAdapter.ADAPTER_ID: IDuanjuAdapter,
    FanqieNovelAdapter.ADAPTER_ID: FanqieNovelAdapter,
    ZhenguojianAdapter.ADAPTER_ID: ZhenguojianAdapter,
    "xiaoguo_video": xiaoguo_video,
    "biquge_reader": biquge_reader,
}

__all__ = ["SourceAdapter", "ADAPTERS"]
