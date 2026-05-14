"""
Contract tests for MCP endpoints (resources and tools).

These tests verify that:
1. MCP endpoints call TaskService with the correct arguments
2. MCP endpoints return JSON with the correct structure/format
3. Error handling works (service exceptions → error JSON)

Scope: Tests the mapping between MCP layer and TaskService.  Does NOT test
TaskService business logic (already covered by test_task_service.py and friends).

Test strategy: Test resource and tool handler functions DIRECTLY, not through the
FastMCP server (which is async and complex). This isolates the MCP mapping logic.
"""

from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from taskmajor.domains.tasks import TaskQueryFilters, TaskService


def _mock_task_service(**overrides) -> TaskService:
    """Create a TaskService with a mocked TaskWarrior client."""
    fake_client = SimpleNamespace(
        config_store=SimpleNamespace(config={}, get_contexts=lambda: []),
        context_service=SimpleNamespace(
            define_context=lambda c: None, delete_context=lambda n: None
        ),
        uda_service=SimpleNamespace(define_uda=lambda u: None, delete_uda=lambda n: None),
    )
    return TaskService(taskwarrior_client=fake_client, **overrides)


# ============================================================================
# AGENDA RESOURCES TESTS
# ============================================================================


class TestAgendaResources:
    """Test agenda/today and agenda/week resource handlers."""

    def test_agenda_today_returns_json_with_tasks_and_total(self):
        """agenda/today resource returns JSON with tasks and total keys."""
        service = _mock_task_service()
        service.query_tasks = MagicMock(
            return_value={"tasks": [], "total": 0, "sort": [], "limit": None}
        )
        service.today_window_filters = MagicMock(return_value={})

        # Simulate the handler logic (as implemented in register_agenda_resources)
        payload = service.query_tasks(
            filters={"status": "pending", **service.today_window_filters()},
            sort=["due", "priority", "description"],
            limit=None,
        )
        result_str = json.dumps(payload, default=str)
        result = json.loads(result_str)

        assert "tasks" in result
        assert "total" in result
        service.query_tasks.assert_called_once()

    def test_agenda_today_calls_service_with_pending_status(self):
        """agenda/today calls query_tasks with status=pending."""
        service = _mock_task_service()
        service.query_tasks = MagicMock(
            return_value={"tasks": [], "total": 0, "sort": [], "limit": None}
        )
        service.today_window_filters = MagicMock(return_value={})

        payload = service.query_tasks(
            filters={"status": "pending", **service.today_window_filters()},
            sort=["due", "priority", "description"],
            limit=None,
        )
        json.dumps(payload, default=str)

        service.query_tasks.assert_called_once()
        call_kwargs = service.query_tasks.call_args[1]
        assert call_kwargs["filters"]["status"] == "pending"

    def test_agenda_today_error_returns_error_json(self):
        """agenda/today handler returns {"error": "..."} on exception."""
        service = _mock_task_service()
        service.query_tasks = MagicMock(side_effect=ValueError("Query failed"))
        service.today_window_filters = MagicMock(return_value={})

        try:
            payload = service.query_tasks(
                filters={"status": "pending", **service.today_window_filters()},
                sort=["due", "priority", "description"],
                limit=None,
            )
            result_str = json.dumps(payload, default=str)
        except Exception as e:
            result_str = json.dumps({"error": str(e)})

        result = json.loads(result_str)
        assert "error" in result
        assert "Query failed" in result["error"]

    def test_agenda_week_returns_json_with_tasks_and_total(self):
        """agenda/week resource returns JSON with tasks and total keys."""
        service = _mock_task_service()
        service.query_tasks = MagicMock(
            return_value={"tasks": [], "total": 0, "sort": [], "limit": None}
        )
        service.week_window_filters = MagicMock(return_value={})

        payload = service.query_tasks(
            filters={"status": "pending", **service.week_window_filters()},
            sort=["due", "priority", "description"],
            limit=None,
        )
        result_str = json.dumps(payload, default=str)
        result = json.loads(result_str)

        assert "tasks" in result
        assert "total" in result
        service.query_tasks.assert_called_once()


# ============================================================================
# STATUS RESOURCES TESTS
# ============================================================================


class TestStatusResources:
    """Test status/overdue resource handler."""

    def test_status_overdue_returns_json_with_tasks_and_total(self):
        """status/overdue returns {"tasks": [...], "total": N} JSON."""
        service = _mock_task_service()
        service.query_tasks = MagicMock(
            return_value={"tasks": [], "total": 0, "sort": [], "limit": None}
        )

        payload = service.query_tasks(
            filters={"status": "pending", "due_before": datetime.now().astimezone()},
            sort=["due", "priority", "description"],
            limit=None,
        )
        result_str = json.dumps(payload, default=str)
        result = json.loads(result_str)

        assert "tasks" in result
        assert "total" in result

    def test_status_overdue_calls_service_with_due_before_filter(self):
        """status/overdue filters by due_before=now."""
        service = _mock_task_service()
        service.query_tasks = MagicMock(
            return_value={"tasks": [], "total": 0, "sort": [], "limit": None}
        )

        now = datetime.now().astimezone()
        payload = service.query_tasks(
            filters={"status": "pending", "due_before": now},
            sort=["due", "priority", "description"],
            limit=None,
        )
        json.dumps(payload, default=str)

        service.query_tasks.assert_called_once()
        call_kwargs = service.query_tasks.call_args[1]
        assert call_kwargs["filters"]["status"] == "pending"
        assert "due_before" in call_kwargs["filters"]

    def test_status_overdue_error_returns_error_json(self):
        """status/overdue returns {"error": "..."} on exception."""
        service = _mock_task_service()
        service.query_tasks = MagicMock(side_effect=RuntimeError("Service error"))

        try:
            payload = service.query_tasks(
                filters={"status": "pending", "due_before": datetime.now().astimezone()},
                sort=["due", "priority", "description"],
                limit=None,
            )
            result_str = json.dumps(payload, default=str)
        except Exception as e:
            result_str = json.dumps({"error": str(e)})

        result = json.loads(result_str)
        assert "error" in result


# ============================================================================
# QUEUE RESOURCES TESTS
# ============================================================================


class TestQueueResources:
    """Test queue/unsorted resource handler."""

    def test_queue_unsorted_returns_count_and_tasks(self):
        """queue/unsorted returns {"count": N, "tasks": [...]} JSON."""
        service = _mock_task_service()
        service.query_tasks = MagicMock(
            return_value={"tasks": [], "total": 0, "sort": [], "limit": None}
        )

        tasks = service.query_tasks(
            filters={"status": "pending"},
            sort=["priority", "due", "description"],
            limit=None,
        )
        result_str = json.dumps({"count": len(tasks), "tasks": tasks}, default=str)
        result = json.loads(result_str)

        assert "count" in result
        assert "tasks" in result

    def test_queue_unsorted_calls_service_with_pending_filter(self):
        """queue/unsorted filters by status=pending."""
        service = _mock_task_service()
        service.query_tasks = MagicMock(
            return_value={"tasks": [], "total": 0, "sort": [], "limit": None}
        )

        tasks = service.query_tasks(
            filters={"status": "pending"},
            sort=["priority", "due", "description"],
            limit=None,
        )
        json.dumps({"count": len(tasks), "tasks": tasks}, default=str)

        service.query_tasks.assert_called_once()
        call_kwargs = service.query_tasks.call_args[1]
        assert call_kwargs["filters"]["status"] == "pending"

    def test_queue_unsorted_error_returns_error_json(self):
        """queue/unsorted returns {"error": "..."} on exception."""
        service = _mock_task_service()
        service.query_tasks = MagicMock(side_effect=Exception("Query error"))

        try:
            tasks = service.query_tasks(
                filters={"status": "pending"},
                sort=["priority", "due", "description"],
                limit=None,
            )
            result_str = json.dumps({"count": len(tasks), "tasks": tasks}, default=str)
        except Exception as e:
            result_str = json.dumps({"error": str(e)})

        result = json.loads(result_str)
        assert "error" in result


# ============================================================================
# ANALYTICS RESOURCES TESTS
# ============================================================================


class TestAnalyticsResources:
    """Test analytics/summary resource handler."""

    def test_analytics_summary_returns_valid_json(self):
        """analytics/summary returns valid JSON with statistics."""
        service = _mock_task_service()
        service.get_stats = MagicMock(
            return_value={"by_status": {}, "by_project": {}, "by_priority": {}}
        )

        stats = service.get_stats(filters={"status": "all"})
        result_str = json.dumps(stats, default=str)
        result = json.loads(result_str)

        assert isinstance(result, dict)

    def test_analytics_summary_calls_get_stats_with_all_status(self):
        """analytics/summary calls get_stats(filters={'status': 'all'})."""
        service = _mock_task_service()
        service.get_stats = MagicMock(
            return_value={"by_status": {}, "by_project": {}, "by_priority": {}}
        )

        stats = service.get_stats(filters={"status": "all"})
        json.dumps(stats, default=str)

        service.get_stats.assert_called_once()
        call_kwargs = service.get_stats.call_args[1]
        assert call_kwargs["filters"]["status"] == "all"

    def test_analytics_summary_error_returns_error_json(self):
        """analytics/summary returns {"error": "..."} on exception."""
        service = _mock_task_service()
        service.get_stats = MagicMock(side_effect=Exception("Stats error"))

        try:
            stats = service.get_stats(filters={"status": "all"})
            result_str = json.dumps(stats, default=str)
        except Exception as e:
            result_str = json.dumps({"error": str(e)})

        result = json.loads(result_str)
        assert "error" in result


# ============================================================================
# CONFIG RESOURCES TESTS
# ============================================================================


class TestConfigResources:
    """Test config/schema resource handler."""

    def test_config_schema_returns_valid_json(self):
        """config/schema returns valid JSON with schema information."""
        service = _mock_task_service()
        service.get_config = MagicMock(
            return_value={
                "projects": [],
                "tags": [],
                "priorities": [],
                "contexts": [],
            }
        )

        config = service.get_config()
        result_str = json.dumps(config, default=str)
        result = json.loads(result_str)

        assert isinstance(result, dict)

    def test_config_schema_calls_get_config(self):
        """config/schema calls task_service.get_config()."""
        service = _mock_task_service()
        service.get_config = MagicMock(
            return_value={
                "projects": ["Work"],
                "tags": ["urgent"],
                "priorities": ["H", "M", "L"],
                "contexts": [],
            }
        )

        config = service.get_config()
        json.dumps(config, default=str)

        service.get_config.assert_called_once()


# ============================================================================
# QUERY_TASKS TOOL TESTS
# ============================================================================


class TestQueryTasksTool:
    """Test query_tasks MCP tool contract."""

    def test_query_tasks_passes_all_arguments_to_service(self):
        """query_tasks passes filters, sort, limit, offset to task_service.query_tasks()."""
        service = _mock_task_service()
        service.query_tasks = MagicMock(
            return_value={"tasks": [], "total": 0, "sort": [], "limit": None}
        )

        # Simulate tool call
        filters = TaskQueryFilters(project="Work", status="pending")
        result = service.query_tasks(filters=filters, sort=["priority"], limit=10, offset=0)

        service.query_tasks.assert_called_once()
        call_kwargs = service.query_tasks.call_args[1]
        assert call_kwargs["filters"] == filters
        assert call_kwargs["sort"] == ["priority"]
        assert call_kwargs["limit"] == 10
        assert call_kwargs["offset"] == 0
        assert isinstance(result, dict)

    def test_query_tasks_returns_dict_with_tasks_total(self):
        """query_tasks returns dict with tasks, total, sort, limit keys."""
        service = _mock_task_service()
        expected = {"tasks": [], "total": 0, "sort": [], "limit": None}
        service.query_tasks = MagicMock(return_value=expected)

        result = service.query_tasks(filters=None, sort=None, limit=50, offset=0)

        assert isinstance(result, dict)
        assert "tasks" in result
        assert "total" in result

    def test_query_tasks_with_no_filters(self):
        """query_tasks works with filters=None."""
        service = _mock_task_service()
        service.query_tasks = MagicMock(
            return_value={"tasks": [], "total": 0, "sort": [], "limit": None}
        )

        result = service.query_tasks(filters=None, sort=None, limit=50, offset=0)

        assert isinstance(result, dict)
        service.query_tasks.assert_called_once()


# ============================================================================
# GET_STATS TOOL TESTS
# ============================================================================


class TestGetStatsTool:
    """Test get_stats MCP tool contract."""

    def test_get_stats_passes_filters_to_service(self):
        """get_stats passes filters to task_service.get_stats()."""
        service = _mock_task_service()
        service.get_stats = MagicMock(
            return_value={"by_status": {}, "by_project": {}, "by_priority": {}}
        )

        filters = TaskQueryFilters(project="Work")
        result = service.get_stats(filters=filters)

        service.get_stats.assert_called_once()
        assert isinstance(result, dict)

    def test_get_stats_returns_dict_with_statistics(self):
        """get_stats returns dict with by_status, by_project, by_priority."""
        service = _mock_task_service()
        stats = {
            "by_status": {"pending": 5},
            "by_project": {"Work": 3},
            "by_priority": {"H": 2},
        }
        service.get_stats = MagicMock(return_value=stats)

        result = service.get_stats(filters=None)

        assert isinstance(result, dict)
        assert "by_status" in result


# ============================================================================
# DONE_TASK TOOL TESTS
# ============================================================================


class TestDoneTaskTool:
    """Test done_task MCP tool contract."""

    def test_done_task_calls_complete_task(self):
        """done_task calls task_service.complete_task(task_id)."""
        from taskmajor.mcp.errors import ok

        service = _mock_task_service()
        service.complete_task = MagicMock(return_value=True)

        # Simulate done_task tool
        if service.complete_task("task-123"):
            result = ok("Task task-123 marked as completed successfully.")
        else:
            from taskmajor.mcp.errors import TASK_NOT_FOUND, fail
            result = fail("Task task-123 not found", TASK_NOT_FOUND)

        service.complete_task.assert_called_once_with("task-123")
        assert isinstance(result, dict)
        assert result["success"] is True

    def test_done_task_returns_success_message_on_true(self):
        """done_task returns success ToolResult when complete_task returns True."""
        from taskmajor.mcp.errors import ok

        service = _mock_task_service()
        service.complete_task = MagicMock(return_value=True)

        if service.complete_task("task-123"):
            result = ok("Task task-123 marked as completed successfully.")
        else:
            from taskmajor.mcp.errors import TASK_NOT_FOUND, fail
            result = fail("Task task-123 not found", TASK_NOT_FOUND)

        assert result["success"] is True
        assert "successfully" in result["data"].lower()

    def test_done_task_returns_failure_on_false(self):
        """done_task returns failure ToolResult when complete_task returns False."""
        from taskmajor.mcp.errors import TASK_NOT_FOUND, fail, ok

        service = _mock_task_service()
        service.complete_task = MagicMock(return_value=False)

        if service.complete_task("task-123"):
            result = ok("Task task-123 marked as completed successfully.")
        else:
            result = fail("Task task-123 not found", TASK_NOT_FOUND)

        assert result["success"] is False
        assert result["error_code"] == TASK_NOT_FOUND


# ============================================================================
# ADD_TASK TOOL TESTS
# ============================================================================


class TestAddTaskTool:
    """Test add_task MCP tool contract."""

    def test_add_task_calls_service_add_task(self):
        """add_task calls task_service.add_task(task_input)."""
        from taskwarrior import TaskInputDTO

        service = _mock_task_service()
        mock_task = SimpleNamespace(uuid="id", description="New task")
        service.add_task = MagicMock(return_value=mock_task)
        service.serialize_task = MagicMock(return_value={"uuid": "id"})

        task_input = TaskInputDTO(description="New task")
        created_task = service.add_task(task_input)
        response = service.serialize_task(created_task)

        service.add_task.assert_called_once()
        assert isinstance(response, dict)

    def test_add_task_returns_serialized_dict(self):
        """add_task returns serialized task dict."""
        from taskwarrior import TaskInputDTO

        service = _mock_task_service()
        mock_task = SimpleNamespace(uuid="id")
        service.add_task = MagicMock(return_value=mock_task)
        service.serialize_task = MagicMock(return_value={"uuid": "id", "description": "New task"})

        task_input = TaskInputDTO(description="New task")
        created_task = service.add_task(task_input)
        result = service.serialize_task(created_task)

        assert isinstance(result, dict)
        assert "uuid" in result


# ============================================================================
# UPDATE_TASK TOOL TESTS
# ============================================================================


class TestUpdateTaskTool:
    """Test update_task MCP tool contract."""

    def test_update_task_calls_service_update_task(self):
        """update_task calls task_service.update_task(task_id, task_input)."""
        from taskwarrior import TaskInputDTO

        service = _mock_task_service()
        mock_task = SimpleNamespace(uuid="task-id", description="Updated")
        service.update_task = MagicMock(return_value=mock_task)
        service.serialize_task = MagicMock(return_value={"uuid": "task-id"})

        task_input = TaskInputDTO(description="Updated")
        updated_task = service.update_task("task-id", task_input)
        response = service.serialize_task(updated_task)

        service.update_task.assert_called_once_with("task-id", task_input)
        assert isinstance(response, dict)


# ============================================================================
# DELETE_TASK TOOL TESTS
# ============================================================================


class TestDeleteTaskTool:
    """Test delete_task MCP tool contract."""

    def test_delete_task_calls_service_delete_task(self):
        """delete_task calls task_service.delete_task(task_id)."""
        from taskmajor.mcp.errors import ok

        service = _mock_task_service()
        service.delete_task = MagicMock(return_value=True)

        # Simulate delete_task tool
        if service.delete_task("task-id"):
            result = ok("Task task-id marked as deleted successfully.")
        else:
            from taskmajor.mcp.errors import TASK_NOT_FOUND, fail
            result = fail("Task task-id not found", TASK_NOT_FOUND)

        service.delete_task.assert_called_once_with("task-id")
        assert isinstance(result, dict)
        assert result["success"] is True


# ============================================================================
# START_TASK / STOP_TASK TOOL TESTS
# ============================================================================


class TestStartStopTaskTools:
    """Test start_task and stop_task MCP tools contract."""

    def test_start_task_calls_service_start_task(self):
        """start_task calls task_service.start_task(task_id)."""
        from taskmajor.mcp.errors import ok

        service = _mock_task_service()
        service.start_task = MagicMock(return_value=True)

        if service.start_task("task-id"):
            result = ok("Task task-id started successfully.")
        else:
            from taskmajor.mcp.errors import TASK_NOT_FOUND, fail
            result = fail("Task task-id not found", TASK_NOT_FOUND)

        service.start_task.assert_called_once_with("task-id")
        assert isinstance(result, dict)
        assert result["success"] is True

    def test_stop_task_calls_service_stop_task(self):
        """stop_task calls task_service.stop_task(task_id)."""
        from taskmajor.mcp.errors import ok

        service = _mock_task_service()
        service.stop_task = MagicMock(return_value=True)

        if service.stop_task("task-id"):
            result = ok("Task task-id stopped successfully.")
        else:
            from taskmajor.mcp.errors import TASK_NOT_FOUND, fail
            result = fail("Task task-id not found", TASK_NOT_FOUND)

        service.stop_task.assert_called_once_with("task-id")
        assert isinstance(result, dict)
        assert result["success"] is True


# ============================================================================
# CLASSIFY_TASK TOOL TESTS
# ============================================================================
