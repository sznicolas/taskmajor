"""Tests for mcp/tools/config_tools.py."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastmcp import FastMCP

import taskmajor.mcp.prompts  # noqa: F401 — ensures mcp/prompts/__init__.py is executed
from taskmajor.mcp.tools.config_tools import register_config_tools


def _make_mcp() -> FastMCP:
    return FastMCP("test")


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _get_fn(mcp: FastMCP, name: str):
    tool = await mcp.get_tool(name)
    assert tool is not None
    return tool.fn  # type: ignore[attr-defined]


def _mock_config_service():
    return MagicMock()


# ---------------------------------------------------------------------------
# prompts/__init__.py smoke test
# ---------------------------------------------------------------------------


def test_prompts_init_is_importable():
    assert taskmajor.mcp.prompts.__all__ == []


# ---------------------------------------------------------------------------
# get_config
# ---------------------------------------------------------------------------


class TestGetConfigTool:
    def test_happy_path_returns_config_dict(self):
        mcp = _make_mcp()
        svc = _mock_config_service()
        svc.get_all_config.return_value = {"rc.timezone": "UTC"}
        register_config_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "get_config"))
        result = fn()

        assert result["success"] is True
        assert result["data"] == {"rc.timezone": "UTC"}
        svc.get_all_config.assert_called_once()

    def test_exception_returns_internal_error(self):
        mcp = _make_mcp()
        svc = _mock_config_service()
        svc.get_all_config.side_effect = RuntimeError("config unavailable")
        register_config_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "get_config"))
        result = fn()

        assert result["success"] is False
        assert result["error_code"] == "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# set_timezone
# ---------------------------------------------------------------------------


class TestSetTimezoneTool:
    def test_success_returns_confirmation(self):
        mcp = _make_mcp()
        svc = _mock_config_service()
        register_config_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "set_timezone"))
        result = fn(timezone="Europe/Paris")

        assert result["success"] is True
        assert "Europe/Paris" in result["data"]
        svc.set_timezone.assert_called_once_with("Europe/Paris")

    def test_value_error_returns_invalid_input(self):
        mcp = _make_mcp()
        svc = _mock_config_service()
        svc.set_timezone.side_effect = ValueError("Unknown timezone 'Not/A/Zone'")
        register_config_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "set_timezone"))
        result = fn(timezone="Not/A/Zone")

        assert result["success"] is False
        assert result["error_code"] == "INVALID_INPUT"

    def test_exception_returns_config_error(self):
        mcp = _make_mcp()
        svc = _mock_config_service()
        svc.set_timezone.side_effect = RuntimeError("task command failed")
        register_config_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "set_timezone"))
        result = fn(timezone="UTC")

        assert result["success"] is False
        assert result["error_code"] == "CONFIG_ERROR"


# ---------------------------------------------------------------------------
# add_uda
# ---------------------------------------------------------------------------


class TestAddUdaTool:
    def test_success_returns_confirmation(self):
        mcp = _make_mcp()
        svc = _mock_config_service()
        register_config_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "add_uda"))
        uda_config = SimpleNamespace(name="complexity", uda_type="numeric")
        result = fn(uda_config=uda_config)

        assert result["success"] is True
        assert "complexity" in result["data"]
        svc.add_uda.assert_called_once_with(uda_config)

    def test_value_error_returns_invalid_input(self):
        mcp = _make_mcp()
        svc = _mock_config_service()
        svc.add_uda.side_effect = ValueError("invalid type")
        register_config_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "add_uda"))
        result = fn(uda_config=SimpleNamespace(name="bad", uda_type="unknown"))

        assert result["success"] is False
        assert result["error_code"] == "INVALID_INPUT"

    def test_exception_returns_config_error(self):
        mcp = _make_mcp()
        svc = _mock_config_service()
        svc.add_uda.side_effect = RuntimeError("tw error")
        register_config_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "add_uda"))
        result = fn(uda_config=SimpleNamespace(name="complexity", uda_type="numeric"))

        assert result["success"] is False
        assert result["error_code"] == "CONFIG_ERROR"


# ---------------------------------------------------------------------------
# delete_uda
# ---------------------------------------------------------------------------


class TestDeleteUdaTool:
    def test_success_returns_confirmation(self):
        mcp = _make_mcp()
        svc = _mock_config_service()
        register_config_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "delete_uda"))
        result = fn(name="complexity")

        assert result["success"] is True
        assert "complexity" in result["data"]
        svc.delete_uda.assert_called_once_with("complexity")

    def test_exception_returns_config_error(self):
        mcp = _make_mcp()
        svc = _mock_config_service()
        svc.delete_uda.side_effect = RuntimeError("not found")
        register_config_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "delete_uda"))
        result = fn(name="nonexistent")

        assert result["success"] is False
        assert result["error_code"] == "CONFIG_ERROR"


# ---------------------------------------------------------------------------
# define_context
# ---------------------------------------------------------------------------


class TestDefineContextTool:
    def test_success_returns_confirmation(self):
        mcp = _make_mcp()
        svc = _mock_config_service()
        register_config_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "define_context"))
        context = SimpleNamespace(name="work")
        result = fn(context=context)

        assert result["success"] is True
        assert "work" in result["data"]
        svc.define_context.assert_called_once_with(context)

    def test_exception_returns_config_error(self):
        mcp = _make_mcp()
        svc = _mock_config_service()
        svc.define_context.side_effect = RuntimeError("error")
        register_config_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "define_context"))
        result = fn(context=SimpleNamespace(name="work"))

        assert result["success"] is False
        assert result["error_code"] == "CONFIG_ERROR"


# ---------------------------------------------------------------------------
# delete_context
# ---------------------------------------------------------------------------


class TestDeleteContextTool:
    def test_success_returns_confirmation(self):
        mcp = _make_mcp()
        svc = _mock_config_service()
        register_config_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "delete_context"))
        result = fn(name="work")

        assert result["success"] is True
        assert "work" in result["data"]
        svc.delete_context.assert_called_once_with("work")

    def test_exception_returns_config_error(self):
        mcp = _make_mcp()
        svc = _mock_config_service()
        svc.delete_context.side_effect = RuntimeError("error")
        register_config_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "delete_context"))
        result = fn(name="work")

        assert result["success"] is False
        assert result["error_code"] == "CONFIG_ERROR"


# ---------------------------------------------------------------------------
# whitelist filtering
# ---------------------------------------------------------------------------


class TestConfigToolsWhitelist:
    def test_whitelist_filters_out_unlisted_tools(self):
        mcp = _make_mcp()
        svc = _mock_config_service()
        register_config_tools(mcp, svc, whitelist={"get_config", "set_timezone"})

        tool_names = {t.name for t in _run(mcp.list_tools())}
        assert "get_config" in tool_names
        assert "set_timezone" in tool_names
        assert "add_uda" not in tool_names
        assert "define_context" not in tool_names

    def test_none_whitelist_registers_all_tools(self):
        mcp = _make_mcp()
        svc = _mock_config_service()
        register_config_tools(mcp, svc, whitelist=None)

        tool_names = {t.name for t in _run(mcp.list_tools())}
        expected = {
            "get_config", "set_timezone", "add_uda", "delete_uda",
            "define_context", "delete_context",
        }
        assert expected.issubset(tool_names)

    def test_empty_whitelist_registers_no_tools(self):
        mcp = _make_mcp()
        svc = _mock_config_service()
        register_config_tools(mcp, svc, whitelist=set())

        tool_names = {t.name for t in _run(mcp.list_tools())}
        assert len(tool_names) == 0
