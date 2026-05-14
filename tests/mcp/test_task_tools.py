"""Tests for mcp/tools/task_tools.py."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock

from fastmcp import FastMCP

from taskmajor.mcp.tools.task_tools import register_task_tools


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


def _mock_service():
    svc = MagicMock()
    svc.taskwarrior_client = MagicMock()
    svc.serialize_task = MagicMock(return_value={"uuid": "abc", "description": "test"})
    return svc


# ---------------------------------------------------------------------------
# query_tasks
# ---------------------------------------------------------------------------


class TestQueryTasksTool:
    def test_happy_path_returns_service_result(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.query_tasks.return_value = {"tasks": [], "total": 0}
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "query_tasks"))
        result = fn()

        assert result["success"] is True
        assert result["data"]["total"] == 0
        svc.query_tasks.assert_called_once()

    def test_passes_limit_and_offset_to_service(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.query_tasks.return_value = {"tasks": [], "total": 0}
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "query_tasks"))
        fn(sort=["-urgency"], limit=10, offset=5)

        call_kwargs = svc.query_tasks.call_args
        assert call_kwargs.kwargs["limit"] == 10
        assert call_kwargs.kwargs["offset"] == 5

    def test_value_error_returns_invalid_input(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.query_tasks.side_effect = ValueError("bad filter")
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "query_tasks"))
        result = fn()

        assert result["success"] is False
        assert result["error_code"] == "INVALID_INPUT"

    def test_exception_returns_internal_error(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.query_tasks.side_effect = RuntimeError("db error")
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "query_tasks"))
        result = fn()

        assert result["success"] is False
        assert result["error_code"] == "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------


class TestGetStatsTool:
    def test_happy_path(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.get_stats.return_value = {"by_status": {}, "total": 0}
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "get_stats"))
        result = fn()

        assert result["success"] is True
        svc.get_stats.assert_called_once()

    def test_exception_returns_internal_error(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.get_stats.side_effect = RuntimeError("error")
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "get_stats"))
        result = fn()

        assert result["success"] is False
        assert result["error_code"] == "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# next_task
# ---------------------------------------------------------------------------


class TestNextTaskTool:
    def test_happy_path(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.next_task.return_value = {"id": 1, "description": "do something"}
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "next_task"))
        result = fn()

        assert result["success"] is True
        svc.next_task.assert_called_once()

    def test_exception_returns_internal_error(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.next_task.side_effect = RuntimeError("error")
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "next_task"))
        result = fn()

        assert result["success"] is False
        assert result["error_code"] == "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# get_task
# ---------------------------------------------------------------------------


class TestGetTaskTool:
    def test_task_found_with_datetime_entry_and_modified(self):
        mcp = _make_mcp()
        svc = _mock_service()
        task = MagicMock()
        task.entry = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        task.modified = datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        svc.taskwarrior_client.get_task.return_value = task
        svc.serialize_task.return_value = {"uuid": "abc", "description": "test"}
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "get_task"))
        result = fn(task_id="abc")

        assert result["success"] is True
        assert result["data"]["entry"] == task.entry.isoformat()
        assert result["data"]["modified"] == task.modified.isoformat()

    def test_task_found_with_none_entry_and_modified(self):
        mcp = _make_mcp()
        svc = _mock_service()
        task = MagicMock()
        task.entry = None
        task.modified = None
        svc.taskwarrior_client.get_task.return_value = task
        svc.serialize_task.return_value = {"uuid": "abc"}
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "get_task"))
        result = fn(task_id="abc")

        assert result["success"] is True
        assert result["data"]["entry"] is None
        assert result["data"]["modified"] is None

    def test_task_found_with_non_datetime_entry_sets_none(self):
        """entry/modified present but lacking isoformat → serialized as None."""
        mcp = _make_mcp()
        svc = _mock_service()
        task = MagicMock()
        task.entry = 12345  # int — no isoformat
        task.modified = "2026-01-01"  # str — no isoformat
        svc.taskwarrior_client.get_task.return_value = task
        svc.serialize_task.return_value = {"uuid": "abc"}
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "get_task"))
        result = fn(task_id="abc")

        assert result["success"] is True
        assert result["data"]["entry"] is None
        assert result["data"]["modified"] is None

    def test_task_not_found_returns_task_not_found_error(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.taskwarrior_client.get_task.return_value = None
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "get_task"))
        result = fn(task_id="missing-id")

        assert result["success"] is False
        assert result["error_code"] == "TASK_NOT_FOUND"
        assert "missing-id" in result["error"]

    def test_get_task_raises_returns_internal_error(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.taskwarrior_client.get_task.side_effect = RuntimeError("connection error")
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "get_task"))
        result = fn(task_id="abc")

        assert result["success"] is False
        assert result["error_code"] == "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# done_task
# ---------------------------------------------------------------------------


class TestDoneTaskTool:
    def test_done_task_success(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.complete_task.return_value = True
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "done_task"))
        result = fn(task_id="abc")

        assert result["success"] is True
        assert "abc" in result["data"]
        svc.complete_task.assert_called_once_with("abc")

    def test_done_task_not_found_returns_task_not_found(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.complete_task.return_value = False
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "done_task"))
        result = fn(task_id="abc")

        assert result["success"] is False
        assert result["error_code"] == "TASK_NOT_FOUND"

    def test_done_task_exception_returns_internal_error(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.complete_task.side_effect = RuntimeError("error")
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "done_task"))
        result = fn(task_id="abc")

        assert result["success"] is False
        assert result["error_code"] == "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# add_task
# ---------------------------------------------------------------------------


class TestAddTaskTool:
    def test_add_task_success(self):
        mcp = _make_mcp()
        svc = _mock_service()
        created_task = MagicMock()
        svc.add_task.return_value = created_task
        svc.serialize_task.return_value = {"uuid": "new-abc", "description": "new task"}
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "add_task"))
        task_input = MagicMock()
        result = fn(task_input=task_input)

        assert result["success"] is True
        assert result["data"]["uuid"] == "new-abc"
        svc.add_task.assert_called_once_with(task_input)

    def test_add_task_value_error_returns_invalid_input(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.add_task.side_effect = ValueError("invalid description")
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "add_task"))
        result = fn(task_input=MagicMock())

        assert result["success"] is False
        assert result["error_code"] == "INVALID_INPUT"

    def test_add_task_exception_returns_internal_error(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.add_task.side_effect = RuntimeError("tw error")
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "add_task"))
        result = fn(task_input=MagicMock())

        assert result["success"] is False
        assert result["error_code"] == "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# update_task
# ---------------------------------------------------------------------------


class TestUpdateTaskTool:
    def test_update_task_success(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.update_task.return_value = MagicMock()
        svc.serialize_task.return_value = {"uuid": "abc", "priority": "H"}
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "update_task"))
        task_input = MagicMock()
        result = fn(task_id="abc", task_input=task_input)

        assert result["success"] is True
        svc.update_task.assert_called_once_with("abc", task_input)

    def test_update_task_value_error_returns_invalid_input(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.update_task.side_effect = ValueError("nothing changed")
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "update_task"))
        result = fn(task_id="abc", task_input=MagicMock())

        assert result["success"] is False
        assert result["error_code"] == "INVALID_INPUT"

    def test_update_task_exception_returns_internal_error(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.update_task.side_effect = RuntimeError("error")
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "update_task"))
        result = fn(task_id="abc", task_input=MagicMock())

        assert result["success"] is False
        assert result["error_code"] == "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# delete_task
# ---------------------------------------------------------------------------


class TestDeleteTaskTool:
    def test_delete_task_success(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.delete_task.return_value = True
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "delete_task"))
        result = fn(task_id="abc")

        assert result["success"] is True
        svc.delete_task.assert_called_once_with("abc")

    def test_delete_task_not_found_returns_task_not_found(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.delete_task.return_value = False
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "delete_task"))
        result = fn(task_id="abc")

        assert result["success"] is False
        assert result["error_code"] == "TASK_NOT_FOUND"

    def test_delete_task_exception_returns_internal_error(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.delete_task.side_effect = RuntimeError("error")
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "delete_task"))
        result = fn(task_id="abc")

        assert result["success"] is False
        assert result["error_code"] == "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# start_task / stop_task
# ---------------------------------------------------------------------------


class TestStartStopTaskTools:
    def test_start_task_success(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.start_task.return_value = True
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "start_task"))
        result = fn(task_id="abc")

        assert result["success"] is True
        svc.start_task.assert_called_once_with("abc")

    def test_start_task_not_found_returns_task_not_found(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.start_task.return_value = False
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "start_task"))
        result = fn(task_id="abc")

        assert result["success"] is False
        assert result["error_code"] == "TASK_NOT_FOUND"

    def test_start_task_exception_returns_internal_error(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.start_task.side_effect = RuntimeError("error")
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "start_task"))
        result = fn(task_id="abc")

        assert result["success"] is False
        assert result["error_code"] == "INTERNAL_ERROR"

    def test_stop_task_success(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.stop_task.return_value = True
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "stop_task"))
        result = fn(task_id="abc")

        assert result["success"] is True
        svc.stop_task.assert_called_once_with("abc")

    def test_stop_task_not_found_returns_task_not_found(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.stop_task.return_value = False
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "stop_task"))
        result = fn(task_id="abc")

        assert result["success"] is False
        assert result["error_code"] == "TASK_NOT_FOUND"

    def test_stop_task_exception_returns_internal_error(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.stop_task.side_effect = RuntimeError("error")
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "stop_task"))
        result = fn(task_id="abc")

        assert result["success"] is False
        assert result["error_code"] == "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# get_projects / get_tags / get_udas
# ---------------------------------------------------------------------------


class TestGetProjectsTagsUdas:
    def test_get_projects_happy_path(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.get_projects.return_value = {"projects": ["Work", "Home"], "total": 2}
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "get_projects"))
        result = fn()

        assert result["success"] is True
        assert result["data"]["total"] == 2

    def test_get_projects_exception_returns_internal_error(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.get_projects.side_effect = RuntimeError("error")
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "get_projects"))
        result = fn()

        assert result["success"] is False
        assert result["error_code"] == "INTERNAL_ERROR"

    def test_get_tags_happy_path(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.get_tags.return_value = {"tags": ["+work", "+urgent"], "total": 2}
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "get_tags"))
        result = fn()

        assert result["success"] is True

    def test_get_tags_exception_returns_internal_error(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.get_tags.side_effect = RuntimeError("error")
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "get_tags"))
        result = fn()

        assert result["success"] is False

    def test_get_udas_happy_path(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.get_udas.return_value = {"udas": [{"name": "complexity"}], "total": 1}
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "get_udas"))
        result = fn()

        assert result["success"] is True

    def test_get_udas_exception_returns_internal_error(self):
        mcp = _make_mcp()
        svc = _mock_service()
        svc.get_udas.side_effect = RuntimeError("error")
        register_task_tools(mcp, svc)

        fn = _run(_get_fn(mcp, "get_udas"))
        result = fn()

        assert result["success"] is False


# ---------------------------------------------------------------------------
# whitelist filtering
# ---------------------------------------------------------------------------


class TestTaskToolsWhitelist:
    def test_whitelist_filters_out_unlisted_tools(self):
        mcp = _make_mcp()
        svc = _mock_service()
        register_task_tools(mcp, svc, whitelist={"query_tasks", "add_task"})

        tool_names = {t.name for t in _run(mcp.list_tools())}
        assert "query_tasks" in tool_names
        assert "add_task" in tool_names
        assert "delete_task" not in tool_names
        assert "get_projects" not in tool_names

    def test_none_whitelist_registers_all_tools(self):
        mcp = _make_mcp()
        svc = _mock_service()
        register_task_tools(mcp, svc, whitelist=None)

        tool_names = {t.name for t in _run(mcp.list_tools())}
        expected = {
            "query_tasks", "get_stats", "next_task", "get_task",
            "done_task", "add_task", "update_task", "delete_task",
            "start_task", "stop_task", "get_projects", "get_tags", "get_udas",
        }
        assert expected.issubset(tool_names)

    def test_empty_whitelist_registers_no_tools(self):
        mcp = _make_mcp()
        svc = _mock_service()
        register_task_tools(mcp, svc, whitelist=set())

        tool_names = {t.name for t in _run(mcp.list_tools())}
        assert len(tool_names) == 0
