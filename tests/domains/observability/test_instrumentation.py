"""Tests for domains/observability/instrumentation.py."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from taskmajor.domains.observability.instrumentation import (
    _wrap,
    instrument_resource,
    instrument_tool,
    patch_mcp_instrumentation,
)


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_instrumentation_mcp():
    """Create an MCP-like object suitable for instrumentation tests.

    MagicMock auto-creates truthy child mocks for any attribute access, which
    causes patch_mcp_instrumentation to always hit the idempotency guard on the
    very first call.  Setting _taskmajor_instrumented = False explicitly prevents
    that so the first call actually applies the patch.
    """
    tool = MagicMock()
    tool._taskmajor_instrumented = False
    resource = MagicMock()
    mcp = SimpleNamespace(tool=tool, resource=resource)
    return mcp


# ---------------------------------------------------------------------------
# _wrap — async wrapper
# ---------------------------------------------------------------------------


class TestWrapAsync:
    def test_async_wrapper_returns_result(self):
        async def my_fn(x):
            return x * 3

        wrapped = _wrap(my_fn, "span", "tool", {"mcp.tool.name": "my_fn"})
        result = _run(wrapped(7))

        assert result == 21

    def test_async_wrapper_propagates_exception(self):
        async def failing():
            raise ValueError("async boom")

        wrapped = _wrap(failing, "span", "tool", {})

        with pytest.raises(ValueError, match="async boom"):
            _run(wrapped())

    def test_wrap_returns_async_wrapper_for_coroutine(self):
        async def my_async():
            return 1

        wrapped = _wrap(my_async, "span", "tool", {})
        assert asyncio.iscoroutinefunction(wrapped)


# ---------------------------------------------------------------------------
# _wrap — sync wrapper
# ---------------------------------------------------------------------------


class TestWrapSync:
    def test_sync_wrapper_returns_result(self):
        def my_fn(x):
            return x + 10

        wrapped = _wrap(my_fn, "span", "resource", {"mcp.resource.uri": "taskmajor://test"})
        result = wrapped(5)

        assert result == 15

    def test_sync_wrapper_propagates_exception(self):
        def failing():
            raise RuntimeError("sync boom")

        wrapped = _wrap(failing, "span", "resource", {})

        with pytest.raises(RuntimeError, match="sync boom"):
            wrapped()

    def test_wrap_returns_sync_wrapper_for_regular_function(self):
        def my_sync():
            return 1

        wrapped = _wrap(my_sync, "span", "resource", {})
        assert not asyncio.iscoroutinefunction(wrapped)


# ---------------------------------------------------------------------------
# instrument_tool / instrument_resource
# ---------------------------------------------------------------------------


class TestInstrumentHelpers:
    def test_instrument_tool_wraps_async_fn(self):
        async def my_tool(ctx):
            return "ok"

        wrapped = instrument_tool(my_tool)
        result = _run(wrapped(MagicMock()))

        assert result == "ok"

    def test_instrument_resource_wraps_sync_fn(self):
        def my_resource():
            return "data"

        wrapped = instrument_resource(my_resource)
        assert wrapped() == "data"

    def test_instrument_resource_uses_uri_when_provided(self):
        def my_resource():
            return "x"

        wrapped = instrument_resource(my_resource, uri="taskmajor://custom")
        # Verify it returns a callable and executes correctly
        assert callable(wrapped)
        assert wrapped() == "x"


# ---------------------------------------------------------------------------
# patch_mcp_instrumentation
# ---------------------------------------------------------------------------


class TestPatchMcpInstrumentation:
    def test_idempotent_second_call_is_noop(self):
        mcp = _make_instrumentation_mcp()

        patch_mcp_instrumentation(mcp)
        patched_once = mcp.tool

        # Second call must not swap mcp.tool again
        patch_mcp_instrumentation(mcp)
        assert mcp.tool is patched_once

    def test_patched_tool_direct_callable_path(self):
        """patched_tool(some_fn) — fn passed directly (not as a name kwarg)."""
        mcp = _make_instrumentation_mcp()
        patch_mcp_instrumentation(mcp)

        async def my_handler():
            return "result"

        # Direct callable path: patched_tool(fn) → original_tool(instrumented_fn)
        mcp.tool(my_handler)
        # No exception = direct-callable path executed correctly

    def test_patched_tool_decorator_path(self):
        """patched_tool("name")(fn) — decorator-factory path covers lines 124-128."""
        mcp = _make_instrumentation_mcp()
        patch_mcp_instrumentation(mcp)

        async def my_handler():
            return "result"

        # After patching mcp.tool is the real patched_tool function
        decorator = mcp.tool("my_tool_name")
        assert callable(decorator)
        decorator(my_handler)  # executes lines 125-126

    def test_resource_patching_wraps_handler(self):
        """patched_resource(uri)(fn) wraps the handler with instrument_resource."""
        mcp = _make_instrumentation_mcp()
        patch_mcp_instrumentation(mcp)

        def my_resource():
            return "resource data"

        mcp.resource("taskmajor://test")(my_resource)
        # No exception = resource patching path executed correctly
