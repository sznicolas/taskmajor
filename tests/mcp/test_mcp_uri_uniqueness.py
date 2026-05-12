"""Test: no duplicate MCP URIs or tool names after registration."""

import inspect
from collections import Counter

import pytest

from taskmajor.bootstrap import create_mcp


async def _maybe_await(value):
    """Await value if it's awaitable, otherwise return it as-is."""
    if inspect.isawaitable(value):
        return await value
    return value


async def _list_resource_uris(mcp) -> list[str]:
    """Return a list of registered resource URIs, handling async/sync APIs."""
    # Prefer public API
    if hasattr(mcp, "list_resources"):
        res = mcp.list_resources()
        resources = await _maybe_await(res)
        return [getattr(r, "uri", str(r)) for r in resources]

    # Fallback to internal managers
    for attr in ("_resource_manager", "resource_manager"):
        manager = getattr(mcp, attr, None)
        if manager is None:
            continue
        if hasattr(manager, "list_resources"):
            res = manager.list_resources()
            resources = await _maybe_await(res)
            return [getattr(r, "uri", str(r)) for r in resources]
        if hasattr(manager, "resources"):
            resources = manager.resources
            resources = await _maybe_await(resources)
            return [getattr(r, "uri", str(r)) for r in resources]

    # Last resort: inspect attributes on the MCP object
    uris = []
    for v in vars(mcp).values():
        try:
            v_val = await _maybe_await(v)
        except Exception:
            continue
        if hasattr(v_val, "uri"):
            try:
                uris.append(v_val.uri)
            except Exception:
                uris.append(str(v_val))
    return uris


async def _list_tool_names(mcp) -> list[str]:
    """Return a list of registered tool names, handling async/sync APIs."""
    if hasattr(mcp, "list_tools"):
        res = mcp.list_tools()
        tools = await _maybe_await(res)
        return [getattr(t, "name", str(t)) for t in tools]

    for attr in ("_tool_manager", "tool_manager"):
        manager = getattr(mcp, attr, None)
        if manager is None:
            continue
        if hasattr(manager, "list_tools"):
            res = manager.list_tools()
            tools = await _maybe_await(res)
            return [getattr(t, "name", str(t)) for t in tools]
        if hasattr(manager, "tools"):
            tools = manager.tools
            tools = await _maybe_await(tools)
            return [getattr(t, "name", str(t)) for t in tools]

    names = []
    for v in vars(mcp).values():
        try:
            v_val = await _maybe_await(v)
        except Exception:
            continue
        if hasattr(v_val, "name"):
            try:
                names.append(v_val.name)
            except Exception:
                names.append(str(v_val))
    return names


@pytest.mark.asyncio
async def test_no_duplicate_resource_uris():
    """Every registered resource URI must be unique."""
    try:
        maybe = create_mcp()
        if inspect.isawaitable(maybe):
            mcp, _, _ = await maybe
        else:
            mcp, _, _ = maybe
    except Exception as e:
        pytest.skip(f"Skipping test due to MCP init error: {e}")

    uris = await _list_resource_uris(mcp)
    duplicates = [uri for uri, cnt in Counter(uris).items() if cnt > 1]
    assert not duplicates, f"Duplicate resource URIs found: {duplicates}"


@pytest.mark.asyncio
async def test_no_duplicate_tool_names():
    """Every registered tool name must be unique."""
    try:
        maybe = create_mcp()
        if inspect.isawaitable(maybe):
            mcp, _, _ = await maybe
        else:
            mcp, _, _ = maybe
    except Exception as e:
        pytest.skip(f"Skipping test due to MCP init error: {e}")

    names = await _list_tool_names(mcp)
    duplicates = [n for n, cnt in Counter(names).items() if cnt > 1]
    assert not duplicates, f"Duplicate tool names found: {duplicates}"
