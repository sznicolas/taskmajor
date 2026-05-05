"""Task filter models, priority enum, and API constants for the tasks domain."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import IntEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class Priority(IntEnum):
    """Task priority levels, ordered from highest to lowest urgency."""

    H = 0
    M = 1
    L = 2
    NONE = 3  # tasks without priority sort last


SUPPORTED_TASK_BY_SCOPE = {"project", "priority", "day", "week"}
SUPPORTED_QUERY_STATUSES = {"pending", "waiting", "completed", "deleted"}
PRIORITY_ORDER = {p.name: p.value for p in Priority if p != Priority.NONE}

METADATA_VIEWS = ["review", "today", "week", "overdue"]
METADATA_SUPPORTED_FILTERS = [
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
]
METADATA_SUPPORTED_SORTS = ["due", "-due", "priority", "-priority", "project", "urgency"]
METADATA_RESOURCE_URIS = {
    "review": "taskmajor://queue/unsorted",
    "inbox": "taskmajor://queue/unsorted",
    "today": "taskmajor://agenda/today",
    "week": "taskmajor://agenda/week",
    "overdue": "taskmajor://status/overdue",
    "stats": "taskmajor://analytics/summary",
    "metadata": "taskmajor://config/schema",
    "context": "taskmajor://context/current",
    "errors": "taskmajor://debug/errors",
    "undo": "taskmajor://history/undo",
}
METADATA_TAG_CONVENTIONS = {
    "contexts": {"prefix": "+@"},
    "lists": {"prefix": "+"},
}
METADATA_API_VERSION = "2.1"


class TaskQueryFilters(BaseModel):
    """Supported task filters exposed through the MCP business tools."""

    model_config = ConfigDict(extra="forbid")

    project: str | None = None
    projects: list[str] | None = None
    priority: str | None = None
    status: str | list[str] | None = None
    tags_any: list[str] | None = None
    tags_all: list[str] | None = None
    due_before: str | datetime | None = None
    due_after: str | datetime | None = None
    text: str | None = None
    has_depends: bool | None = None
    is_blocked: bool | None = None

    @field_validator("tags_any", "tags_all", mode="before")
    @classmethod
    def normalize_tag_filter(cls, tags: list[str] | None) -> list[str] | None:
        """Strip leading '+', remove duplicates and empty tags."""
        if tags is None:
            return None
        normalized: list[str] = []
        seen: set[str] = set()
        for tag in tags:
            normalized_tag = tag.strip().lstrip("+")
            if not normalized_tag:
                raise ValueError("Tag filters must not be empty.")
            if normalized_tag not in seen:
                seen.add(normalized_tag)
                normalized.append(normalized_tag)
        return normalized

    @field_validator("priority", mode="before")
    @classmethod
    def validate_priority(cls, value: str | None) -> str | None:
        """Validate priority is one of H, M, L."""
        if value is None:
            return None
        upper = value.strip().upper()
        if upper not in ("H", "M", "L"):
            raise ValueError(f"Invalid priority {value!r}. Must be 'H', 'M', or 'L'.")
        return upper

    @model_validator(mode="after")
    def validate_filter_combinations(self) -> TaskQueryFilters:
        """Reject ambiguous filter combinations early."""
        if self.project and self.projects:
            raise ValueError("Use either 'project' or 'projects', not both.")
        return self


def normalize_filters(
    filters: TaskQueryFilters | Mapping[str, Any] | None,
) -> TaskQueryFilters:
    """Coerce a raw mapping or None into a TaskQueryFilters instance."""
    if filters is None:
        return TaskQueryFilters()
    if isinstance(filters, TaskQueryFilters):
        return filters
    return TaskQueryFilters.model_validate(dict(filters))


def normalize_statuses(status: str | Sequence[str] | None) -> list[str]:
    """Validate and normalize a status value or list into lowercase strings."""
    if status is None:
        return ["pending"]

    values = [status] if isinstance(status, str) else list(status)
    normalized: list[str] = []
    for value in values:
        lowered = value.lower()
        if lowered == "all":
            normalized.extend(sorted(SUPPORTED_QUERY_STATUSES))
            continue
        if lowered not in SUPPORTED_QUERY_STATUSES:
            raise ValueError(
                f"Unsupported status '{value}'. "
                f"Use one of: {', '.join(sorted(SUPPORTED_QUERY_STATUSES | {'all'}))}."
            )
        normalized.append(lowered)

    return list(dict.fromkeys(normalized))
