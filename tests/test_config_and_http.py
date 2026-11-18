"""配置加载、HTTP 客户端与配置驱动适配器的测试。

使用本地模拟上游（127.0.0.1 随机端口），不访问任何真实站点。
"""

from __future__ import annotations

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List

from platform.config import ConfigError, EndpointConfig, SourceConfig, load_sources_config, parse_source
from platform.errors import RateLimited, SourceDisabled, SourceNotReady, UpstreamError
from platform.http_client import HttpClient, pick
from platform.models import MediaType
from platform.adapters.http_source import ConfiguredHttpAdapter


# ---------------------------------------------------------------- 模拟上游


class MockUpstream(BaseHTTPRequestHandler):
    """按路径返回固定 JSON；可配置失败次数以验证重试。"""

    calls: List[str] = []
    fail_status: int = 0
    fail_times: int = 0

    def log_message(self, *args: Any) -> None:
        pass

    def do_GET(self) -> None:  # noqa: N802
        type(self).calls.append(self.path)
        if MockUpstream.fail_times > 0:
            MockUpstream.fail_times -= 1
            self.send_response(MockUpstream.fail_status or 500)
            self.end_headers()
            self.wfile.write(b"{}")
            return

        if self.path.startswith("/v1/search"):
            payload = {
                "data": {
                    "items": [
                        {"id": "m-1", "title": "测试作品一", "rating": "8.4", "summary": "简介一"},
                        {"id": "m-2", "title": "测试作品二", "rating": None},
                    ]
                }
            }
        elif self.path.startswith("/v1/detail/m-1"):
            payload = {"data": {"id": "m-1", "title": "测试作品一", "rating": 8.4}}
        elif self.path.startswith("/v1/episodes/m-1") or self.path.startswith("/v1/detail/m-1/episodes"):
            payload = {"data": {"episodes": [{"id": "e-1", "title": "第一集", "duration": 600}]}}
        elif self.path.startswith("/v1/play/m-1"):
            payload = {"data": {"url": "https://cdn.example.com/m-1.m3u8", "format": "m3u8"}}
        else:
            payload = {"data": {}}

        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_mock() -> tuple[ThreadingHTTPServer, int]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), MockUpstream)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    MockUpstream.calls = []
    MockUpstream.fail_times = 0
    return httpd, port


# ---------------------------------------------------------------- 配置


class ConfigTest(unittest.TestCase):
    def test_parse_source_minimal(self) -> None:
        source = parse_source(
            {
                "adapter_id": "test_src",
                "base_url": "https://api.example.com/",
                "endpoints": {"search": "v1/search"},
            }
        )
        self.assertEqual(source.base_url, "https://api.example.com")
        self.assertEqual(source.host, "api.example.com")
        self.assertFalse(source.enabled)
        self.assertEqual(source.endpoints["search"].method, "GET")

    def test_parse_source_rejects_bad_base_url(self) -> None:
        with self.assertRaises(ValueError):
            parse_source({"adapter_id": "x", "base_url": "ftp://example.com"})

    def test_parse_source_rejects_post(self) -> None:
        with self.assertRaises(ValueError):
            parse_source(
                {
                    "adapter_id": "x",
                    "base_url": "https://example.com",
                    "endpoints": {"search": {"path": "v1/s", "method": "POST"}},
                }
            )

    def test_missing_file_returns_empty(self) -> None:
        self.assertEqual(load_sources_config(Path("/nonexistent/sources.json")), {})

    def test_duplicate_adapter_id_rejected(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.json"
            path.write_text(
                json.dumps(
                    {
                        "sources": [
                            {"adapter_id": "dup", "base_url": "https://a.example.com"},
                            {"adapter_id": "dup", "base_url": "https://b.example.com"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ConfigError):
                load_sources_config(path)

    def test_example_config_is_valid_json(self) -> None:
        example = Path(__file__).resolve().parent.parent / "platform" / "config" / "sources.example.json"
        payload = json.loads(example.read_text(encoding="utf-8"))
        self.assertIn("sources", payload)
        # 示例默认必须关闭，避免误连
        for raw in payload["sources"]:
            self.assertFalse(bool(raw.get("enabled", False)))


# ---------------------------------------------------------------- HTTP 客户端


class HttpClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.httpd, cls.port = start_mock()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def test_domain_not_in_allowlist_rejected(self) -> None:
        client = HttpClient(allowed_hosts=["api.other.com"])
        with self.assertRaises(SourceDisabled):
            client.get_json(f"http://127.0.0.1:{self.port}/v1/search")

    def test_get_json_success(self) -> None:
        client = HttpClient(allowed_hosts=["127.0.0.1"])
        result = client.get_json(f"http://127.0.0.1:{self.port}/v1/search")
        self.assertEqual(result.status, 200)
        self.assertIsInstance(result.payload, dict)

    def test_retry_then_success(self) -> None:
        MockUpstream.calls = []
        MockUpstream.fail_times = 1
        MockUpstream.fail_status = 500
        client = HttpClient(allowed_hosts=["127.0.0.1"], max_retries=1)
        result = client.get_json(f"http://127.0.0.1:{self.port}/v1/search")
        self.assertEqual(result.status, 200)
        self.assertGreaterEqual(len(MockUpstream.calls), 2)  # 第一次 500，重试后成功
        MockUpstream.fail_times = 0

    def test_429_raises_rate_limited(self) -> None:
        MockUpstream.fail_times = 5
        MockUpstream.fail_status = 429
        client = HttpClient(allowed_hosts=["127.0.0.1"], max_retries=1)
        with self.assertRaises(RateLimited):
            client.get_json(f"http://127.0.0.1:{self.port}/v1/search")
        MockUpstream.fail_times = 0

    def test_pick_dotted_path(self) -> None:
        payload = {"data": {"items": [{"title": "a"}]}}
        self.assertEqual(pick(payload, "data.items.0.title"), "a")
        self.assertIsNone(pick(payload, "data.items.5.title"))
        self.assertEqual(pick(payload, "data.items.0.title.x", "fallback"), "fallback")

    def test_build_url_with_params(self) -> None:
        url = HttpClient.build_url("https://api.example.com/", "/v1/search", {"q": "雾", "page": "1"})
        self.assertIn("q=%E9%9B%BE", url)  # "雾" 的 UTF-8 百分号编码
        self.assertIn("page=1", url)


# ---------------------------------------------------------------- 配置驱动适配器


class ConfiguredAdapterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.httpd, cls.port = start_mock()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _config(self, enabled: bool = True) -> SourceConfig:
        return SourceConfig(
            adapter_id="mock_src",
            display_name="模拟来源",
            media_types=["drama"],
            base_url=self.base_url,
            endpoints={
                "search": EndpointConfig(path="v1/search", params={"q": "{query}", "page": "{page}"}),
                "detail": EndpointConfig(path="v1/detail/{id}"),
                "episodes": EndpointConfig(path="v1/episodes/{id}"),
                "resolve": EndpointConfig(path="v1/play/{id}", params={"episode": "{episode}"}),
            },
            license_name="test-only",
            enabled=enabled,
            min_interval_seconds=0,
            max_retries=0,
        )

    def test_meta_status_follows_enabled(self) -> None:
        self.assertEqual(ConfiguredHttpAdapter(self._config(True)).meta().status.value, "active")
        self.assertEqual(ConfiguredHttpAdapter(self._config(False)).meta().status.value, "stub")

    def test_search_maps_fields(self) -> None:
        adapter = ConfiguredHttpAdapter(self._config())
        items = list(adapter.search("测试", page=1))
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].external_id, "m-1")
        self.assertEqual(items[0].title, "测试作品一")
        self.assertAlmostEqual(items[0].rating, 8.4)
        self.assertIsNone(items[1].rating)

    def test_detail_and_episodes_and_resolve(self) -> None:
        adapter = ConfiguredHttpAdapter(self._config())
        item = adapter.detail("m-1")
        self.assertEqual(item.title, "测试作品一")
        episodes = list(adapter.episodes("m-1"))
        self.assertEqual(episodes[0].external_id, "e-1")
        resolved = adapter.resolve("m-1", "e-1")
        self.assertEqual(resolved.url, "https://cdn.example.com/m-1.m3u8")
        self.assertEqual(resolved.format, "m3u8")

    def test_missing_endpoint_reports_not_ready(self) -> None:
        from dataclasses import replace

        config = replace(self._config(), endpoints={"search": self._config().endpoints["search"]})
        adapter = ConfiguredHttpAdapter(config)
        with self.assertRaises(SourceNotReady):
            adapter.resolve("m-1")

    def test_empty_query_rejected(self) -> None:
        from platform.errors import BadRequest

        adapter = ConfiguredHttpAdapter(self._config())
        with self.assertRaises(BadRequest):
            adapter.search("  ")


# ---------------------------------------------------------------- 前端页面


class WebUiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from platform.aggregator import default_aggregator
        from platform.server import Handler, build_server

        Handler.aggregator = default_aggregator
        cls.httpd = build_server("127.0.0.1", 0)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)

    def _raw(self, path: str):
        import urllib.request

        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as response:
            return response.status, response.read().decode("utf-8")

    def test_root_serves_ui(self) -> None:
        status, body = self._raw("/")
        self.assertEqual(status, 200)
        self.assertIn("lets-go-look", body)
        self.assertIn("多源影视", body)

    def test_ui_alias(self) -> None:
        status, body = self._raw("/ui")
        self.assertEqual(status, 200)
        self.assertIn("/search?", body)


if __name__ == "__main__":
    unittest.main()
