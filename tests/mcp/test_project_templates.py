"""Tests for mcp/templates/project_templates.py."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from taskmajor.mcp.templates.project_templates import register_project_templates


def _capture_get_project_tasks(task_service):
    """Register project templates and return the captured get_project_tasks handler."""
    captured: dict = {}

    class CaptureMCP:
        def resource(self, uri, **kwargs):
            def decorator(fn):
                captured[uri] = fn
                return fn

            return decorator

    register_project_templates(CaptureMCP(), task_service)
    return captured.get("taskmajor://project/{project_name}/tasks")


class TestGetProjectTasksTemplate:
    def test_happy_path_returns_json_task_list(self):
        task_service = MagicMock()
        task_service.query_tasks.return_value = [
            {"uuid": "abc", "description": "Buy milk", "project": "home"},
            {"uuid": "def", "description": "Fix bug", "project": "home"},
        ]

        fn = _capture_get_project_tasks(task_service)
        result = json.loads(fn("home"))

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["description"] == "Buy milk"

    def test_query_tasks_called_with_correct_filter(self):
        task_service = MagicMock()
        task_service.query_tasks.return_value = []

        fn = _capture_get_project_tasks(task_service)
        fn("myproject")

        task_service.query_tasks.assert_called_once_with(
            filters={"project": "myproject"},
            sort=["due", "priority", "description"],
            limit=None,
        )

    def test_exception_returns_error_json(self):
        task_service = MagicMock()
        task_service.query_tasks.side_effect = RuntimeError("DB unavailable")

        fn = _capture_get_project_tasks(task_service)
        result = json.loads(fn("work"))

        assert result["project"] == "work"
        assert "error" in result
        assert "DB unavailable" in result["error"]

    def test_handler_registered_under_correct_uri(self):
        captured: dict = {}

        class CaptureMCP:
            def resource(self, uri, **kwargs):
                def decorator(fn):
                    captured[uri] = fn
                    return fn

                return decorator

        register_project_templates(CaptureMCP(), MagicMock())
        assert "taskmajor://project/{project_name}/tasks" in captured
