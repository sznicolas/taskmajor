from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock

import pytest
from taskwarrior import TaskInputDTO, TaskOutputDTO

from taskmajor.domains.tasks import Priority, TaskService


def _task(
    description: str,
    *,
    task_uuid: str,
    task_id: int = 1,
    status: str = "pending",
    project: str | None = None,
    priority: str | None = None,
    tags: list[str] | None = None,
    due: datetime | None = None,
    urgency: float | None = None,
    udas: dict | None = None,
) -> Any:
    payload = {
        "id": task_id,
        "uuid": uuid.UUID(task_uuid),
        "description": description,
        "status": status,
        "project": project,
        "priority": priority,
        "tags": tags or [],
        "udas": udas or {},
    }
    if due is not None:
        payload["due"] = due
    if urgency is not None:
        payload["urgency"] = urgency
    return TaskOutputDTO(**cast(Any, payload))

def test_add_task():
    """Test adding a new task."""
    mock_taskwarrior = Mock()
    mock_taskwarrior.add_task.return_value = _task(
        "Test task",
        task_uuid="12345678-1234-1234-1234-123456789012",
    )

    task_service = TaskService(mock_taskwarrior)
    task_input = TaskInputDTO(description="Test task", project="test_project")

    result = task_service.add_task(task_input)

    assert isinstance(result, TaskOutputDTO)
    assert result.uuid == uuid.UUID("12345678-1234-1234-1234-123456789012")
    assert result.description == "Test task"

def test_list_pending_tasks():
    """Test listing pending tasks."""
    mock_taskwarrior = Mock()
    mock_taskwarrior.get_tasks.return_value = [
        _task("Task 1", task_uuid="11111111-1111-1111-1111-111111111111"),
        _task("Task 2", task_uuid="22222222-2222-2222-2222-222222222222"),
    ]

    task_service = TaskService(mock_taskwarrior)
    result = task_service.list_pending_tasks()

    assert len(result) == 2
    assert all(task.status == "pending" for task in result)

def test_update_task():
    """Test updating a task with field changes."""
    mock_taskwarrior = Mock()
    current_task = _task(
        "Original task",
        task_uuid="12345678-1234-1234-1234-123456789012",
        project="old_project",
    )
    updated_task = _task(
        "Updated task",
        task_uuid="12345678-1234-1234-1234-123456789012",
        project="test_project",
    )
    mock_taskwarrior.get_task.return_value = current_task
    mock_taskwarrior.modify_task.return_value = updated_task

    task_service = TaskService(mock_taskwarrior)
    task_input = TaskInputDTO(description="Updated task", project="test_project")

    result = task_service.update_task("12345678-1234-1234-1234-123456789012", task_input)

    assert isinstance(result, TaskOutputDTO)
    assert result.uuid == uuid.UUID("12345678-1234-1234-1234-123456789012")
    assert result.description == "Updated task"
    assert result.project == "test_project"

def test_delete_task():
    """Test deleting a task."""
    mock_taskwarrior = Mock()
    mock_taskwarrior.get_task.return_value = _task(
        "Test task",
        task_uuid="12345678-1234-1234-1234-123456789012",
    )
    mock_taskwarrior.delete_task.return_value = True

    task_service = TaskService(mock_taskwarrior)
    result = task_service.delete_task("12345678-1234-1234-1234-123456789012")

    assert result is True

def test_query_tasks_returns_canonical_shape():
    mock_taskwarrior = Mock()
    now = datetime.now(UTC)
    mock_taskwarrior.get_tasks.return_value = [
        _task(
            "Inbox task",
            task_uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            project="Inbox",
            due=now + timedelta(hours=2),
        ),
        _task(
            "Completed task",
            task_uuid="cccccccc-cccc-cccc-cccc-cccccccccccc",
            status="completed",
            project="Inbox",
        ),
    ]

    task_service = TaskService(mock_taskwarrior)
    result = task_service.query_tasks(filters={"project": "Inbox"}, limit=None)

    assert result["total"] == 1
    assert result["tasks"] == [
        {
            "uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "description": "Inbox task",
            "project": "Inbox",
            "priority": None,
            "tags": [],
            "due": (now + timedelta(hours=2)).isoformat(),
            "status": "pending",
            "depends": [],
        }
    ]

def test_query_tasks_supports_filters_and_sorting():
    mock_taskwarrior = Mock()
    now = datetime.now(UTC)
    mock_taskwarrior.get_tasks.return_value = [
        _task(
            "Write roadmap",
            task_uuid="11111111-1111-1111-1111-111111111111",
            project="work",
            priority="M",
            tags=["planning", "focus", "@office"],
            due=now + timedelta(days=2),
        ),
        _task(
            "Ship feature",
            task_uuid="22222222-2222-2222-2222-222222222222",
            project="work",
            priority="H",
            tags=["focus", "release", "@office"],
            due=now + timedelta(days=1),
        ),
        _task(
            "Plan holiday",
            task_uuid="33333333-3333-3333-3333-333333333333",
            project="personal",
            priority="L",
            tags=["travel"],
        ),
    ]

    task_service = TaskService(mock_taskwarrior)
    result = task_service.query_tasks(
        filters={
            "projects": ["work"],
            "tags_any": ["+@office"],
            "tags_all": ["+focus"],
            "text": "feature",
            "due_before": now + timedelta(days=3),
        },
        sort=["priority"],
        limit=None,
    )

    assert result["total"] == 1
    assert result["tasks"][0]["description"] == "Ship feature"

def test_get_stats_counts_overdue():
    mock_taskwarrior = Mock()
    now = datetime.now(UTC)
    mock_taskwarrior.get_tasks.return_value = [
        _task(
            "Overdue task",
            task_uuid="11111111-1111-1111-1111-111111111111",
            project="Inbox",
            due=now - timedelta(days=1),
        ),
        _task(
            "Actionable task",
            task_uuid="22222222-2222-2222-2222-222222222222",
            project="work",
            priority="H",
        ),
        _task(
            "Done",
            task_uuid="33333333-3333-3333-3333-333333333333",
            status="completed",
            project="Inbox",
            priority="M",
        ),
    ]

    task_service = TaskService(mock_taskwarrior)
    stats = task_service.get_stats(filters={"status": "all"})

    assert stats["total"] == 3
    assert stats["by_status"]["completed"] == 1
    assert stats["by_project"]["Inbox"] == 2
    assert stats["overdue"] == 1

def test_get_tasks_by_scope_groups_tasks_by_scope():
    mock_taskwarrior = Mock()
    now = datetime.now(UTC)
    mock_taskwarrior.get_tasks.return_value = [
        _task(
            "Roadmap A",
            task_uuid="11111111-1111-1111-1111-111111111111",
            project="alpha",
            due=now + timedelta(days=1),
        ),
        _task(
            "Roadmap B",
            task_uuid="22222222-2222-2222-2222-222222222222",
            project="beta",
        ),
    ]

    task_service = TaskService(mock_taskwarrior)
    roadmap = task_service.get_tasks_by_scope(scope="project")

    assert roadmap["scope"] == "project"
    assert roadmap["total"] == 2
    assert [group["key"] for group in roadmap["groups"]] == ["alpha", "beta"]

def test_next_task_returns_highest_urgency_unblocked_task():
    mock_taskwarrior = Mock()
    mock_taskwarrior.get_tasks.return_value = [
        _task(
            "Low urgency",
            task_uuid="11111111-1111-1111-1111-111111111111",
            project="work",
            urgency=10.0,
        ),
        _task(
            "High urgency",
            task_uuid="22222222-2222-2222-2222-222222222222",
            project="work",
            priority="H",
            urgency=80.0,
        ),
    ]

    task_service = TaskService(mock_taskwarrior)
    result = task_service.next_task()

    assert result["total"] == 2
    assert result["tasks"][0]["description"] == "High urgency"
    assert result["selection_reason"] == "highest_urgency"

def test_update_task_with_triage_metadata():
    """Test update_task for triage classification (project, priority, due, tags)."""
    mock_taskwarrior = Mock()
    current_task = _task(
        "Triage me",
        task_uuid="12345678-1234-1234-1234-123456789012",
        project=None,
        priority=None,
        tags=[],
    )
    updated_task = _task(
        "Triage me",
        task_uuid="12345678-1234-1234-1234-123456789012",
        project="work",
        priority="H",
        tags=["focus"],
    )
    mock_taskwarrior.get_task.return_value = current_task
    mock_taskwarrior.modify_task.return_value = updated_task

    task_service = TaskService(mock_taskwarrior)
    task_input = TaskInputDTO(project="work", priority="H", tags=["focus"])
    result = task_service.update_task(
        "12345678-1234-1234-1234-123456789012",
        task_input,
    )

    # Verify only explicit fields were set
    modify_input = mock_taskwarrior.modify_task.call_args.args[0]
    assert modify_input.model_dump(exclude_unset=True) == {
        "project": "work",
        "priority": "H",
        "tags": ["focus"],
    }
    # Verify return format is single task object
    assert isinstance(result, TaskOutputDTO)
    assert result.project == "work"
    assert result.priority == "H"

def test_update_task_raises_on_no_changes():
    """Test that update_task raises ValueError when no fields would change."""
    mock_taskwarrior = Mock()
    current_task = _task(
        "No changes",
        task_uuid="12345678-1234-1234-1234-123456789012",
        project="work",
        priority="H",
        tags=["focus"],
    )
    mock_taskwarrior.get_task.return_value = current_task

    task_service = TaskService(mock_taskwarrior)
    # Attempt to update with same values as current state
    task_input = TaskInputDTO(project="work", priority="H", tags=["focus"])

    with pytest.raises(ValueError, match="No changes detected"):
        task_service.update_task(
            "12345678-1234-1234-1234-123456789012",
            task_input,
        )

def test_update_task_raises_on_empty_changes():
    """Test that update_task raises ValueError when no fields are specified."""
    task_service = TaskService(Mock())

    with pytest.raises(ValueError, match="No changes detected"):
        task_service.update_task("123", TaskInputDTO())

def test_metadata_exposes_v2_contract():
    mock_taskwarrior = Mock()
    mock_taskwarrior.get_tasks.return_value = [
        _task(
            "Review task",
            task_uuid="11111111-1111-1111-1111-111111111111",
            project="Inbox",
            tags=["phone", "@calls"],
        ),
        _task(
            "Actionable task",
            task_uuid="22222222-2222-2222-2222-222222222222",
            project="work",
            priority="H",
            tags=["waiting"],
        ),
    ]
    mock_taskwarrior.context_service.get_contexts.return_value = [
        SimpleNamespace(name="calls", read_filter="+@calls", write_filter="+@calls", active=True),
        SimpleNamespace(name="office", read_filter="+@office", write_filter="+@office", active=False),
    ]
    mock_taskwarrior.context_service.get_current_context.return_value = "calls"

    task_service = TaskService(mock_taskwarrior)
    metadata = task_service.get_metadata()

    # Core expected metadata fields (v2 contract)
    expected_base = {
        "projects": ["Inbox", "work"],
        "tags": ["+@calls", "+phone", "+waiting"],
        "context_tags": ["+@calls"],
        "available_contexts": ["calls", "office"],
        "active_context": "calls",
        "priorities": ["H", "M", "L"],
        "views": ["review", "today", "week", "overdue"],
        "supported_filters": [
            "project",
            "priority",
            "status",
            "tags_any",
            "tags_all",
            "due_before",
            "due_after",
            "has_depends",
            "is_blocked",
            "text",
        ],
        "supported_sorts": ["due", "-due", "priority", "-priority", "project", "urgency"],
        "tag_conventions": {
            "contexts": {"prefix": "+@"},
            "lists": {"prefix": "+"},
        },
        "api_version": "2.1",
    }

    for key, value in expected_base.items():
        assert metadata[key] == value

    # The resource_uris must at least include the original v2 contract entries
    expected_resource_uris = {
        "review": "taskmajor://queue/unsorted",
        "today": "taskmajor://agenda/today",
        "week": "taskmajor://agenda/week",
        "overdue": "taskmajor://status/overdue",
        "stats": "taskmajor://analytics/summary",
        "metadata": "taskmajor://config/schema",
    }

    assert "resource_uris" in metadata and isinstance(metadata["resource_uris"], dict)
    for k, v in expected_resource_uris.items():
        assert k in metadata["resource_uris"] and metadata["resource_uris"][k] == v

    # Ensure discovery includes newly-added canonical URIs so agents can find them
    for new_key in ("inbox", "context", "errors", "undo"):
        assert new_key in metadata["resource_uris"]


# ---------------------------------------------------------------------------
# stop_task edge cases
# ---------------------------------------------------------------------------

def test_stop_task_not_found_returns_false():
    """When task is not in storage AND not in TaskWarrior, stop_task returns False."""
    tw = Mock()
    tw.get_task.return_value = None

    service = TaskService(tw)
    service.storage.get_task = Mock(return_value=None)

    result = service.stop_task("12345678-1234-1234-1234-123456789012")

    assert result is False
    tw.stop_task.assert_not_called()


def test_stop_task_success_calls_tw_stop():
    """When task is found in storage, stop_task calls taskwarrior_client.stop_task and returns True."""
    tw = Mock()
    task = _task("Active task", task_uuid="12345678-1234-1234-1234-123456789012")

    service = TaskService(tw)
    service.storage.get_task = Mock(return_value=task)

    result = service.stop_task("12345678-1234-1234-1234-123456789012")

    assert result is True
    tw.stop_task.assert_called_once_with("12345678-1234-1234-1234-123456789012")


# ---------------------------------------------------------------------------
# start_task edge cases
# ---------------------------------------------------------------------------

def test_start_task_not_found_returns_false():
    """When task is absent from storage and TaskWarrior, start_task returns False."""
    tw = Mock()
    tw.get_task.return_value = None

    service = TaskService(tw)
    service.storage.get_task = Mock(return_value=None)

    result = service.start_task("99999999-9999-9999-9999-999999999999")

    assert result is False
    tw.start_task.assert_not_called()


# ---------------------------------------------------------------------------
# complete_task edge cases
# ---------------------------------------------------------------------------

def test_complete_task_verifies_completion_via_status():
    """done_task returns object with status=completed → storage marked, returns True."""
    tw = Mock()
    tw.done_task.return_value = _task(
        "Finished",
        task_uuid="12345678-1234-1234-1234-123456789012",
        status="completed",
    )

    service = TaskService(tw)
    service.storage.mark_task_completed = Mock()

    result = service.complete_task("12345678-1234-1234-1234-123456789012")

    assert result is True
    service.storage.mark_task_completed.assert_called_once()


# ---------------------------------------------------------------------------
# list_contexts edge cases
# ---------------------------------------------------------------------------

def test_list_contexts_returns_empty_on_error():
    """When context_service.get_contexts() raises, list_contexts returns []."""
    tw = Mock()
    tw.context_service.get_contexts.side_effect = RuntimeError("context fetch failed")

    service = TaskService(tw)
    result = service.list_contexts()

    assert result == []


# ---------------------------------------------------------------------------
# Priority enum ordering
# ---------------------------------------------------------------------------

def test_priority_enum_ordering():
    assert Priority.H < Priority.M
    assert Priority.M < Priority.L
    assert Priority.L < Priority.NONE
