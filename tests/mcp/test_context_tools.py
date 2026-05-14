"""Tests for mcp/tools/context_tools.py (48% coverage)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastmcp import FastMCP

from taskmajor.mcp.tools.context_tools import register_context_tools


def _make_mcp() -> FastMCP:
    return FastMCP("test")


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


async def _get_fn(mcp: FastMCP, name: str):
    tool = await mcp.get_tool(name)
    return tool.fn


# ---------------------------------------------------------------------------
# list_contexts
# ---------------------------------------------------------------------------


class TestListContexts:
    def test_list_contexts_happy_path(self):
        mcp = _make_mcp()
        service = MagicMock()
        service.list_contexts.return_value = [
            SimpleNamespace(name="work", read_filter="+work", write_filter="+work", active=True)
        ]
        service.get_current_context.return_value = "work"

        register_context_tools(mcp, service)
        fn = _run(_get_fn(mcp, "list_contexts"))
        result = fn()

        assert result["active"] == "work"
        assert len(result["contexts"]) == 1
        assert result["contexts"][0]["name"] == "work"

    def test_list_contexts_service_raises_returns_error(self):
        mcp = _make_mcp()
        service = MagicMock()
        service.list_contexts.side_effect = RuntimeError("TW error")

        register_context_tools(mcp, service)
        fn = _run(_get_fn(mcp, "list_contexts"))
        result = fn()

        assert "error" in result


# ---------------------------------------------------------------------------
# set_context
# ---------------------------------------------------------------------------


class TestSetContext:
    def test_set_context_success(self):
        mcp = _make_mcp()
        service = MagicMock()
        service.set_context.return_value = True

        register_context_tools(mcp, service)
        fn = _run(_get_fn(mcp, "set_context"))
        result = fn(name="work")

        assert "work" in result
        assert "activated" in result.lower()
        service.set_context.assert_called_once_with("work")

    def test_set_context_service_raises_returns_error_string(self):
        mcp = _make_mcp()
        service = MagicMock()
        service.set_context.side_effect = ValueError("no such context")

        register_context_tools(mcp, service)
        fn = _run(_get_fn(mcp, "set_context"))
        result = fn(name="nonexistent")

        assert "Failed" in result or "failed" in result
        assert "nonexistent" in result


# ---------------------------------------------------------------------------
# unset_context
# ---------------------------------------------------------------------------


class TestUnsetContext:
    def test_unset_context_success(self):
        mcp = _make_mcp()
        service = MagicMock()
        service.unset_context.return_value = True

        register_context_tools(mcp, service)
        fn = _run(_get_fn(mcp, "unset_context"))
        result = fn()

        assert "deactivated" in result.lower() or "Context" in result
        service.unset_context.assert_called_once()

    def test_unset_context_service_raises_returns_error_string(self):
        mcp = _make_mcp()
        service = MagicMock()
        service.unset_context.side_effect = RuntimeError("internal error")

        register_context_tools(mcp, service)
        fn = _run(_get_fn(mcp, "unset_context"))
        result = fn()

        assert "Failed" in result or "failed" in result


# ---------------------------------------------------------------------------
# whitelist filtering
# ---------------------------------------------------------------------------


class TestContextToolsWhitelist:
    def test_whitelist_filters_out_tools(self):
        mcp = _make_mcp()
        service = MagicMock()
        register_context_tools(mcp, service, whitelist={"list_contexts"})
        tool_names = {t.name for t in _run(mcp.list_tools())}
        assert "list_contexts" in tool_names
        assert "set_context" not in tool_names
        assert "unset_context" not in tool_names

    def test_none_whitelist_registers_all(self):
        mcp = _make_mcp()
        service = MagicMock()
        register_context_tools(mcp, service, whitelist=None)
        tool_names = {t.name for t in _run(mcp.list_tools())}
        assert {"list_contexts", "set_context", "unset_context"}.issubset(tool_names)
