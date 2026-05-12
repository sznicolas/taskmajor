"""Instrumentation helpers for MCP tools and resources."""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastmcp import FastMCP

from opentelemetry import metrics, trace
from opentelemetry.trace import StatusCode

__all__ = ["instrument_tool", "instrument_resource", "patch_mcp_instrumentation"]

_tracer = trace.get_tracer("taskmajor")
_meter = metrics.get_meter("taskmajor")

_PATCHED_ATTR = "_taskmajor_instrumented"

_call_counter = _meter.create_counter(
    name="mcp.calls.total",
    description="Total number of MCP tool/resource calls",
    unit="1",
)
_latency_histogram = _meter.create_histogram(
    name="mcp.call.duration",
    description="Duration of MCP tool/resource calls",
    unit="ms",
)

logger = logging.getLogger(__name__)


def _wrap(fn: Callable, span_name: str, call_type: str, extra_attrs: dict[str, str]) -> Callable:
    """Wrap *fn* with OTel span, metrics recording, and structured logging."""

    base_attrs = {"mcp.call.type": call_type, **extra_attrs}

    @functools.wraps(fn)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        with _tracer.start_as_current_span(span_name, attributes=base_attrs) as span:
            start = time.monotonic()
            try:
                result = await fn(*args, **kwargs)
                span.set_attribute("mcp.call.status", "ok")
                _call_counter.add(1, {**base_attrs, "mcp.call.status": "ok"})
                return result
            except Exception as exc:
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
                span.set_attribute("mcp.call.status", "error")
                _call_counter.add(1, {**base_attrs, "mcp.call.status": "error"})
                logger.exception("MCP %s %r failed", call_type, span_name)
                raise
            finally:
                elapsed_ms = (time.monotonic() - start) * 1000
                _latency_histogram.record(elapsed_ms, base_attrs)

    @functools.wraps(fn)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        with _tracer.start_as_current_span(span_name, attributes=base_attrs) as span:
            start = time.monotonic()
            try:
                result = fn(*args, **kwargs)
                span.set_attribute("mcp.call.status", "ok")
                _call_counter.add(1, {**base_attrs, "mcp.call.status": "ok"})
                return result
            except Exception as exc:
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
                span.set_attribute("mcp.call.status", "error")
                _call_counter.add(1, {**base_attrs, "mcp.call.status": "error"})
                logger.exception("MCP %s %r failed", call_type, span_name)
                raise
            finally:
                elapsed_ms = (time.monotonic() - start) * 1000
                _latency_histogram.record(elapsed_ms, base_attrs)

    return async_wrapper if asyncio.iscoroutinefunction(fn) else sync_wrapper


def instrument_tool(fn: Callable) -> Callable:
    """Wrap a MCP tool handler with OTel instrumentation."""
    return _wrap(
        fn, span_name=fn.__name__, call_type="tool", extra_attrs={"mcp.tool.name": fn.__name__}
    )


def instrument_resource(fn: Callable, uri: str | None = None) -> Callable:
    """Wrap a MCP resource handler with OTel instrumentation."""
    resource_uri = uri or fn.__name__
    return _wrap(
        fn,
        span_name=resource_uri,
        call_type="resource",
        extra_attrs={"mcp.resource.uri": resource_uri},
    )


def patch_mcp_instrumentation(mcp: FastMCP) -> None:
    """Apply OTel instrumentation patches to a FastMCP instance.

    Wraps mcp.tool and mcp.resource so every registered handler is
    automatically instrumented. Idempotent — safe to call multiple times
    on the same instance.

    Should be called once in create_mcp() immediately after the FastMCP
    instance is created, before any tools or resources are registered.
    """
    if getattr(mcp.tool, _PATCHED_ATTR, False):
        return  # already patched

    original_tool = mcp.tool

    def patched_tool(name_or_fn=None, **kwargs):
        if callable(name_or_fn):
            return original_tool(instrument_tool(name_or_fn), **kwargs)

        def decorator(fn: Callable) -> Callable:
            inner = original_tool(name_or_fn, **kwargs)
            return inner(instrument_tool(fn))

        return decorator

    patched_tool._taskmajor_instrumented = True  # type: ignore[attr-defined]
    mcp.tool = patched_tool  # type: ignore[method-assign]

    original_resource = mcp.resource

    def patched_resource(uri: str, **kwargs):
        decorator = original_resource(uri, **kwargs)

        def instrumented_decorator(fn: Callable) -> Callable:
            return decorator(instrument_resource(fn, uri))

        return instrumented_decorator

    mcp.resource = patched_resource  # type: ignore[method-assign]
