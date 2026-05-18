"""Tests for mcp/tools/date_tools.py (37% coverage)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from fastmcp import FastMCP

from taskmajor.mcp.tools.date_tools import (
    _has_broken_minutes,
    _is_iso_duration,
    register_date_tools,
)

# ---------------------------------------------------------------------------
# _has_broken_minutes
# ---------------------------------------------------------------------------


class TestHasBrokenMinutes:
    @pytest.mark.parametrize(
        "expr",
        [
            "today+9h30m",
            "now+1h45m",
            "2026-01-01+2h15m",
        ],
    )
    def test_broken_minute_patterns_detected(self, expr: str):
        assert _has_broken_minutes(expr) is True

    @pytest.mark.parametrize(
        "expr",
        [
            "today+9h",
            "now+30m",
            "today+570min",
            "eom",
            "friday",
            "2026-05-15",
            "P2W",
        ],
    )
    def test_non_broken_patterns_not_detected(self, expr: str):
        assert _has_broken_minutes(expr) is False


# ---------------------------------------------------------------------------
# _is_iso_duration
# ---------------------------------------------------------------------------


class TestIsIsoDuration:
    @pytest.mark.parametrize("expr", ["P2W", "P1D", "PT1H", "P1Y2M3D"])
    def test_iso_duration_detected(self, expr: str):
        assert _is_iso_duration(expr) is True

    @pytest.mark.parametrize("expr", ["today", "eom", "2026-05-15", "friday"])
    def test_non_iso_duration_not_detected(self, expr: str):
        assert _is_iso_duration(expr) is False


# ---------------------------------------------------------------------------
# Helpers for tool access
# ---------------------------------------------------------------------------


def _make_mcp():
    return FastMCP("test")


def _run(coro):
    # Use asyncio.run for compatibility with modern Python event loop policy
    return asyncio.run(coro)


async def _get_fn(mcp: FastMCP, name: str):
    tool = await mcp.get_tool(name)
    assert tool is not None
    return tool.fn  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# resolve_date tool
# ---------------------------------------------------------------------------


class TestResolveDateTool:
    def test_resolve_date_happy_path(self):
        mcp = _make_mcp()
        tw = MagicMock()
        tw.task_calc.return_value = "2026-05-20T00:00:00Z"
        register_date_tools(mcp, tw)

        fn = _run(_get_fn(mcp, "resolve_date"))
        result = fn(expression="friday")

        assert result["success"] is True
        assert result["data"]["resolved"] == "2026-05-20T00:00:00Z"
        assert "date" in result["data"]
        assert "warning" not in result["data"]

    def test_resolve_date_broken_minutes_adds_warning(self):
        mcp = _make_mcp()
        tw = MagicMock()
        tw.task_calc.return_value = "2026-05-14T09:30:00Z"
        register_date_tools(mcp, tw)

        fn = _run(_get_fn(mcp, "resolve_date"))
        result = fn(expression="today+9h30m")

        assert result["success"] is True
        assert "warning" in result["data"]
        assert "broken" in result["data"]["warning"].lower() or "+" in result["data"]["warning"]

    def test_resolve_date_iso_duration_adds_warning_and_skips_split(self):
        mcp = _make_mcp()
        tw = MagicMock()
        tw.task_calc.return_value = "P14D"
        register_date_tools(mcp, tw)

        fn = _run(_get_fn(mcp, "resolve_date"))
        result = fn(expression="P2W")

        assert result["success"] is True
        assert "warning" in result["data"]
        assert result["data"]["resolved"] == "P14D"
        # No date/time split keys since we return early for ISO durations
        assert "date" not in result["data"]

    def test_resolve_date_task_calc_raises_returns_error(self):
        mcp = _make_mcp()
        tw = MagicMock()
        tw.task_calc.side_effect = RuntimeError("invalid expression")
        register_date_tools(mcp, tw)

        fn = _run(_get_fn(mcp, "resolve_date"))
        result = fn(expression="garbage!")

        assert result["success"] is False
        assert result["error"] is not None

    def test_resolve_date_no_time_part(self):
        mcp = _make_mcp()
        tw = MagicMock()
        tw.task_calc.return_value = "2026-05-20"
        register_date_tools(mcp, tw)

        fn = _run(_get_fn(mcp, "resolve_date"))
        result = fn(expression="friday")

        assert result["data"]["time"] is None


# ---------------------------------------------------------------------------
# validate_date tool
# ---------------------------------------------------------------------------


class TestValidateDateTool:
    def test_validate_date_valid_expression(self):
        mcp = _make_mcp()
        tw = MagicMock()
        tw.date_validator.return_value = True
        register_date_tools(mcp, tw)

        fn = _run(_get_fn(mcp, "validate_date"))
        result = fn(expression="tomorrow")

        assert result["success"] is True
        assert result["data"]["valid"] is True
        assert "warning" not in result["data"]

    def test_validate_date_broken_minutes_adds_warning(self):
        mcp = _make_mcp()
        tw = MagicMock()
        tw.date_validator.return_value = True
        register_date_tools(mcp, tw)

        fn = _run(_get_fn(mcp, "validate_date"))
        result = fn(expression="today+9h30m")

        assert result["success"] is True
        assert "warning" in result["data"]
        assert result["data"]["valid"] is True

    def test_validate_date_invalid_expression(self):
        mcp = _make_mcp()
        tw = MagicMock()
        tw.date_validator.return_value = False
        register_date_tools(mcp, tw)

        fn = _run(_get_fn(mcp, "validate_date"))
        result = fn(expression="not-a-date")

        assert result["success"] is True
        assert result["data"]["valid"] is False


# ---------------------------------------------------------------------------
# whitelist
# ---------------------------------------------------------------------------


class TestDateToolsWhitelist:
    def test_whitelist_excludes_validate_date(self):
        mcp = _make_mcp()
        tw = MagicMock()
        register_date_tools(mcp, tw, whitelist={"resolve_date"})
        tool_names = {t.name for t in _run(mcp.list_tools())}
        assert "resolve_date" in tool_names
        assert "validate_date" not in tool_names
