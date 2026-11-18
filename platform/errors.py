"""统一错误码与异常。

对外只暴露稳定的错误码，不把上游原始堆栈或接口细节透传给调用方
（见 docs/COMPLIANCE.md 与 docs/ARCHITECTURE.md 的统一约定）。
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional


class ErrorCode(str, Enum):
    BAD_REQUEST = "BAD_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    SOURCE_DISABLED = "SOURCE_DISABLED"      # 未授权 / 闭源来源，拒绝服务
    SOURCE_NOT_READY = "SOURCE_NOT_READY"    # 骨架已留，上游尚未实现或授权未到
    UPSTREAM_ERROR = "UPSTREAM_ERROR"        # 上游接口异常
    RATE_LIMITED = "RATE_LIMITED"            # 触发上游频次限制
    INTERNAL_ERROR = "INTERNAL_ERROR"


class PlatformError(Exception):
    """平台层异常基类，携带稳定错误码与来源标识。"""

    code: ErrorCode = ErrorCode.INTERNAL_ERROR

    def __init__(
        self,
        message: str,
        *,
        source: Optional[str] = None,
        detail: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.source = source
        self.detail = detail or {}

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code.value, "message": self.message}
        if self.source:
            payload["source"] = self.source
        if self.detail:
            payload["detail"] = self.detail
        return payload


class BadRequest(PlatformError):
    code = ErrorCode.BAD_REQUEST


class NotFound(PlatformError):
    code = ErrorCode.NOT_FOUND


class SourceDisabled(PlatformError):
    code = ErrorCode.SOURCE_DISABLED


class SourceNotReady(PlatformError):
    code = ErrorCode.SOURCE_NOT_READY


class UpstreamError(PlatformError):
    code = ErrorCode.UPSTREAM_ERROR


class RateLimited(PlatformError):
    code = ErrorCode.RATE_LIMITED


def normalize_exception(exc: Exception, source: Optional[str] = None) -> PlatformError:
    """把适配器抛出的异常归一到平台错误码。

    适配器约定：PermissionError 表示未授权禁用，NotImplementedError 表示尚未实现。
    """
    if isinstance(exc, PlatformError):
        if source and not exc.source:
            exc.source = source
        return exc
    if isinstance(exc, PermissionError):
        return SourceDisabled(str(exc) or "来源未授权", source=source)
    if isinstance(exc, NotImplementedError):
        return SourceNotReady(str(exc) or "来源尚未实现", source=source)
    return UpstreamError(
        "上游调用失败",
        source=source,
        detail={"error": type(exc).__name__},
    )
