"""
Fault injection primitives shared by every mock tool.

Section 19 of the brief requires we can test: successful execution, tool
failure, malformed input, missing information, API timeout, duplicate
requests, and incorrect AI decisions — all without touching real systems.

Every mock tool in this package accepts an optional `fault` argument on its
calls. This module defines the fault vocabulary and a small exception
hierarchy so callers (the event logger, shadow engine, tests) can catch
specific failure classes rather than parsing error strings.
"""

from __future__ import annotations

from enum import Enum


class FaultType(str, Enum):
    NONE = "none"
    TOOL_FAILURE = "tool_failure"  # e.g. simulated DB/service outage
    MALFORMED_INPUT = "malformed_input"  # caller sent unusable data
    MISSING_INFORMATION = "missing_information"  # required field absent
    API_TIMEOUT = "api_timeout"  # simulated slow/unresponsive service
    DUPLICATE_REQUEST = "duplicate_request"  # same request submitted twice


class MockToolError(Exception):
    """Base class for all mock-tool failures."""

    def __init__(self, message: str, fault_type: FaultType):
        super().__init__(message)
        self.fault_type = fault_type


class ToolFailureError(MockToolError):
    def __init__(self, message: str = "Simulated tool failure."):
        super().__init__(message, FaultType.TOOL_FAILURE)


class MalformedInputError(MockToolError):
    def __init__(self, message: str = "Input could not be parsed."):
        super().__init__(message, FaultType.MALFORMED_INPUT)


class MissingInformationError(MockToolError):
    def __init__(self, message: str = "Required information is missing."):
        super().__init__(message, FaultType.MISSING_INFORMATION)


class ApiTimeoutError(MockToolError):
    def __init__(self, message: str = "Simulated API timeout."):
        super().__init__(message, FaultType.API_TIMEOUT)


class DuplicateRequestError(MockToolError):
    def __init__(self, message: str = "This request has already been processed."):
        super().__init__(message, FaultType.DUPLICATE_REQUEST)


_FAULT_EXCEPTIONS: dict[FaultType, type[MockToolError]] = {
    FaultType.TOOL_FAILURE: ToolFailureError,
    FaultType.MALFORMED_INPUT: MalformedInputError,
    FaultType.MISSING_INFORMATION: MissingInformationError,
    FaultType.API_TIMEOUT: ApiTimeoutError,
    FaultType.DUPLICATE_REQUEST: DuplicateRequestError,
}


def maybe_raise(fault: FaultType) -> None:
    """Raise the exception matching `fault`, or do nothing if FaultType.NONE.

    Every mock tool method calls this first, so a caller (tests, the shadow
    engine) can force any failure mode deterministically instead of relying
    on randomness.
    """
    if fault == FaultType.NONE:
        return
    exc_cls = _FAULT_EXCEPTIONS.get(fault)
    if exc_cls is None:
        raise ValueError(f"Unknown fault type: {fault!r}")
    raise exc_cls()
