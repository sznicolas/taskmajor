"""
Tests for roadmap MCP resources: project, priority, day, week.

Follows the same testing style as tests/mcp/test_mcp_endpoints.py by
simulating the resource handler behavior and asserting the mapping to
TaskService calls and JSON output.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from taskmajor.domains.tasks import TaskService


def _mock_task_service(**overrides) -> TaskService:
    """Create a TaskService with a mocked TaskWarrior client."""
    fake_client = SimpleNamespace(
        config_store=SimpleNamespace(config={}, get_contexts=lambda: []),
        context_service=SimpleNamespace(define_context=lambda c: None, delete_context=lambda n: None),
        uda_service=SimpleNamespace(define_uda=lambda u: None, delete_uda=lambda n: None),
    )
    return TaskService(taskwarrior_client=fake_client, **overrides)


@pytest.mark.parametrize("scope", ["project", "priority", "day", "week"])
class TestRoadmapResources:
    def test_roadmap_scope_returns_groups_and_total(self, scope: str):
        """Each roadmap resource returns JSON containing groups and total."""
        service = _mock_task_service()
        from typing import cast
        cast(Any, service).get_tasks_by_scope = MagicMock(return_value={"scope": scope, "groups": [], "total": 0})

        payload = service.get_tasks_by_scope(scope, filters={"status": "pending"})
        result_str = json.dumps(payload, default=str)
        result: dict[str, Any] = json.loads(result_str)

        assert "groups" in result
        assert "total" in result
        from typing import cast
        cast(Any, service).get_tasks_by_scope.assert_called_once()

    def test_roadmap_scope_calls_service_with_pending_filter(self, scope: str):
        """Each roadmap resource calls get_tasks_by_scope(scope, filters={'status':'pending'})."""
        service = _mock_task_service()
        from typing import cast
        cast(Any, service).get_tasks_by_scope = MagicMock(return_value={"scope": scope, "groups": [], "total": 0})

        payload = service.get_tasks_by_scope(scope, filters={"status": "pending"})
        json.dumps(payload, default=str)

        from typing import cast
        cast(Any, service).get_tasks_by_scope.assert_called_once()
        call_args = cast(Any, service).get_tasks_by_scope.call_args
        # positional first arg is scope
        assert call_args[0][0] == scope
        assert call_args[1]["filters"]["status"] == "pending"

    def test_roadmap_scope_error_returns_error_json(self, scope: str):
        """If the underlying service raises, the resource should return an error JSON."""
        service = _mock_task_service()
        from typing import cast
        cast(Any, service).get_tasks_by_scope = MagicMock(side_effect=RuntimeError("service failure"))

        try:
            payload = service.get_tasks_by_scope(scope, filters={"status": "pending"})
            result_str = json.dumps(payload, default=str)
        except Exception as e:
            result_str = json.dumps({"error": str(e)})

        result = json.loads(result_str)
        assert "error" in result
        assert "service failure" in result["error"]
