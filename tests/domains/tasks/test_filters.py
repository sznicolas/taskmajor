from __future__ import annotations

import pytest
from pydantic import ValidationError

from taskmajor.domains.tasks import TaskQueryFilters

# ---------------------------------------------------------------------------
# Valid cases
# ---------------------------------------------------------------------------

def test_empty_filters_all_none():
    f = TaskQueryFilters()
    assert f.project is None
    assert f.projects is None
    assert f.priority is None
    assert f.status is None
    assert f.tags_any is None
    assert f.tags_all is None
    assert f.due_before is None
    assert f.due_after is None
    assert f.text is None


def test_single_project():
    f = TaskQueryFilters(project="work")
    assert f.project == "work"


def test_multiple_projects():
    f = TaskQueryFilters(projects=["work", "home"])
    assert f.projects == ["work", "home"]


def test_priority_high():
    f = TaskQueryFilters(priority="H")
    assert f.priority == "H"


def test_priority_medium():
    f = TaskQueryFilters(priority="M")
    assert f.priority == "M"


def test_priority_low():
    f = TaskQueryFilters(priority="L")
    assert f.priority == "L"


def test_priority_lowercase_normalized():
    f = TaskQueryFilters(priority="h")
    assert f.priority == "H"


def test_priority_lowercase_m_normalized():
    f = TaskQueryFilters(priority="m")
    assert f.priority == "M"


def test_tags_plus_prefix_stripped():
    f = TaskQueryFilters(tags_any=["+urgent"])
    assert f.tags_any == ["urgent"]


def test_tags_deduplicated():
    f = TaskQueryFilters(tags_any=["a", "a"])
    assert f.tags_any == ["a"]


def test_tags_all_plus_prefix_stripped():
    f = TaskQueryFilters(tags_all=["+focus", "+work"])
    assert f.tags_all == ["focus", "work"]


def test_status_string():
    f = TaskQueryFilters(status="pending")
    assert f.status == "pending"


def test_status_list():
    f = TaskQueryFilters(status=["pending", "waiting"])
    assert f.status == ["pending", "waiting"]


def test_text_filter():
    f = TaskQueryFilters(text="buy milk")
    assert f.text == "buy milk"


# ---------------------------------------------------------------------------
# Invalid cases
# ---------------------------------------------------------------------------

def test_project_and_projects_raises():
    with pytest.raises(ValidationError):
        TaskQueryFilters(project="work", projects=["home"])


def test_empty_tag_raises():
    with pytest.raises(ValidationError):
        TaskQueryFilters(tags_any=[""])


def test_invalid_priority_raises():
    with pytest.raises(ValidationError):
        TaskQueryFilters(priority="X")


def test_unknown_field_raises():
    with pytest.raises(ValidationError):
        TaskQueryFilters(unknown_field="x")  # type: ignore[call-arg]
