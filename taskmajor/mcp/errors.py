"""
Structured error handling for MCP tools.

All MCP tool responses should be wrapped using ok() or fail() to produce
a consistent ToolResult shape that callers can rely on.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Error code constants
# ---------------------------------------------------------------------------

TASK_NOT_FOUND = "TASK_NOT_FOUND"
INVALID_INPUT = "INVALID_INPUT"
TASK_ALREADY_STARTED = "TASK_ALREADY_STARTED"
TASK_ALREADY_STOPPED = "TASK_ALREADY_STOPPED"
CONFIG_ERROR = "CONFIG_ERROR"
PROFILE_ERROR = "PROFILE_ERROR"
INTERNAL_ERROR = "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# ToolResult model
# ---------------------------------------------------------------------------


class ToolResult(BaseModel):
    success: bool
    error: str | None = None
    error_code: str | None = None
    data: Any | None = None


# ---------------------------------------------------------------------------
# Shortcut helpers
# ---------------------------------------------------------------------------


def ok(data: Any) -> dict:
    """Return a successful ToolResult payload."""
    return ToolResult(success=True, data=data).model_dump()


def fail(message: str, code: str = INTERNAL_ERROR) -> dict:
    """Return a failed ToolResult payload."""
    return ToolResult(success=False, error=message, error_code=code).model_dump()
