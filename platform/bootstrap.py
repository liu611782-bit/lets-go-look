"""平台装配：内置适配器 + 配置驱动的来源，一并注册。

默认无 `platform/config/sources.json` 时，注册表就是内置 7 个来源；
一旦提供配置（文件或 `LGL_SOURCES_CONFIG`），额外来源自动上线，
状态由 `enabled` 决定（false 时可见但不发起真实请求）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from platform.adapters.http_source import ConfiguredHttpAdapter
from platform.config import SourceConfig, load_sources_config
from platform.registry import Registry


def register_configured(registry: Registry, sources: dict[str, SourceConfig]) -> Registry:
    for adapter_id, source in sources.items():
        registry.register(adapter_id, _factory_for(source))
    return registry


def _factory_for(source: SourceConfig):
    def create() -> ConfiguredHttpAdapter:
        return ConfiguredHttpAdapter(source)

    return create


def create_registry(config_file: Optional[Path] = None) -> Registry:
    registry = Registry()
    try:
        sources = load_sources_config(config_file)
    except Exception:
        # 配置非法时不阻断平台启动，只让可配置来源缺位
        sources = {}
    return register_configured(registry, sources)


default_registry = create_registry()
