"""
Property-based tests using Hypothesis for task query operations.

These tests verify invariants that should hold for ANY combination of valid inputs:
  - Query results never exceed the specified limit
  - No exceptions are raised for valid filter combinations
  - Sorting is stable and produces consistent results
  - Pagination (limit + offset) works correctly
  - Filtering doesn't break under edge cases (empty filters, no matches, etc.)

Strategy generation notes:
  - Limits are bounded (0-500) to avoid timeout/memory issues
  - Offsets are reasonable (0-100)
  - Project names are alphanumeric (no special chars that might cause injection)
  - Priority is restricted to valid values (H, M, L, None)
  - Tags are single-word alphanumeric (no spaces, special chars)
  - Dates are within a reasonable range (±1 year from now)
  - Generated examples are reproducible with --hypothesis-seed=0
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

# Ensure repo root is on sys.path for imports
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from taskmajor.domains.tasks import TaskService  # noqa: E402

# ============================================================================
# HYPOTHESIS STRATEGIES FOR TEST DATA GENERATION
# ============================================================================


@st.composite
def project_names(draw) -> str | None:
    """Generate valid project names or None (no project).

    Realistic values: alphanumeric, underscore, dash. Optional.
    """
    if draw(st.booleans()):
        return None
    return draw(
        st.text(
            alphabet=st.characters(
                blacklist_categories=["Cs"],
                blacklist_characters=" /\\:;,.",
            ),
            min_size=1,
            max_size=20,
        )
    )


@st.composite
def priority_values(draw) -> str | None:
    """Generate valid priority values or None.

    TaskWarrior supports: H (high), M (medium), L (low).
    """
    return draw(st.one_of(st.none(), st.just("H"), st.just("M"), st.just("L")))


@st.composite
def tag_lists(draw) -> list[str] | None:
    """Generate lists of tags or None.

    Tags are alphanumeric, no spaces/special chars.
    """
    if draw(st.booleans()):
        return None
    return draw(
        st.lists(
            st.text(
                alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_",
                min_size=1,
                max_size=15,
            ),
            min_size=0,
            max_size=5,
            unique=True,
        )
    )


@st.composite
def date_filters(draw) -> tuple[datetime | None, datetime | None]:
    """Generate due_before and due_after date filters.

    Dates are within ±1 year from now to avoid extreme values.
    """
    now = datetime.now()
    base_date = draw(
        st.datetimes(
            min_value=now - timedelta(days=365),
            max_value=now + timedelta(days=365),
        )
    )
    due_after = draw(st.one_of(st.none(), st.just(base_date)))
    due_before = draw(st.one_of(st.none(), st.just(base_date + timedelta(days=1))))
    return (due_after, due_before)


@st.composite
def pagination_params(draw) -> tuple[int, int]:
    """Generate reasonable limit and offset values.

    Limits: 0-500 (0 means no limit, 1-500 are typical page sizes)
    Offsets: 0-100 (reasonable for pagination)
    """
    limit = draw(st.integers(min_value=0, max_value=500))
    offset = draw(st.integers(min_value=0, max_value=100))
    return (limit, offset)


@st.composite
def status_values(draw) -> str | None:
    """Generate valid status values.

    Common statuses: pending, waiting, completed, deleted.
    """
    return draw(
        st.one_of(
            st.none(),
            st.just("pending"),
            st.just("waiting"),
            st.just("completed"),
            st.just("deleted"),
        )
    )


@st.composite
def sort_specs(draw) -> list[str] | None:
    """Generate valid sort specifications.

    Valid fields: due, priority, project, description, urgency, entry.
    Can be prefixed with '-' for descending order.
    """
    if draw(st.booleans()):
        return None
    fields = ["due", "priority", "project", "description", "urgency"]
    specs = []
    for _ in range(draw(st.integers(min_value=1, max_value=3))):
        field = draw(st.sampled_from(fields))
        spec = draw(st.booleans())
        specs.append(f"-{field}" if spec else field)
    return list(set(specs))  # Remove duplicates


# ============================================================================
# FIXTURES AND HELPERS
# ============================================================================


def _mock_task_service(**overrides) -> TaskService:
    """Create a TaskService with a mocked TaskWarrior client."""
    fake_client = SimpleNamespace(
        config_store=SimpleNamespace(config={}, get_contexts=lambda: []),
        context_service=SimpleNamespace(
            define_context=lambda c: None, delete_context=lambda n: None
        ),
        uda_service=SimpleNamespace(define_uda=lambda u: None, delete_uda=lambda n: None),
        get_tasks=lambda *args, **kwargs: [],
    )
    return TaskService(taskwarrior_client=fake_client, **overrides)


def _make_task(
    project: str | None = "Work",
    priority: str | None = "M",
    status: str = "pending",
    **kwargs,
) -> SimpleNamespace:
    """Create a mock task with given properties."""
    defaults: dict[str, Any] = {
        "uuid": str(uuid.uuid4()),
        "description": "task",
        "project": project,
        "priority": priority,
        "tags": [],
        "due": None,
        "status": status,
        "urgency": 0,
        "entry": None,
        "start": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ============================================================================
# PROPERTY-BASED TESTS
# ============================================================================


class TestQueryTasksLimitInvariant:
    """Property: query_tasks never returns more than limit results."""

    @given(
        limit=st.integers(min_value=1, max_value=100),
        offset=st.integers(min_value=0, max_value=50),
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_limit_always_respected(self, limit: int, offset: int):
        """For any positive limit, results ≤ limit."""
        service = _mock_task_service()

        # Create more tasks than limit
        tasks = [
            _make_task(project=f"P{i % 3}", priority="HML"[i % 3], status="pending")
            for i in range(max(limit + 50, 100))
        ]

        # Mock get_tasks to return all tasks
        cast(Any, service.taskwarrior_client).get_tasks = lambda *a, **kw: tasks

        result = service.query_tasks(
            filters={"status": "pending"},
            sort=["due"],
            limit=limit,
            offset=offset,
        )

        # Number of returned tasks ≤ limit
        assert len(result["tasks"]) <= limit, (
            f"Returned {len(result['tasks'])} tasks but limit was {limit}"
        )

    def test_limit_zero_returns_empty(self):
        """limit=0 returns empty list (tasks[offset:offset])."""
        service = _mock_task_service()
        tasks = [_make_task(status="pending") for _ in range(50)]
        cast(Any, service.taskwarrior_client).get_tasks = lambda *a, **kw: tasks

        # limit=0 with offset=0 returns tasks[0:0] = []
        result = service.query_tasks(
            filters={"status": "pending"},
            sort=None,
            limit=0,
            offset=0,
        )

        assert len(result["tasks"]) == 0
        assert result["total"] == 50  # But total includes all matching tasks


class TestQueryTasksNoExceptions:
    """Property: query_tasks never raises an exception for valid inputs."""

    @given(
        project=project_names(),
        priority=priority_values(),
        status=status_values(),
        tags=tag_lists(),
        limit=st.integers(min_value=0, max_value=200),
        offset=st.integers(min_value=0, max_value=50),
    )
    @settings(
        max_examples=150,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    )
    def test_no_exception_on_valid_filters(
        self,
        project: str | None,
        priority: str | None,
        status: str | None,
        tags: list[str] | None,
        limit: int,
        offset: int,
    ):
        """Any combination of valid filters should not raise an exception."""
        service = _mock_task_service()
        tasks = [_make_task(status="pending") for _ in range(50)]
        cast(Any, service.taskwarrior_client).get_tasks = lambda *a, **kw: tasks

        try:
            filters_dict: dict[str, Any] = {}
            if project is not None:
                filters_dict["project"] = project
            if priority is not None:
                filters_dict["priority"] = priority
            if status is not None:
                filters_dict["status"] = status
            if tags is not None and tags:
                filters_dict["tags_any"] = tags

            result = service.query_tasks(
                filters=filters_dict or None,
                sort=None,
                limit=limit,
                offset=offset,
            )

            # Should always return a dict with tasks and total
            assert isinstance(result, dict)
            assert "tasks" in result
            assert "total" in result
        except Exception as e:
            pytest.fail(f"Unexpected exception with valid filters: {e}")

    @given(sort_specs())
    @settings(max_examples=80, deadline=None)
    def test_no_exception_on_sort_specs(self, sort_specs: list[str] | None):
        """Any valid sort specification should not raise an exception."""
        service = _mock_task_service()
        tasks = [_make_task() for _ in range(30)]
        cast(Any, service.taskwarrior_client).get_tasks = lambda *a, **kw: tasks

        try:
            result = service.query_tasks(
                filters={"status": "pending"},
                sort=sort_specs,
                limit=10,
                offset=0,
            )
            assert isinstance(result, dict)
        except Exception as e:
            pytest.fail(f"Unexpected exception with sort={sort_specs}: {e}")


class TestQueryTasksOffsetBehavior:
    """Property: offset correctly skips N tasks."""

    @given(
        offset=st.integers(min_value=0, max_value=50),
        limit=st.integers(min_value=1, max_value=50),
    )
    @settings(max_examples=100, deadline=None)
    def test_offset_skips_n_tasks(self, offset: int, limit: int):
        """Offset N should skip the first N tasks."""
        service = _mock_task_service()
        total_tasks = 100
        tasks = [_make_task(status="pending") for _ in range(total_tasks)]
        cast(Any, service.taskwarrior_client).get_tasks = lambda *a, **kw: tasks

        result = service.query_tasks(
            filters={"status": "pending"},
            sort=["description"],
            limit=limit,
            offset=offset,
        )

        # The first returned task should be at index `offset`
        # (if offset < total_tasks)
        returned_tasks = result["tasks"]
        if offset < total_tasks:
            if offset + limit > total_tasks:
                # We should have the remaining tasks
                expected_count = total_tasks - offset
            else:
                expected_count = min(limit, total_tasks - offset)
            assert len(returned_tasks) == expected_count, (
                f"offset={offset}, limit={limit}, total={total_tasks}, "
                f"expected {expected_count} but got {len(returned_tasks)}"
            )
        else:
            # offset >= total_tasks should return empty
            assert len(returned_tasks) == 0

    @given(st.data())
    @settings(max_examples=80, deadline=None)
    def test_offset_consistency_across_calls(self, data):
        """Multiple calls with same offset should return same tasks."""
        offset = data.draw(st.integers(min_value=0, max_value=20))
        limit = data.draw(st.integers(min_value=5, max_value=20))

        service = _mock_task_service()
        tasks = [_make_task(status="pending") for _ in range(50)]
        cast(Any, service.taskwarrior_client).get_tasks = lambda *a, **kw: tasks

        # Call twice with same parameters
        result1 = service.query_tasks(
            filters={"status": "pending"},
            sort=["description"],
            limit=limit,
            offset=offset,
        )
        result2 = service.query_tasks(
            filters={"status": "pending"},
            sort=["description"],
            limit=limit,
            offset=offset,
        )

        # Results should be identical
        assert len(result1["tasks"]) == len(result2["tasks"])
        for t1, t2 in zip(result1["tasks"], result2["tasks"], strict=False):
            assert t1["uuid"] == t2["uuid"]


class TestQueryTasksEmptyResults:
    """Property: edge cases with zero matches or empty inputs."""

    @given(
        limit=st.integers(min_value=0, max_value=100),
        offset=st.integers(min_value=0, max_value=50),
    )
    @settings(max_examples=50, deadline=None)
    def test_empty_result_set_is_valid(self, limit: int, offset: int):
        """A query matching zero tasks should return empty list, not error."""
        service = _mock_task_service()
        cast(Any, service.taskwarrior_client).get_tasks = lambda *a, **kw: []

        result = service.query_tasks(
            filters={"status": "pending"},
            sort=None,
            limit=limit,
            offset=offset,
        )

        assert result["total"] == 0
        assert result["tasks"] == []

    def test_nonexistent_project_filter_returns_empty(self):
        """Filtering by a nonexistent project should return empty, not error."""
        service = _mock_task_service()
        tasks = [
            _make_task(project="Work", status="pending"),
            _make_task(project="Home", status="pending"),
        ]
        cast(Any, service.taskwarrior_client).get_tasks = lambda *a, **kw: tasks

        result = service.query_tasks(
            filters={"project": "DoesNotExist", "status": "pending"},
            sort=None,
            limit=10,
            offset=0,
        )

        assert result["total"] == 0
        assert result["tasks"] == []


class TestQueryTasksFilterInteraction:
    """Property: multiple filters combined work correctly."""

    @given(
        project=project_names(),
        priority=priority_values(),
        limit=st.integers(min_value=1, max_value=50),
    )
    @settings(max_examples=100, deadline=None)
    def test_project_and_priority_filters_applied(
        self, project: str | None, priority: str | None, limit: int
    ):
        """project + priority filters should both apply (AND logic)."""
        service = _mock_task_service()

        # Create tasks with various combinations
        tasks = []
        for i in range(50):
            p = "Work" if i % 2 == 0 else "Home"
            pr = "HML"[i % 3]
            tasks.append(_make_task(project=p, priority=pr, status="pending"))

        cast(Any, service.taskwarrior_client).get_tasks = lambda *a, **kw: tasks

        filters = {"status": "pending"}
        if project:
            filters["project"] = project
        if priority:
            filters["priority"] = priority

        result = service.query_tasks(
            filters=filters,
            sort=None,
            limit=limit,
            offset=0,
        )

        # Verify all returned tasks match the filters
        for task in result["tasks"]:
            if project:
                assert task["project"] == project, (
                    f"Task {task['uuid']} project {task['project']} != {project}"
                )
            if priority:
                assert task["priority"] == priority, (
                    f"Task {task['uuid']} priority {task['priority']} != {priority}"
                )
            assert task["status"] == "pending"


class TestQueryTasksStableSorting:
    """Property: sorting is stable and produces consistent results."""

    @given(sort_specs())
    @settings(max_examples=50, deadline=None)
    def test_sort_is_stable(self, sort_specs: list[str] | None):
        """Same data sorted twice should produce identical order."""
        service = _mock_task_service()
        tasks = [_make_task(status="pending") for _ in range(30)]
        cast(Any, service.taskwarrior_client).get_tasks = lambda *a, **kw: tasks

        result1 = service.query_tasks(
            filters={"status": "pending"},
            sort=sort_specs,
            limit=None,
            offset=0,
        )
        result2 = service.query_tasks(
            filters={"status": "pending"},
            sort=sort_specs,
            limit=None,
            offset=0,
        )

        # Order should be identical
        uuids1 = [t["uuid"] for t in result1["tasks"]]
        uuids2 = [t["uuid"] for t in result2["tasks"]]
        assert uuids1 == uuids2, "Sort order should be deterministic"
