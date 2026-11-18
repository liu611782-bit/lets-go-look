"""命令行入口：不启动服务也能验证聚合链路。

用法（仓库根目录执行）：
    PYTHONPATH=. python3 -m platform.cli sources
    PYTHONPATH=. python3 -m platform.cli health
    PYTHONPATH=. python3 -m platform.cli search 雾 --type drama
    PYTHONPATH=. python3 -m platform.cli detail demo_catalog demo-drama-001
    PYTHONPATH=. python3 -m platform.cli resolve demo_catalog demo-drama-001 ep-1
    PYTHONPATH=. python3 -m platform.cli serve --port 8080
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, List, Optional

from platform.aggregator import default_aggregator
from platform.errors import PlatformError
from platform.models import MediaType


def _print(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _handle_sources(_: argparse.Namespace) -> int:
    _print({"sources": default_aggregator.sources()})
    return 0


def _handle_health(_: argparse.Namespace) -> int:
    _print(default_aggregator.health())
    return 0


def _handle_search(args: argparse.Namespace) -> int:
    media_type = MediaType(args.type) if args.type else None
    sources = [s for s in (args.sources or "").split(",") if s.strip()] or None
    outcome = default_aggregator.search(args.query, media_type=media_type, page=args.page, sources=sources)
    _print(outcome.to_dict())
    return 0


def _handle_detail(args: argparse.Namespace) -> int:
    _print(default_aggregator.detail(args.source, args.id))
    return 0


def _handle_resolve(args: argparse.Namespace) -> int:
    _print(default_aggregator.resolve(args.source, args.id, args.episode))
    return 0


def _handle_serve(args: argparse.Namespace) -> int:
    from platform.server import serve

    serve(host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lets-go-look", description="多源聚合平台 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("sources", help="列出全部来源及接入状态").set_defaults(func=_handle_sources)
    sub.add_parser("health", help="输出服务与来源健康状态").set_defaults(func=_handle_health)

    p_search = sub.add_parser("search", help="多源检索并合并去重")
    p_search.add_argument("query")
    p_search.add_argument("--type", choices=[mt.value for mt in MediaType])
    p_search.add_argument("--page", type=int, default=1)
    p_search.add_argument("--sources", help="逗号分隔的 adapter_id，缺省为全部可用来源")
    p_search.set_defaults(func=_handle_search)

    p_detail = sub.add_parser("detail", help="取详情与分集 / 章节")
    p_detail.add_argument("source")
    p_detail.add_argument("id")
    p_detail.set_defaults(func=_handle_detail)

    p_resolve = sub.add_parser("resolve", help="解析可播放 / 可阅读地址")
    p_resolve.add_argument("source")
    p_resolve.add_argument("id")
    p_resolve.add_argument("episode", nargs="?", default=None)
    p_resolve.set_defaults(func=_handle_resolve)

    p_serve = sub.add_parser("serve", help="启动 HTTP 聚合服务")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8080)
    p_serve.set_defaults(func=_handle_serve)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except PlatformError as error:
        _print({"error": error.to_dict()})
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
