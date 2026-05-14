"""Coverage tests for TaskService — error paths, context ops, window filters, etc."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import Mock, patch

import pytest
from taskwarrior import TaskInputDTO, TaskOutputDTO

from taskmajor.domains.tasks import TaskService


def _task(
    description: str,
    *,
    task_uuid: str = "12345678-1234-1234-1234-123456789012",
    task_id: int = 1,
    status: str = "pending",
    project: str | None = None,
    priority: str | None = None,
    tags: list[str] | None = None,
    due: datetime | None = None,
    urgency: float | None = None,
    depends: list | None = None,
) -> Any:
    payload: dict[str, Any] = {
        "id": task_id,
        "uuid": uuid.UUID(task_uuid),
        "description": description,
        "status": status,
        "project": project,
        "priority": priority,
        "tags": tags or [],
        "udas": {},
    }
    if due is not None:
        payload["due"] = due
    if urgency is not None:
        payload["urgency"] = urgency
    if depends is not None:
        payload["depends"] = depends
    return TaskOutputDTO(**cast(Any, payload))


# ---------------------------------------------------------------------------
# refresh_task_from_taskwarrior
# ---------------------------------------------------------------------------


class TestRefreshTask:
    def test_found_task_refreshes_storage_and_returns(self):
        tw = Mock()
        task = _task("My task")
        tw.get_task.return_value = task

        svc = TaskService(tw)
        result = svc.refresh_task_from_taskwarrior("12345678-1234-1234-1234-123456789012")

        assert result is task
        tw.get_task.assert_called_once()

    def test_not_found_returns_none(self):
        tw = Mock()
        tw.get_task.return_value = None

        svc = TaskService(tw)
        result = svc.refresh_task_from_taskwarrior("99999999-9999-9999-9999-999999999999")

        assert result is None

    def test_exception_returns_none(self):
        tw = Mock()
        tw.get_task.side_effect = RuntimeError("TW crashed")

        svc = TaskService(tw)
        result = svc.refresh_task_from_taskwarrior("12345678-1234-1234-1234-123456789012")

        assert result is None


# ---------------------------------------------------------------------------
# _mark_storage_completed / complete_task error paths
# ---------------------------------------------------------------------------


class TestCompleteTask:
    def test_complete_task_done_task_raises_calls_verify(self):
        """When done_task raises, falls back to _verify_task_completed."""
        tw = Mock()
        tw.done_task.side_effect = RuntimeError("TW error")
        completed = _task("Task", status="completed")
        tw.get_task.return_value = completed

        svc = TaskService(tw)
        result = svc.complete_task("12345678-1234-1234-1234-123456789012")

        assert result is True

    def test_complete_task_done_task_raises_and_verify_returns_false(self):
        """done_task raises and TaskWarrior says not completed → False."""
        tw = Mock()
        tw.done_task.side_effect = RuntimeError("TW error")
        tw.get_task.return_value = _task("Task", status="pending")

        svc = TaskService(tw)
        result = svc.complete_task("12345678-1234-1234-1234-123456789012")

        assert result is False

    def test_complete_task_done_task_raises_and_get_task_raises(self):
        """Both done_task and get_task raise → returns False."""
        tw = Mock()
        tw.done_task.side_effect = RuntimeError("TW error")
        tw.get_task.side_effect = RuntimeError("also broken")

        svc = TaskService(tw)
        result = svc.complete_task("12345678-1234-1234-1234-123456789012")

        assert result is False

    def test_complete_task_returns_none_falls_back_to_verify(self):
        """done_task returns None → falls back to verify via get_task."""
        tw = Mock()
        tw.done_task.return_value = None
        tw.get_task.return_value = _task("Task", status="completed")

        svc = TaskService(tw)
        result = svc.complete_task("12345678-1234-1234-1234-123456789012")

        assert result is True

    def test_mark_storage_completed_keyerror_does_not_raise(self):
        """_mark_storage_completed with missing key is best-effort."""
        tw = Mock()
        svc = TaskService(tw)
        svc.storage.mark_task_completed = Mock(side_effect=KeyError("nope"))
        # Should not raise
        svc._mark_storage_completed("missing-id")


# ---------------------------------------------------------------------------
# set_context / unset_context
# ---------------------------------------------------------------------------


class TestContextOps:
    def test_set_context_success(self):
        tw = Mock()
        tw.apply_context.return_value = None

        svc = TaskService(tw)
        result = svc.set_context("work")

        assert result is True
        tw.apply_context.assert_called_once_with("work")

    def test_set_context_exception_returns_false(self):
        tw = Mock()
        tw.apply_context.side_effect = RuntimeError("no such context")

        svc = TaskService(tw)
        result = svc.set_context("nonexistent")

        assert result is False

    def test_unset_context_success(self):
        tw = Mock()
        tw.unset_context.return_value = None

        svc = TaskService(tw)
        result = svc.unset_context()

        assert result is True
        tw.unset_context.assert_called_once()

    def test_unset_context_exception_returns_false(self):
        tw = Mock()
        tw.unset_context.side_effect = RuntimeError("cannot unset")

        svc = TaskService(tw)
        result = svc.unset_context()

        assert result is False


# ---------------------------------------------------------------------------
# _is_blocked
# ---------------------------------------------------------------------------


class TestIsBlocked:
    def test_no_dependencies_returns_false(self):
        tw = Mock()
        svc = TaskService(tw)
        task = _task("standalone", depends=[])
        assert svc._is_blocked(task) is False

    def test_dep_completed_returns_false(self):
        tw = Mock()
        dep_uuid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        dep = _task("dep", task_uuid=dep_uuid, status="completed")
        tw.get_task.return_value = dep

        svc = TaskService(tw)
        task = _task("blocked", depends=[dep_uuid])
        assert svc._is_blocked(task) is False

    def test_dep_pending_returns_true(self):
        tw = Mock()
        dep_uuid = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        dep = _task("dep", task_uuid=dep_uuid, status="pending")
        tw.get_task.return_value = dep

        svc = TaskService(tw)
        task = _task("blocked", depends=[dep_uuid])
        assert svc._is_blocked(task) is True

    def test_dep_fetch_raises_logs_and_returns_false(self):
        """If fetching a dependency raises, the task is not considered blocked."""
        tw = Mock()
        tw.get_task.side_effect = RuntimeError("network error")

        svc = TaskService(tw)
        dep_uuid = "cccccccc-cccc-cccc-cccc-cccccccccccc"
        task = _task("blocked", depends=[dep_uuid])

        # Should not raise, should return False (skip block check)
        result = svc._is_blocked(task)
        assert result is False

    def test_dep_found_in_storage_cache(self):
        """Dependency already in storage cache (completed) — no TW call needed."""
        tw = Mock()
        dep_uuid = "dddddddd-dddd-dddd-dddd-dddddddddddd"
        dep = _task("dep", task_uuid=dep_uuid, status="completed")

        svc = TaskService(tw)
        svc.storage.store_task(dep_uuid, dep)

        task = _task("blocked", depends=[dep_uuid])
        assert svc._is_blocked(task) is False
        tw.get_task.assert_not_called()


# ---------------------------------------------------------------------------
# start_task / stop_task — task not in storage, fetched from TW
# ---------------------------------------------------------------------------


class TestStartStopTaskFetch:
    def test_start_task_fetches_from_tw_when_not_in_storage(self):
        tw = Mock()
        fetched = _task("fetched")
        tw.get_task.return_value = fetched

        svc = TaskService(tw)
        svc.storage.get_task = Mock(return_value=None)

        result = svc.start_task("12345678-1234-1234-1234-123456789012")

        assert result is True
        tw.start_task.assert_called_once()

    def test_stop_task_fetches_from_tw_when_not_in_storage(self):
        tw = Mock()
        fetched = _task("fetched")
        tw.get_task.return_value = fetched

        svc = TaskService(tw)
        svc.storage.get_task = Mock(return_value=None)

        result = svc.stop_task("12345678-1234-1234-1234-123456789012")

        assert result is True
        tw.stop_task.assert_called_once()

    def test_start_task_exception_returns_false(self):
        tw = Mock()
        tw.get_task.return_value = _task("task")
        tw.start_task.side_effect = RuntimeError("TW crash")

        svc = TaskService(tw)
        svc.storage.get_task = Mock(return_value=None)

        result = svc.start_task("12345678-1234-1234-1234-123456789012")
        assert result is False

    def test_stop_task_exception_returns_false(self):
        tw = Mock()
        tw.get_task.return_value = _task("task")
        tw.stop_task.side_effect = RuntimeError("TW crash")

        svc = TaskService(tw)
        svc.storage.get_task = Mock(return_value=None)

        result = svc.stop_task("12345678-1234-1234-1234-123456789012")
        assert result is False


# ---------------------------------------------------------------------------
# get_udas — fallback when not implemented
# ---------------------------------------------------------------------------


class TestGetUdas:
    def test_get_udas_happy_path(self):
        tw = Mock()
        tw.get_udas.return_value = [{"name": "severity"}]

        svc = TaskService(tw)
        result = svc.get_udas()

        assert result["total"] == 1
        assert result["udas"] == [{"name": "severity"}]

    def test_get_udas_attribute_error_returns_fallback(self):
        tw = Mock()

        svc = TaskService(tw)
        tw.get_udas.side_effect = AttributeError("not implemented")
        result = svc.get_udas()

        assert result["udas"] == []
        assert result["total"] == 0
        assert "note" in result

    def test_get_udas_not_implemented_error_returns_fallback(self):
        tw = Mock()
        tw.get_udas.side_effect = NotImplementedError("not yet")

        svc = TaskService(tw)
        result = svc.get_udas()

        assert result["udas"] == []
        assert result["total"] == 0


# ---------------------------------------------------------------------------
# today_window_filters / week_window_filters
# ---------------------------------------------------------------------------


class TestWindowFilters:
    def test_today_window_filters_returns_due_after_and_due_before(self):
        tw = Mock()
        svc = TaskService(tw)
        result = svc.today_window_filters()

        assert "due_after" in result
        assert "due_before" in result
        after = result["due_after"]
        before = result["due_before"]
        # before - after should be roughly 1 day
        assert timedelta(hours=23) < (before - after) <= timedelta(days=1, seconds=1)

    def test_week_window_filters_returns_7_day_span(self):
        tw = Mock()
        svc = TaskService(tw)
        result = svc.week_window_filters()

        assert "due_after" in result
        assert "due_before" in result
        span = result["due_before"] - result["due_after"]
        assert timedelta(days=6) < span <= timedelta(days=7, seconds=1)


# ---------------------------------------------------------------------------
# _roadmap_key
# ---------------------------------------------------------------------------


class TestRoadmapKey:
    def test_scope_project(self):
        tw = Mock()
        svc = TaskService(tw)
        task = _task("t", project="Work")
        assert svc._roadmap_key(task, "project") == "Work"

    def test_scope_project_none(self):
        tw = Mock()
        svc = TaskService(tw)
        task = _task("t")
        assert svc._roadmap_key(task, "project") == "(none)"

    def test_scope_priority(self):
        tw = Mock()
        svc = TaskService(tw)
        task = _task("t", priority="H")
        assert svc._roadmap_key(task, "priority") == "H"

    def test_scope_day(self):
        tw = Mock()
        svc = TaskService(tw)
        due = datetime(2026, 5, 15, 10, 0, tzinfo=UTC)
        task = _task("t", due=due)
        assert svc._roadmap_key(task, "day") == "2026-05-15"

    def test_scope_week(self):
        tw = Mock()
        svc = TaskService(tw)
        due = datetime(2026, 5, 11, tzinfo=UTC)  # Monday of week 20
        task = _task("t", due=due)
        key = svc._roadmap_key(task, "week")
        assert key.startswith("2026-W")

    def test_scope_unscheduled(self):
        tw = Mock()
        svc = TaskService(tw)
        task = _task("t")  # no due date
        assert svc._roadmap_key(task, "day") == "(unscheduled)"

    def test_unsupported_scope_raises(self):
        tw = Mock()
        svc = TaskService(tw)
        due = datetime(2026, 5, 15, tzinfo=UTC)
        task = _task("t", due=due)
        with pytest.raises(ValueError, match="Unsupported roadmap scope"):
            svc._roadmap_key(task, "month")
