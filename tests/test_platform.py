"""聚合平台单元测试（标准库 unittest）。

运行：PYTHONPATH=. python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import threading
import unittest
import urllib.error
import urllib.request
from typing import Optional, Sequence

from platform.adapters import ADAPTERS
from platform.adapters.base import SourceAdapter
from platform.aggregator import Aggregator, normalize_title
from platform.errors import BadRequest, NotFound, SourceDisabled
from platform.models import MediaItem, MediaType, ResolvedSource, SourceMeta, SourceStatus
from platform.registry import Registry


class FakeAdapter(SourceAdapter):
    """测试用假适配器：固定返回若干条目，或按需抛出异常。"""

    ADAPTER_ID = "fake"

    def __init__(
        self,
        adapter_id: str,
        items: Sequence[MediaItem],
        status: SourceStatus = SourceStatus.ACTIVE,
        fail: Optional[Exception] = None,
    ) -> None:
        self.ADAPTER_ID = adapter_id
        self._items = list(items)
        self._status = status
        self._fail = fail

    def meta(self) -> SourceMeta:
        return SourceMeta(
            adapter_id=self.ADAPTER_ID,
            display_name=f"假来源 {self.ADAPTER_ID}",
            media_types=(MediaType.DRAMA, MediaType.NOVEL),
            status=self._status,
            license="test",
        )

    def _maybe_fail(self) -> None:
        if self._fail is not None:
            raise self._fail

    def search(self, query: str, media_type: Optional[MediaType] = None, page: int = 1) -> Sequence[MediaItem]:
        self._maybe_fail()
        return [i for i in self._items if media_type is None or i.media_type == media_type]

    def detail(self, external_id: str) -> MediaItem:
        self._maybe_fail()
        for item in self._items:
            if item.external_id == external_id:
                return item
        raise NotFound(f"不存在：{external_id}")

    def resolve(self, external_id: str, episode_or_chapter_id: Optional[str] = None) -> ResolvedSource:
        self._maybe_fail()
        return ResolvedSource(url=f"https://example.com/{external_id}", media_type=MediaType.DRAMA)


def make_item(source: str, eid: str, title: str, media_type: MediaType, rating: float) -> MediaItem:
    return MediaItem(
        source=source,
        external_id=eid,
        title=title,
        media_type=media_type,
        rating=rating,
    )


class RegistryTest(unittest.TestCase):
    def test_default_registry_contains_all_sources(self) -> None:
        registry = Registry()
        self.assertEqual(len(registry.ids()), len(ADAPTERS))
        for adapter_id in registry.ids():
            registry.get(adapter_id).meta()

    def test_disabled_sources_excluded_from_enabled(self) -> None:
        registry = Registry()
        ids = [adapter.meta().adapter_id for adapter in registry.enabled()]
        self.assertNotIn("xiaoguo_video", ids)
        self.assertNotIn("biquge_reader", ids)
        self.assertIn("demo_catalog", ids)

    def test_unknown_source_raises(self) -> None:
        with self.assertRaises(NotFound):
            Registry().get("no_such_source")


class DemoCatalogTest(unittest.TestCase):
    def setUp(self) -> None:
        self.aggregator = Aggregator()

    def test_health_counts_sources(self) -> None:
        payload = self.aggregator.health()
        total = sum(payload["by_status"].values())
        self.assertEqual(total, payload["source_count"])
        self.assertEqual(payload["by_status"][SourceStatus.DISABLED.value], 2)

    def test_search_returns_demo_items(self) -> None:
        outcome = self.aggregator.search("雾", sources=["demo_catalog"])
        self.assertEqual(outcome.total, 1)
        self.assertEqual(outcome.items[0].title, "雾港三封信")
        self.assertFalse(outcome.degraded)

    def test_search_type_filter(self) -> None:
        outcome = self.aggregator.search("图书馆", media_type=MediaType.NOVEL)
        self.assertEqual(outcome.total, 1)
        self.assertEqual(outcome.items[0].media_type, MediaType.NOVEL)

    def test_search_empty_query_rejected(self) -> None:
        with self.assertRaises(BadRequest):
            self.aggregator.search("   ")

    def test_detail_and_resolve(self) -> None:
        detail = self.aggregator.detail("demo_catalog", "demo-drama-001")
        self.assertEqual(len(detail["episodes"]), 3)
        resolved = self.aggregator.resolve("demo_catalog", "demo-drama-001", "ep-1")
        self.assertTrue(resolved["url"].startswith("https://example.com/demo-media/"))
        self.assertEqual(resolved["format"], "m3u8")

    def test_resolve_unknown_episode(self) -> None:
        with self.assertRaises(NotFound):
            self.aggregator.resolve("demo_catalog", "demo-drama-001", "ep-99")


class AggregationBehaviourTest(unittest.TestCase):
    def test_stub_sources_degrade_without_failing(self) -> None:
        outcome = Aggregator().search("雾")
        statuses = {r["adapter_id"]: r for r in outcome.per_source}
        # 骨架来源全部返回 SOURCE_NOT_READY，但整体检索仍然成功
        self.assertTrue(outcome.degraded)
        self.assertIn("aquan_duanju", statuses)
        self.assertEqual(statuses["aquan_duanju"]["error"]["code"], "SOURCE_NOT_READY")

    def test_disabled_source_reported_when_explicit(self) -> None:
        outcome = Aggregator().search("雾", sources=["xiaoguo_video", "demo_catalog"])
        record = next(r for r in outcome.per_source if r["adapter_id"] == "xiaoguo_video")
        self.assertEqual(record["error"]["code"], "SOURCE_DISABLED")
        self.assertEqual(outcome.total, 1)

    def test_detail_on_disabled_source_is_forbidden(self) -> None:
        with self.assertRaises(SourceDisabled):
            Aggregator().detail("biquge_reader", "any")

    def test_cross_source_dedupe_and_ranking(self) -> None:
        left = make_item("left", "l-1", "雾港三封信", MediaType.DRAMA, 7.0)
        right = make_item("right", "r-1", "雾港 三封信", MediaType.DRAMA, 9.0)
        other = make_item("right", "r-2", "长夜列车", MediaType.DRAMA, 8.0)
        registry = Registry(
            factories={
                "left": lambda: FakeAdapter("left", [left]),
                "right": lambda: FakeAdapter("right", [right, other]),
            }
        )
        aggregator = Aggregator(registry=registry)
        outcome = aggregator.search("三封信", sources=["left", "right"])

        self.assertEqual(outcome.total, 2)
        top = outcome.items[0]
        # 主项取自评分更高的来源，因此展示其标题；两个来源都被聚到同一 key
        self.assertEqual(top.primary.rating, 9.0)
        self.assertEqual(top.primary.title, "雾港 三封信")
        self.assertEqual(len(top.sources), 2)
        self.assertEqual({ref.adapter_id for ref in top.sources}, {"left", "right"})
        self.assertEqual(top.key, "drama:" + normalize_title("雾港三封信"))

    def test_partial_failure_keeps_results(self) -> None:
        good = make_item("good", "g-1", "潮汐图书馆", MediaType.NOVEL, 8.0)
        registry = Registry(
            factories={
                "good": lambda: FakeAdapter("good", [good]),
                "bad": lambda: FakeAdapter("bad", [], fail=RuntimeError("boom")),
            }
        )
        outcome = Aggregator(registry=registry).search("潮汐", sources=["good", "bad"])
        self.assertEqual(outcome.total, 1)
        self.assertTrue(outcome.degraded)
        bad = next(r for r in outcome.per_source if r["adapter_id"] == "bad")
        self.assertEqual(bad["error"]["code"], "UPSTREAM_ERROR")

    def test_search_cache_hits(self) -> None:
        aggregator = Aggregator(cache_ttl=60)
        first = aggregator.search("雾")
        second = aggregator.search("雾")
        self.assertIs(first, second)

    def test_normalize_title_ignores_punctuation_and_case(self) -> None:
        self.assertEqual(normalize_title("Hong  Kong，第 1 季"), normalize_title("hongkong第1季"))


class HttpApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from platform.server import build_server

        cls.httpd = build_server("127.0.0.1", 0)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)

    def _get(self, path: str) -> tuple[int, dict]:
        import json

        url = f"http://127.0.0.1:{self.port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def test_health(self) -> None:
        status, payload = self._get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")

    def test_search_endpoint(self) -> None:
        status, payload = self._get("/search?q=%E6%B5%81&type=novel")
        self.assertEqual(status, 200)
        self.assertIn("items", payload)

    def test_search_missing_query(self) -> None:
        status, payload = self._get("/search")
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["code"], "BAD_REQUEST")

    def test_disabled_source_returns_403(self) -> None:
        status, payload = self._get("/detail?source=xiaoguo_video&id=x")
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"]["code"], "SOURCE_DISABLED")

    def test_stub_source_returns_409(self) -> None:
        status, payload = self._get("/detail?source=aquan_duanju&id=x")
        self.assertEqual(status, 409)
        self.assertEqual(payload["error"]["code"], "SOURCE_NOT_READY")

    def test_unknown_route(self) -> None:
        status, payload = self._get("/nope")
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"]["code"], "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
