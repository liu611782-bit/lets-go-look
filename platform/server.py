"""统一聚合服务的最小 HTTP 接口（标准库实现，无第三方依赖）。

端点：
  GET /health
  GET /sources
  GET /search?q=关键词&type=drama|video|novel|comic&page=1&sources=a,b
  GET /detail?source=demo_catalog&id=demo-drama-001
  GET /resolve?source=demo_catalog&id=demo-drama-001&episode=ep-1

启动：PYTHONPATH=. python3 -m platform.cli serve --host 127.0.0.1 --port 8080
"""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from platform.aggregator import Aggregator, default_aggregator
from platform.errors import (
    BadRequest,
    ErrorCode,
    NotFound,
    PlatformError,
)
from platform.models import MediaType

HTTP_BY_CODE: Dict[ErrorCode, int] = {
    ErrorCode.BAD_REQUEST: HTTPStatus.BAD_REQUEST,
    ErrorCode.NOT_FOUND: HTTPStatus.NOT_FOUND,
    ErrorCode.SOURCE_DISABLED: HTTPStatus.FORBIDDEN,
    ErrorCode.SOURCE_NOT_READY: HTTPStatus.CONFLICT,
    ErrorCode.RATE_LIMITED: HTTPStatus.TOO_MANY_REQUESTS,
    ErrorCode.UPSTREAM_ERROR: HTTPStatus.BAD_GATEWAY,
    ErrorCode.INTERNAL_ERROR: HTTPStatus.INTERNAL_SERVER_ERROR,
}

INDEX_HTML = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>lets-go-look</title></head>
<body style="font-family:system-ui;max-width:720px;margin:48px auto;line-height:1.7">
<h1>lets-go-look 聚合服务</h1>
<p>统一检索、详情与解析入口。演示来源 <code>demo_catalog</code> 为仓库自造虚构数据。</p>
<ul>
<li><a href="/health">/health</a> — 服务与各来源状态</li>
<li><a href="/sources">/sources</a> — 来源清单与许可证</li>
<li><a href="/search?q=雾">/search?q=雾</a> — 多源检索</li>
<li><a href="/detail?source=demo_catalog&amp;id=demo-drama-001">/detail</a> — 详情与分集</li>
<li><a href="/resolve?source=demo_catalog&amp;id=demo-drama-001&amp;episode=ep-1">/resolve</a> — 解析（演示占位地址）</li>
</ul>
<p>未授权来源（DISABLED）不发起任何请求；STUB 来源返回 SOURCE_NOT_READY。</p>
</body></html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "lets-go-look/0.2"
    aggregator: Aggregator = default_aggregator

    # ---- 基础工具 ---------------------------------------------------

    def log_message(self, fmt: str, *args: Any) -> None:  # 精简日志，不记录查询内容
        super().log_message(fmt, *args)

    def _send(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status: int, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _fail(self, error: PlatformError) -> None:
        self._send(HTTP_BY_CODE.get(error.code, HTTPStatus.INTERNAL_SERVER_ERROR), {"error": error.to_dict()})

    @staticmethod
    def _single(params: Dict[str, list], name: str) -> Optional[str]:
        values = params.get(name) or []
        return values[0].strip() if values and values[0].strip() else None

    # ---- 路由 -------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802 — 标准库约定
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/") or "/"
        params = parse_qs(parsed.query, keep_blank_values=False)
        try:
            if route == "/":
                self._send_html(HTTPStatus.OK, INDEX_HTML)
                return
            if route == "/health":
                self._send(HTTPStatus.OK, self.aggregator.health())
                return
            if route == "/sources":
                self._send(HTTPStatus.OK, {"sources": self.aggregator.sources()})
                return
            if route == "/search":
                self._handle_search(params)
                return
            if route == "/detail":
                self._handle_detail(params)
                return
            if route == "/resolve":
                self._handle_resolve(params)
                return
            raise NotFound(f"未定义的路由：{route}")
        except PlatformError as error:
            self._fail(error)
        except Exception:  # noqa: BLE001 — 兜底，不泄漏堆栈
            self._fail(PlatformError("服务内部错误"))

    def _handle_search(self, params: Dict[str, list]) -> None:
        query = self._single(params, "q")
        if not query:
            raise BadRequest("缺少查询参数 q")
        raw_type = self._single(params, "type")
        media_type = None
        if raw_type:
            try:
                media_type = MediaType(raw_type)
            except ValueError as exc:
                raise BadRequest(f"不支持的 type：{raw_type}") from exc
        raw_page = self._single(params, "page") or "1"
        try:
            page = int(raw_page)
        except ValueError as exc:
            raise BadRequest(f"page 需为整数：{raw_page}") from exc
        raw_sources = self._single(params, "sources")
        sources = [s for s in (raw_sources or "").split(",") if s.strip()] or None
        outcome = self.aggregator.search(query, media_type=media_type, page=page, sources=sources)
        self._send(HTTPStatus.OK, outcome.to_dict())

    def _handle_detail(self, params: Dict[str, list]) -> None:
        source = self._single(params, "source")
        external_id = self._single(params, "id")
        if not source or not external_id:
            raise BadRequest("source 与 id 均为必填")
        self._send(HTTPStatus.OK, self.aggregator.detail(source, external_id))

    def _handle_resolve(self, params: Dict[str, list]) -> None:
        source = self._single(params, "source")
        external_id = self._single(params, "id")
        if not source or not external_id:
            raise BadRequest("source 与 id 均为必填")
        episode = self._single(params, "episode") or self._single(params, "chapter")
        self._send(HTTPStatus.OK, self.aggregator.resolve(source, external_id, episode))


def build_server(host: str = "127.0.0.1", port: int = 8080) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)


def serve(host: str = "127.0.0.1", port: int = 8080) -> None:
    httpd = build_server(host, port)
    print(f"lets-go-look 聚合服务已启动：http://{host}:{port}")
    print("按 Ctrl+C 停止")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        httpd.server_close()
