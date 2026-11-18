"""配置加载：来源接入参数与运行时开关。

设计原则（见 docs/COMPLIANCE.md）：
- 配置里**不放凭证**，只放“环境变量名”，由运行时注入；
- 仓库内只提交 `sources.example.json` 占位示例，真实配置用环境变量指向仓库外文件；
- 配置文件缺失时返回空集合，平台仍可在演示源上运行。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "sources.json"
CONFIG_ENV = "LGL_SOURCES_CONFIG"

# 允许配置的 HTTP 方法白名单，避免配置变成任意请求工具
ALLOWED_METHODS = {"GET"}


@dataclass(frozen=True)
class EndpointConfig:
    """单个端点模板。`path` 中可用占位符：{query} {page} {id} {episode}。"""

    path: str
    method: str = "GET"
    params: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceConfig:
    """一个可配置来源的接入参数。"""

    adapter_id: str
    display_name: str
    media_types: List[str]
    base_url: str
    endpoints: Dict[str, EndpointConfig]
    fields: Dict[str, str] = field(default_factory=dict)
    search_items_path: str = "data.items"
    episodes_path: str = "data.episodes"
    chapters_path: str = "data.chapters"
    resolve_url_field: str = "data.url"
    license_name: str = "待确认"
    upstream_repo: Optional[str] = None
    note: Optional[str] = None
    enabled: bool = False
    auth_env: Optional[str] = None          # 环境变量名，运行时注入 Authorization
    headers_env: Optional[str] = None       # 环境变量名，值为 JSON 对象
    timeout_seconds: float = 10.0
    max_retries: int = 2
    min_interval_seconds: float = 0.5

    @property
    def host(self) -> str:
        from urllib.parse import urlparse

        return (urlparse(self.base_url).hostname or "").lower()


def _parse_endpoint(raw: Any) -> EndpointConfig:
    if isinstance(raw, str):
        raw = {"path": raw}
    if not isinstance(raw, dict) or not raw.get("path"):
        raise ValueError("endpoint 配置必须是字符串或包含 path 的对象")
    method = str(raw.get("method", "GET")).upper()
    if method not in ALLOWED_METHODS:
        raise ValueError(f"不允许的 HTTP 方法：{method}")
    return EndpointConfig(
        path=str(raw["path"]),
        method=method,
        params={str(k): str(v) for k, v in (raw.get("params") or {}).items()},
    )


def parse_source(raw: Dict[str, Any]) -> SourceConfig:
    adapter_id = str(raw.get("adapter_id") or "").strip()
    if not adapter_id:
        raise ValueError("来源配置缺少 adapter_id")
    base_url = str(raw.get("base_url") or "").strip()
    if not base_url.startswith(("http://", "https://")):
        raise ValueError(f"{adapter_id}: base_url 必须是 http(s) 地址")

    endpoints = {
        name: _parse_endpoint(value)
        for name, value in (raw.get("endpoints") or {}).items()
    }
    return SourceConfig(
        adapter_id=adapter_id,
        display_name=str(raw.get("display_name") or adapter_id),
        media_types=list(raw.get("media_types") or ["drama", "video", "novel"]),
        base_url=base_url.rstrip("/"),
        endpoints=endpoints,
        fields=dict(raw.get("fields") or {}),
        search_items_path=str(raw.get("search_items_path") or "data.items"),
        episodes_path=str(raw.get("episodes_path") or "data.episodes"),
        chapters_path=str(raw.get("chapters_path") or "data.chapters"),
        resolve_url_field=str(raw.get("resolve_url_field") or "data.url"),
        license_name=str(raw.get("license") or "待确认"),
        upstream_repo=raw.get("upstream_repo"),
        note=raw.get("note"),
        enabled=bool(raw.get("enabled", False)),
        auth_env=raw.get("auth_env"),
        headers_env=raw.get("headers_env"),
        timeout_seconds=float(raw.get("timeout_seconds", 10.0)),
        max_retries=int(raw.get("max_retries", 2)),
        min_interval_seconds=float(raw.get("min_interval_seconds", 0.5)),
    )


def config_path() -> Path:
    override = os.environ.get(CONFIG_ENV)
    return Path(override).expanduser() if override else DEFAULT_CONFIG_PATH


class ConfigError(ValueError):
    """配置非法。"""


def load_sources_config(path: Optional[Path] = None) -> Dict[str, SourceConfig]:
    """读取来源配置；文件不存在时返回空集合。"""
    target = path or config_path()
    if not target.exists():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"配置文件不是合法 JSON：{target}") from exc

    raw_sources = payload.get("sources") if isinstance(payload, dict) else payload
    if not isinstance(raw_sources, list):
        raise ConfigError("配置文件顶层必须是 sources 数组")

    result: Dict[str, SourceConfig] = {}
    for raw in raw_sources:
        if not isinstance(raw, dict):
            raise ConfigError("sources 数组元素必须是对象")
        source = parse_source(raw)
        if source.adapter_id in result:
            raise ConfigError(f"来源重复：{source.adapter_id}")
        result[source.adapter_id] = source
    return result


def runtime_headers(source: SourceConfig) -> Dict[str, str]:
    """从环境变量取出运行时请求头；不落盘、不写日志。"""
    headers: Dict[str, str] = {"Accept": "application/json"}
    if source.headers_env:
        raw = os.environ.get(source.headers_env)
        if raw:
            try:
                extra = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ConfigError(f"{source.adapter_id}: headers_env 不是合法 JSON") from exc
            if isinstance(extra, dict):
                headers.update({str(k): str(v) for k, v in extra.items()})
    if source.auth_env:
        token = os.environ.get(source.auth_env)
        if token:
            headers["Authorization"] = token
    return headers
