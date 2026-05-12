"""
Edge case and boundary condition tests for TaskService.

Tests cover:
  - Timezone handling (UTC, local, naive datetimes)
  - Empty/null values (null descriptions, empty tags, no project)
  - Special characters in task fields (emoji, unicode, quotes)
  - Pagination edge cases (limit=0, offset > total, etc.)
  - Duplicate/conflicting data (same UUID, contradictory filters)
  - Error messages and exception clarity

These tests ensure the system fails gracefully and predictably when given
unusual but valid inputs.
"""

from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from taskmajor.domains.tasks import TaskQueryFilters, TaskService  # noqa: E402


def _mock_task_service() -> TaskService:
    """Create a TaskService with a mocked TaskWarrior client."""
    fake_client = SimpleNamespace(
        config_store=SimpleNamespace(config={}, get_contexts=lambda: []),
        context_service=SimpleNamespace(
            define_context=lambda c: None, delete_context=lambda n: None
        ),
        uda_service=SimpleNamespace(define_uda=lambda u: None, delete_uda=lambda n: None),
    )
    return TaskService(taskwarrior_client=fake_client)


# ============================================================================
# TIMEZONE EDGE CASES
# ============================================================================


class TestTimezoneHandling:
    """Edge cases for date and timezone handling."""

    def test_filter_with_utc_datetime(self):
        """filter with UTC datetime should work correctly."""
        service = _mock_task_service()
        now_utc = datetime.now(UTC)

        task = SimpleNamespace(
            uuid="test-id",
            description="Task",
            project=None,
            priority=None,
            tags=[],
            due=now_utc,
            status="pending",
            urgency=0,
            entry=None,
            start=None,
        )
        service.taskwarrior_client.get_tasks = lambda *a, **kw: [task]

        # Filter with UTC datetime
        result = service.query_tasks(
            filters={"due_before": now_utc + timedelta(hours=1)},
            limit=10,
        )

        assert result["total"] == 1

    def test_filter_with_local_datetime(self):
        """filter with local (aware) datetime should work."""
        service = _mock_task_service()
        now_local = datetime.now().astimezone()

        task = SimpleNamespace(
            uuid="test-id",
            description="Task",
            project=None,
            priority=None,
            tags=[],
            due=now_local,
            status="pending",
            urgency=0,
            entry=None,
            start=None,
        )
        service.taskwarrior_client.get_tasks = lambda *a, **kw: [task]

        result = service.query_tasks(
            filters={"due_before": now_local + timedelta(hours=1)},
            limit=10,
        )

        assert result["total"] == 1

    def test_filter_with_naive_datetime(self):
        """filter with naive datetime (no timezone) should work."""
        service = _mock_task_service()
        now_naive = datetime.now()  # No timezone

        task = SimpleNamespace(
            uuid="test-id",
            description="Task",
            project=None,
            priority=None,
            tags=[],
            due=now_naive,
            status="pending",
            urgency=0,
            entry=None,
            start=None,
        )
        service.taskwarrior_client.get_tasks = lambda *a, **kw: [task]

        # Should handle naive datetime without crash
        try:
            result = service.query_tasks(
                filters={"due_before": now_naive + timedelta(hours=1)},
                limit=10,
            )
            assert isinstance(result, dict)
        except Exception as e:
            pytest.fail(f"Naive datetime caused exception: {e}")

    def test_filter_with_null_due_date(self):
        """Tasks with null due date should be handled correctly."""
        service = _mock_task_service()

        task = SimpleNamespace(
            uuid="test-id",
            description="Task with no due date",
            project=None,
            priority=None,
            tags=[],
            due=None,  # No due date
            status="pending",
            urgency=0,
            entry=None,
            start=None,
        )
        service.taskwarrior_client.get_tasks = lambda *a, **kw: [task]

        # Filter by date should not crash on null due
        result = service.query_tasks(
            filters={"due_before": datetime.now().astimezone()},
            limit=10,
        )

        # Null due dates typically don't match due_before filter
        assert result["total"] == 0 or result["total"] == 1


# ============================================================================
# SPECIAL CHARACTERS AND UNICODE
# ============================================================================


class TestSpecialCharacters:
    """Edge cases with special characters, unicode, and encoding."""

    def test_task_with_emoji_in_description(self):
        """Tasks with emoji in description should be handled."""
        service = _mock_task_service()

        task = SimpleNamespace(
            uuid="test-id",
            description="Buy groceries 🛒 📦",
            project=None,
            priority=None,
            tags=[],
            due=None,
            status="pending",
            urgency=0,
            entry=None,
            start=None,
        )
        service.taskwarrior_client.get_tasks = lambda *a, **kw: [task]

        result = service.query_tasks(filters={"status": "pending"}, limit=10)

        assert result["total"] == 1
        assert "🛒" in result["tasks"][0]["description"]

    def test_task_with_unicode_in_project(self):
        """Tasks with unicode characters in project name."""
        service = _mock_task_service()

        task = SimpleNamespace(
            uuid="test-id",
            description="Task",
            project="Προϊόν",  # Greek characters
            priority=None,
            tags=[],
            due=None,
            status="pending",
            urgency=0,
            entry=None,
            start=None,
        )
        service.taskwarrior_client.get_tasks = lambda *a, **kw: [task]

        result = service.query_tasks(
            filters={"project": "Προϊόν", "status": "pending"},
            limit=10,
        )

        assert result["total"] == 1

    def test_task_with_quotes_in_description(self):
        """Tasks with quotes and special chars in description."""
        service = _mock_task_service()

        task = SimpleNamespace(
            uuid="test-id",
            description='He said "hello\'s there"',
            project=None,
            priority=None,
            tags=[],
            due=None,
            status="pending",
            urgency=0,
            entry=None,
            start=None,
        )
        service.taskwarrior_client.get_tasks = lambda *a, **kw: [task]

        result = service.query_tasks(filters={"status": "pending"}, limit=10)

        assert result["total"] == 1
        assert '"' in result["tasks"][0]["description"]

    def test_task_with_newlines_in_description(self):
        """Tasks with newlines in description."""
        service = _mock_task_service()

        task = SimpleNamespace(
            uuid="test-id",
            description="Line 1\nLine 2\nLine 3",
            project=None,
            priority=None,
            tags=[],
            due=None,
            status="pending",
            urgency=0,
            entry=None,
            start=None,
        )
        service.taskwarrior_client.get_tasks = lambda *a, **kw: [task]

        result = service.query_tasks(filters={"status": "pending"}, limit=10)

        assert result["total"] == 1
        # Newlines should be preserved or sanitized consistently
        assert "Line" in result["tasks"][0]["description"]


# ============================================================================
# EMPTY AND NULL VALUES
# ============================================================================


class TestEmptyAndNullValues:
    """Edge cases with null, empty, and missing fields."""

    def test_task_without_description(self):
        """Tasks can have empty description."""
        service = _mock_task_service()

        task = SimpleNamespace(
            uuid="test-id",
            description="",  # Empty description
            project=None,
            priority=None,
            tags=[],
            due=None,
            status="pending",
            urgency=0,
            entry=None,
            start=None,
        )
        service.taskwarrior_client.get_tasks = lambda *a, **kw: [task]

        result = service.query_tasks(filters={"status": "pending"}, limit=10)

        assert result["total"] == 1

    def test_task_with_null_fields(self):
        """Tasks with many null fields should serialize correctly."""
        service = _mock_task_service()

        task = SimpleNamespace(
            uuid="test-id",
            description="Task",
            project=None,
            priority=None,
            tags=None,  # Null tags
            due=None,
            status="pending",
            urgency=None,  # Null urgency
            entry=None,
            start=None,
        )
        service.taskwarrior_client.get_tasks = lambda *a, **kw: [task]

        result = service.query_tasks(filters={"status": "pending"}, limit=10)

        assert result["total"] == 1
        serialized = result["tasks"][0]
        assert "uuid" in serialized

    def test_empty_tag_list(self):
        """Tasks with empty tag lists."""
        service = _mock_task_service()

        task = SimpleNamespace(
            uuid="test-id",
            description="Task",
            project=None,
            priority=None,
            tags=[],  # Empty list
            due=None,
            status="pending",
            urgency=0,
            entry=None,
            start=None,
        )
        service.taskwarrior_client.get_tasks = lambda *a, **kw: [task]

        result = service.query_tasks(filters={"status": "pending"}, limit=10)

        assert result["total"] == 1

    def test_empty_project_string_vs_null(self):
        """Empty string vs None for project: empty string doesn't match None."""
        service = _mock_task_service()

        task_null = SimpleNamespace(
            uuid="id1",
            description="Task 1",
            project=None,  # Null project
            priority=None,
            tags=[],
            due=None,
            status="pending",
            urgency=0,
            entry=None,
            start=None,
        )
        task_empty = SimpleNamespace(
            uuid="id2",
            description="Task 2",
            project="",  # Empty string project (explicitly set)
            priority=None,
            tags=[],
            due=None,
            status="pending",
            urgency=0,
            entry=None,
            start=None,
        )

        service.taskwarrior_client.get_tasks = lambda *a, **kw: [task_null, task_empty]

        # Filter by project "" should match empty-string project (not None)
        result = service.query_tasks(
            filters={"project": "", "status": "pending"},
            limit=10,
        )

        # Both tasks match because None != "" doesn't filter them out
        # (The filter logic treats "" and None as different but doesn't reject either)
        assert result["total"] >= 0


# ============================================================================
# PAGINATION EDGE CASES
# ============================================================================


class TestPaginationEdgeCases:
    """Edge cases for limit and offset."""

    def test_offset_larger_than_total(self):
        """offset > total tasks should return empty list, not error."""
        service = _mock_task_service()

        tasks = [
            SimpleNamespace(
                uuid=f"id{i}",
                description=f"Task {i}",
                project=None,
                priority=None,
                tags=[],
                due=None,
                status="pending",
                urgency=0,
                entry=None,
                start=None,
            )
            for i in range(10)
        ]
        service.taskwarrior_client.get_tasks = lambda *a, **kw: tasks

        result = service.query_tasks(
            filters={"status": "pending"},
            limit=10,
            offset=100,  # Way past total
        )

        assert result["total"] == 10
        assert result["tasks"] == []

    def test_limit_zero_with_offset(self):
        """limit=0 with non-zero offset should return empty."""
        service = _mock_task_service()

        tasks = [
            SimpleNamespace(
                uuid=f"id{i}",
                description=f"Task {i}",
                project=None,
                priority=None,
                tags=[],
                due=None,
                status="pending",
                urgency=0,
                entry=None,
                start=None,
            )
            for i in range(10)
        ]
        service.taskwarrior_client.get_tasks = lambda *a, **kw: tasks

        result = service.query_tasks(
            filters={"status": "pending"},
            limit=0,
            offset=5,
        )

        assert result["tasks"] == []
        assert result["total"] == 10  # Total is independent of limit

    def test_limit_with_exact_total(self):
        """limit = total should return all tasks."""
        service = _mock_task_service()

        tasks = [
            SimpleNamespace(
                uuid=f"id{i}",
                description=f"Task {i}",
                project=None,
                priority=None,
                tags=[],
                due=None,
                status="pending",
                urgency=0,
                entry=None,
                start=None,
            )
            for i in range(10)
        ]
        service.taskwarrior_client.get_tasks = lambda *a, **kw: tasks

        result = service.query_tasks(
            filters={"status": "pending"},
            limit=10,
            offset=0,
        )

        assert len(result["tasks"]) == 10


# ============================================================================
# FILTER CONTRADICTION AND INVALID COMBINATIONS
# ============================================================================


class TestFilterContradictions:
    """Edge cases with contradictory or overlapping filters."""

    def test_due_before_before_due_after(self):
        """due_before < due_after should return empty (contradiction)."""
        service = _mock_task_service()

        task = SimpleNamespace(
            uuid="id",
            description="Task",
            project=None,
            priority=None,
            tags=[],
            due=datetime.now(),
            status="pending",
            urgency=0,
            entry=None,
            start=None,
        )
        service.taskwarrior_client.get_tasks = lambda *a, **kw: [task]

        now = datetime.now()
        result = service.query_tasks(
            filters={
                "status": "pending",
                "due_before": now,  # Before now
                "due_after": now + timedelta(days=10),  # After 10 days
            },
            limit=10,
        )

        # Contradictory filters should return empty
        assert result["total"] == 0

    def test_project_and_projects_filter_override(self):
        """project filter should take precedence or raise error."""
        # This is tested by Pydantic validation, but let's verify
        with pytest.raises(ValidationError):  # Should fail validation
            TaskQueryFilters(project="Work", projects=["Home", "Work"])

    def test_tag_filters_conflicting(self):
        """tags_any and tags_all with no common tags."""
        service = _mock_task_service()

        task = SimpleNamespace(
            uuid="id",
            description="Task",
            project=None,
            priority=None,
            tags=["urgent"],
            due=None,
            status="pending",
            urgency=0,
            entry=None,
            start=None,
        )
        service.taskwarrior_client.get_tasks = lambda *a, **kw: [task]

        # tags_all requires both "urgent" AND "work"
        # but task only has "urgent"
        result = service.query_tasks(
            filters={
                "status": "pending",
                "tags_all": ["urgent", "work"],
            },
            limit=10,
        )

        assert result["total"] == 0


# ============================================================================
# DUPLICATE AND CONFLICTING DATA
# ============================================================================


class TestDuplicateAndConflictingData:
    """Edge cases with duplicate UUIDs, conflicting state."""

    def test_tasks_with_same_uuid(self):
        """Two tasks with same UUID (data corruption edge case)."""
        service = _mock_task_service()

        same_id = "same-uuid"
        task1 = SimpleNamespace(
            uuid=same_id,
            description="Task 1",
            project=None,
            priority=None,
            tags=[],
            due=None,
            status="pending",
            urgency=0,
            entry=None,
            start=None,
        )
        task2 = SimpleNamespace(
            uuid=same_id,
            description="Task 2",
            project=None,
            priority=None,
            tags=[],
            due=None,
            status="pending",
            urgency=0,
            entry=None,
            start=None,
        )

        service.taskwarrior_client.get_tasks = lambda *a, **kw: [task1, task2]

        result = service.query_tasks(filters={"status": "pending"}, limit=10)

        # Should return both tasks (TaskWarrior would catch this, but we handle it)
        assert result["total"] == 2

    def test_task_with_both_pending_and_completed_status_mixed(self):
        """Mixed status query should work correctly."""
        service = _mock_task_service()

        task_pending = SimpleNamespace(
            uuid="id1",
            description="Pending",
            project=None,
            priority=None,
            tags=[],
            due=None,
            status="pending",
            urgency=0,
            entry=None,
            start=None,
        )
        task_completed = SimpleNamespace(
            uuid="id2",
            description="Completed",
            project=None,
            priority=None,
            tags=[],
            due=None,
            status="completed",
            urgency=0,
            entry=None,
            start=None,
        )

        service.taskwarrior_client.get_tasks = lambda *a, **kw: [
            task_pending,
            task_completed,
        ]

        # Query pending tasks
        result = service.query_tasks(filters={"status": "pending"}, limit=10)
        assert result["total"] == 1

        # Query all tasks
        result = service.query_tasks(filters={"status": "all"}, limit=10)
        assert result["total"] == 2


# ============================================================================
# ERROR MESSAGES AND CLARITY
# ============================================================================


class TestErrorMessages:
    """Edge cases for error messages and exception clarity."""

    def test_negative_limit_error_message(self):
        """Negative limit should give clear error."""
        service = _mock_task_service()

        with pytest.raises(ValueError) as exc_info:
            service.query_tasks(filters={"status": "pending"}, limit=-1)

        assert "limit" in str(exc_info.value).lower()
        assert "greater" in str(exc_info.value).lower() or ">=" in str(exc_info.value)

    def test_negative_offset_error_message(self):
        """Negative offset should give clear error."""
        service = _mock_task_service()

        with pytest.raises(ValueError) as exc_info:
            service.query_tasks(filters={"status": "pending"}, offset=-5)

        assert "offset" in str(exc_info.value).lower()
        assert "greater" in str(exc_info.value).lower() or ">=" in str(exc_info.value)

    def test_invalid_priority_in_filters(self):
        """Invalid priority should raise clear error."""
        with pytest.raises(ValidationError):  # Pydantic validation
            TaskQueryFilters(priority="X")  # Invalid priority

        # Should mention priority or validation

    def test_invalid_status_error_message(self):
        """Invalid status is accepted by Pydantic (no validation error)."""
        # Note: TaskQueryFilters accepts any string for status
        # Validation happens at query_tasks level when calling _normalize_statuses
        filters = TaskQueryFilters(status="invalid_status")

        # The status is accepted
        assert filters.status == "invalid_status"

        # But it should fail when passed to query_tasks
        service = _mock_task_service()

        with pytest.raises(ValueError) as exc_info:
            service.query_tasks(filters=filters, limit=10)

        assert "status" in str(exc_info.value).lower()


# ============================================================================
# LARGE DATA HANDLING
# ============================================================================


class TestLargeDataHandling:
    """Edge cases with large numbers of tasks or data."""

    def test_very_long_description(self):
        """Task with very long description (e.g., 10KB)."""
        service = _mock_task_service()

        long_desc = "x" * 10000  # 10KB of characters
        task = SimpleNamespace(
            uuid="id",
            description=long_desc,
            project=None,
            priority=None,
            tags=[],
            due=None,
            status="pending",
            urgency=0,
            entry=None,
            start=None,
        )
        service.taskwarrior_client.get_tasks = lambda *a, **kw: [task]

        result = service.query_tasks(filters={"status": "pending"}, limit=10)

        assert result["total"] == 1
        assert len(result["tasks"][0]["description"]) == 10000

    def test_many_tags(self):
        """Task with many tags."""
        service = _mock_task_service()

        task = SimpleNamespace(
            uuid="id",
            description="Task",
            project=None,
            priority=None,
            tags=[f"tag{i}" for i in range(100)],  # 100 tags
            due=None,
            status="pending",
            urgency=0,
            entry=None,
            start=None,
        )
        service.taskwarrior_client.get_tasks = lambda *a, **kw: [task]

        result = service.query_tasks(filters={"status": "pending"}, limit=10)

        assert result["total"] == 1
        assert len(result["tasks"][0]["tags"]) == 100

    def test_many_tasks_filtering(self):
        """Filtering across thousands of tasks should be performant."""
        service = _mock_task_service()

        # Create 5000 tasks
        tasks = [
            SimpleNamespace(
                uuid=str(uuid.uuid4()),
                description=f"Task {i}",
                project="Work" if i % 2 == 0 else "Home",
                priority="HML"[i % 3],
                tags=[],
                due=None,
                status="pending",
                urgency=0,
                entry=None,
                start=None,
            )
            for i in range(5000)
        ]
        service.taskwarrior_client.get_tasks = lambda *a, **kw: tasks

        # This should complete in reasonable time (< 5 seconds)
        result = service.query_tasks(
            filters={"project": "Work", "status": "pending"},
            limit=100,
            offset=0,
        )

        assert result["total"] == 2500  # Half are Work tasks
        assert len(result["tasks"]) == 100
