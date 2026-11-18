"""统一 HTTP 客户端：域名白名单、超时、有限重试、最小请求间隔。

合规约束：
- 只允许访问配置里显式声明的上游域名（白名单），杜绝把适配器变成通用代理；
- 只支持 GET，不做批量并发抓取；
- 请求头只携带运行时注入的鉴权信息，不写入日志、不落盘；
- 429 / 5xx / 网络错误才重试，且指数退避，最多 `max_retries` 次。
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlencode, urlparse

from platform.errors import RateLimited, SourceDisabled, UpstreamError

DEFAULT_UA = "lets-go-look/0.2 (+metadata aggregator)"


@dataclass
class HttpResult:
    status: int
    payload: Any


class Throttle:
    """按主机维持最小请求间隔，避免高频拉取。"""

    def __init__(self, min_interval_seconds: float) -> None:
        self._interval = max(0.0, min_interval_seconds)
        self._last: Dict[str, float] = {}

    def wait(self, host: str) -> None:
        if self._interval <= 0:
            return
        now = time.monotonic()
        last = self._last.get(host)
        if last is not None:
            elapsed = now - last
            if elapsed < self._interval:
                time.sleep(self._interval - elapsed)
        self._last[host] = time.monotonic()


class HttpClient:
    """极简 HTTP 客户端，仅 GET + JSON。"""

    def __init__(
        self,
        allowed_hosts: Iterable[str],
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
        min_interval_seconds: float = 0.5,
        user_agent: str = DEFAULT_UA,
    ) -> None:
        self.allowed_hosts = {h.lower() for h in allowed_hosts if h}
        self.timeout = timeout_seconds
        self.max_retries = max(0, max_retries)
        self.throttle = Throttle(min_interval_seconds)
        self.user_agent = user_agent

    # ---- 校验 -------------------------------------------------------

    def _assert_allowed(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise UpstreamError("只允许 http(s) 请求")
        host = (parsed.hostname or "").lower()
        if host not in self.allowed_hosts:
            raise SourceDisabled(f"域名未在白名单内：{host}")
        return host

    # ---- 请求 -------------------------------------------------------

    def get_json(self, url: str, headers: Optional[Dict[str, str]] = None) -> HttpResult:
        host = self._assert_allowed(url)
        request_headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        request_headers.update(headers or {})

        attempt = 0
        last_error: Optional[Exception] = None
        while attempt <= self.max_retries:
            if attempt:
                time.sleep(min(2 ** attempt * 0.5, 4.0))
            self.throttle.wait(host)
            try:
                request = urllib.request.Request(url, headers=request_headers, method="GET")
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    return HttpResult(status=response.status, payload=_decode(raw))
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    last_error = RateLimited("上游返回 429，已超出频次限制")
                elif 500 <= exc.code < 600:
                    last_error = UpstreamError(f"上游返回 {exc.code}")
                else:
                    raise UpstreamError(f"上游返回 {exc.code}") from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = UpstreamError("上游网络不可达或超时", detail={"error": type(exc).__name__})
            attempt += 1

        assert last_error is not None
        raise last_error

    # ---- 工具 -------------------------------------------------------

    @staticmethod
    def build_url(base_url: str, path: str, params: Optional[Dict[str, str]] = None) -> str:
        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        if params:
            joiner = "&" if "?" in url else "?"
            url = f"{url}{joiner}{urlencode(params)}"
        return url


def _decode(raw: bytes) -> Any:
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise UpstreamError("上游返回不是合法 JSON") from exc


def pick(payload: Any, dotted_path: str, default: Any = None) -> Any:
    """按点路径取值，如 `data.items`；支持列表下标 `data.items.0.title`。"""
    current = payload
    for part in (dotted_path or "").split("."):
        if not part:
            continue
        if isinstance(current, dict):
            if part not in current:
                return default
            current = current[part]
        elif isinstance(current, list):
            try:
                index = int(part)
            except ValueError:
                return default
            if index < 0 or index >= len(current):
                return default
            current = current[index]
        else:
            return default
    return current
