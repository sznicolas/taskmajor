"""Tests for domains/agent/resource_tools.py (0% coverage)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from taskmajor.domains.agent.resource_tools import (
    create_generic_resource_tool,
    create_resource_tools,
)


def _run(coro):
    # Use asyncio.run to avoid DeprecationWarning about event loop retrieval
    return asyncio.run(coro)


class FakeRunContext:
    """Minimal stand-in for pydantic_ai.RunContext."""


# ---------------------------------------------------------------------------
# create_resource_tools
# ---------------------------------------------------------------------------


def test_create_resource_tools_returns_empty_list():
    """create_resource_tools currently returns [] (populated at runtime)."""
    mcp_server = MagicMock()
    tools = create_resource_tools(mcp_server)
    assert tools == []


# ---------------------------------------------------------------------------
# create_generic_resource_tool — happy path
# ---------------------------------------------------------------------------


def test_create_generic_resource_tool_returns_tool_object():
    mcp_server = MagicMock()
    tool = create_generic_resource_tool(mcp_server)
    assert tool is not None
    assert tool.name == "read_mcp_resource"


def test_read_any_resource_returns_string_content():
    mcp_server = MagicMock()
    mcp_server.list_resources = AsyncMock(
        return_value=[SimpleNamespace(uri="taskmajor://tasks", name="Tasks")]
    )
    mcp_server.read_resource = AsyncMock(return_value="task content")

    tool = create_generic_resource_tool(mcp_server)
    ctx = FakeRunContext()

    result = _run(tool.function(ctx, uri="taskmajor://tasks"))
    assert result == "task content"


def test_read_any_resource_returns_list_content_joined():
    mcp_server = MagicMock()
    mcp_server.list_resources = AsyncMock(
        return_value=[SimpleNamespace(uri="taskmajor://tasks", name="Tasks")]
    )
    mcp_server.read_resource = AsyncMock(return_value=["item1", "item2"])

    tool = create_generic_resource_tool(mcp_server)
    ctx = FakeRunContext()

    result = _run(tool.function(ctx, uri="taskmajor://tasks"))
    assert "item1" in result
    assert "item2" in result


def test_read_any_resource_converts_other_types_to_str():
    mcp_server = MagicMock()
    mcp_server.list_resources = AsyncMock(
        return_value=[SimpleNamespace(uri="taskmajor://tasks", name="Tasks")]
    )
    mcp_server.read_resource = AsyncMock(return_value={"key": "value"})

    tool = create_generic_resource_tool(mcp_server)
    ctx = FakeRunContext()

    result = _run(tool.function(ctx, uri="taskmajor://tasks"))
    assert "key" in result


def test_read_any_resource_not_found_lists_available():
    mcp_server = MagicMock()
    mcp_server.list_resources = AsyncMock(
        return_value=[SimpleNamespace(uri="taskmajor://tasks", name="Tasks")]
    )

    tool = create_generic_resource_tool(mcp_server)
    ctx = FakeRunContext()

    result = _run(tool.function(ctx, uri="taskmajor://unknown"))
    assert "not found" in result
    assert "taskmajor://tasks" in result


def test_read_any_resource_exception_returns_error_string():
    mcp_server = MagicMock()
    mcp_server.list_resources = AsyncMock(side_effect=RuntimeError("connection lost"))

    tool = create_generic_resource_tool(mcp_server)
    ctx = FakeRunContext()

    result = _run(tool.function(ctx, uri="taskmajor://tasks"))
    assert "Error" in result
    assert "connection lost" in result
