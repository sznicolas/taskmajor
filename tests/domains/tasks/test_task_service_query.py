import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

# Ensure repo root is on sys.path for imports when running tests directly
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from taskmajor.domains.tasks import TaskService  # noqa: E402


class FakeTaskWarrior:
    """Minimal TaskWarrior stub for unit tests.

    Simulates get_tasks() filtering by status (via include_completed /
    include_deleted flags).  Project, priority and other field filters are
    applied by TaskService._matches_filters() — not here — so this fake does
    NOT need to replicate that logic.

    Known limitations:
    - Does not simulate complex date filters (due:, scheduled:, …).
    - Does not simulate TaskWarrior filter expressions (e.g. "(+tag or -tag)").
    - The first positional argument to get_tasks() (a raw filter string used
      by the real TaskWarrior) is accepted but intentionally ignored.
    """

    def __init__(self, tasks):
        self._tasks = tasks
        # minimal config_store expected by TaskConfigService
        self.config_store = SimpleNamespace(config={}, get_contexts=lambda: [])
        # minimal services used by TaskConfigService
        self.context_service = SimpleNamespace(
            define_context=lambda c: None, delete_context=lambda n: None
        )
        self.uda_service = SimpleNamespace(define_uda=lambda u: None, delete_uda=lambda n: None)

    def get_tasks(self, *_args, include_completed=False, include_deleted=False):
        """Return tasks filtered by completion/deletion flags.

        The real TaskWarrior only returns completed/deleted tasks when the
        corresponding flag is set.  Pending and waiting tasks are always
        included.
        """
        result = []
        for task in self._tasks:
            status = getattr(task, "status", "pending")
            if status == "completed" and not include_completed:
                continue
            if status == "deleted" and not include_deleted:
                continue
            result.append(task)
        return result

    def get_task(self, task_id):
        for t in self._tasks:
            if str(t.uuid) == str(task_id):
                return t
        return None

    def add_task(self, task_input):
        new_task = SimpleNamespace(
            uuid=uuid.uuid4(),
            description=task_input.description,
            project=getattr(task_input, "project", None),
            priority=getattr(task_input, "priority", None),
            tags=getattr(task_input, "tags", []),
            due=None,
            status="pending",
            urgency=0,
            entry=None,
        )
        self._tasks.append(new_task)
        return new_task


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_task(**kwargs):
    defaults = {
        "uuid": uuid.uuid4(),
        "description": "task",
        "project": None,
        "priority": None,
        "tags": [],
        "due": None,
        "status": "pending",
        "urgency": 0,
        "entry": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@pytest.fixture
def sample_tasks():
    """A diverse set of tasks covering multiple projects, priorities and statuses."""
    return [
        _make_task(
            description="Pending Work H", project="Work", priority="H", status="pending", urgency=9
        ),
        _make_task(
            description="Pending Work M", project="Work", priority="M", status="pending", urgency=5
        ),
        _make_task(
            description="Pending Inbox", project="Inbox", priority="L", status="pending", urgency=2
        ),
        _make_task(
            description="Completed Work",
            project="Work",
            priority="M",
            status="completed",
            urgency=0,
        ),
        _make_task(
            description="Deleted task", project="Inbox", priority=None, status="deleted", urgency=0
        ),
        _make_task(
            description="No project task", project=None, priority="H", status="pending", urgency=7
        ),
    ]


@pytest.fixture
def service(sample_tasks):
    fake = FakeTaskWarrior(sample_tasks)
    return TaskService(taskwarrior_client=fake)


# ---------------------------------------------------------------------------
# Existing tests (must still pass)
# ---------------------------------------------------------------------------


def test_query_tasks_returns_tasks(service):
    res = service.query_tasks(filters={"status": "pending"}, sort=["-urgency"], limit=10, offset=0)
    assert isinstance(res, dict)
    assert "tasks" in res and "total" in res
    # 4 pending tasks in sample_tasks
    assert res["total"] == 4


def test_query_tasks_negative_limit_raises(service):
    with pytest.raises(ValueError):
        service.query_tasks(filters={"status": "pending"}, limit=-1)


def test_query_tasks_negative_offset_raises(service):
    with pytest.raises(ValueError):
        service.query_tasks(filters={"status": "pending"}, offset=-5)


# ---------------------------------------------------------------------------
# Filter-verification tests
# ---------------------------------------------------------------------------


def test_query_tasks_filters_by_project(service):
    """Only tasks belonging to the requested project are returned."""
    res = service.query_tasks(filters={"project": "Work", "status": "pending"})
    descriptions = [t["description"] for t in res["tasks"]]
    assert all("Work" in d for d in descriptions), descriptions
    assert res["total"] == 2


def test_query_tasks_filters_by_priority(service):
    """Only tasks with the requested priority are returned."""
    res = service.query_tasks(filters={"priority": "H", "status": "pending"})
    priorities = [t["priority"] for t in res["tasks"]]
    assert all(p == "H" for p in priorities), priorities
    assert res["total"] == 2  # "Pending Work H" + "No project task"


def test_query_tasks_filters_by_status_completed(service):
    """Completed tasks are returned only when status=completed is requested."""
    res = service.query_tasks(filters={"status": "completed"})
    statuses = [t["status"] for t in res["tasks"]]
    assert all(s == "completed" for s in statuses), statuses
    assert res["total"] == 1


def test_query_tasks_filters_by_status_pending_excludes_completed(service):
    """Pending filter must not include completed or deleted tasks."""
    res = service.query_tasks(filters={"status": "pending"})
    statuses = {t["status"] for t in res["tasks"]}
    assert statuses == {"pending"}, statuses


def test_query_tasks_empty_project_filter_returns_all_pending(service):
    """No project filter → all pending tasks are returned regardless of project."""
    res = service.query_tasks(filters={"status": "pending"})
    assert res["total"] == 4


def test_query_tasks_project_and_priority_combined(service):
    """project + priority filters are AND-ed together."""
    res = service.query_tasks(filters={"project": "Work", "priority": "M", "status": "pending"})
    assert res["total"] == 1
    assert res["tasks"][0]["description"] == "Pending Work M"


def test_query_tasks_no_match_returns_empty(service):
    """A filter that matches nothing returns an empty list, not an error."""
    res = service.query_tasks(filters={"project": "DoesNotExist", "status": "pending"})
    assert res["total"] == 0
    assert res["tasks"] == []


def test_query_tasks_task_without_project_excluded_by_project_filter(service):
    """Tasks that have no project are excluded when a project filter is applied."""
    res = service.query_tasks(filters={"project": "Work", "status": "pending"})
    descriptions = [t["description"] for t in res["tasks"]]
    assert "No project task" not in descriptions
