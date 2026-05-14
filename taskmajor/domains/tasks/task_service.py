"""
Task Service - Business logic layer for task management.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, time, timedelta
from typing import Any, cast

from taskwarrior import ContextDTO, TaskInputDTO, TaskOutputDTO, TaskWarrior

from taskmajor.domains.taskwarrior import TaskConfigService

from ._helpers import (
    coerce_datetime,
    format_tag,
    is_taskwarrior_date_expr,
    normalize_sort_specs,
    serialize_datetime,
)
from .filters import (
    METADATA_API_VERSION,
    METADATA_RESOURCE_URIS,
    METADATA_SUPPORTED_FILTERS,
    METADATA_SUPPORTED_SORTS,
    METADATA_TAG_CONVENTIONS,
    METADATA_VIEWS,
    PRIORITY_ORDER,
    SUPPORTED_TASK_BY_SCOPE,
    Priority,
    TaskQueryFilters,
    normalize_filters,
    normalize_statuses,
)
from .storage import TaskStorage


class TaskService:
    """
    Service class for task management operations using pytaskwarrior.
    """

    def __init__(
        self,
        taskwarrior_client: TaskWarrior | Any,
    ):
        """
        Initialize the TaskService.

        Args:
            taskwarrior_client: Pre-configured TaskWarrior client.
        """
        self.taskwarrior_client = taskwarrior_client
        self.task_config = TaskConfigService(taskwarrior_client)
        self.storage = TaskStorage()
        self.logger = logging.getLogger(__name__)

    def refresh_task_from_taskwarrior(self, task_id: str) -> TaskOutputDTO | None:
        """
        Refresh a task from TaskWarrior, updating the storage.

        Args:
            task_id: The ID of the task to refresh

        Returns:
            TaskOutputDTO: The refreshed task object, or None if not found
        """
        try:
            task = self.taskwarrior_client.get_task(task_id)
            if task:
                self.storage.refresh_task(task_id, task)
                return task
            return None
        except Exception:
            self.logger.debug("Failed to refresh task %s from TaskWarrior", task_id, exc_info=True)
            return None

    def list_pending_tasks(self) -> list[TaskOutputDTO]:
        """
        List all pending tasks from TaskWarrior.

        Returns:
            list[TaskOutputDTO]: A list of pending tasks with their details
        """
        pending_tasks = self.taskwarrior_client.get_tasks()

        for task in pending_tasks:
            self.storage.store_task(task.uuid, task)

        return pending_tasks

    def _mark_storage_completed(self, task_id: str) -> None:
        """Mark a task as completed in local storage (best-effort)."""
        try:
            self.storage.mark_task_completed(task_id)
        except (KeyError, ValueError):
            self.logger.debug("Failed to mark task %s completed in storage", task_id)

    def complete_task(self, task_id: str) -> bool:
        """
        Mark a task as completed.

        Args:
            task_id: The ID of the task to complete

        Returns:
            bool: True if task was successfully completed, False otherwise
        """
        try:
            result = cast(Any, self.taskwarrior_client.done_task(task_id))
        except Exception:
            self.logger.exception("TaskWarrior.done_task raised an exception for %s", task_id)
            # done_task raised — verify if TaskWarrior actually completed the task anyway
            return self._verify_task_completed(task_id)

        # Trust the returned object's status if available
        if result is not None and str(getattr(result, "status", "")).lower() == "completed":
            self._mark_storage_completed(task_id)
            return True

        # Fallback: query TaskWarrior for the current state
        return self._verify_task_completed(task_id)

    def _verify_task_completed(self, task_id: str) -> bool:
        """Query TaskWarrior to verify a task is completed. Updates storage if so."""
        try:
            task = self.taskwarrior_client.get_task(task_id)
            if task and str(getattr(task, "status", "")).lower() == "completed":
                self._mark_storage_completed(task_id)
                return True
        except Exception:
            self.logger.debug("Failed to verify completion state for task %s", task_id)
        return False

    def add_task(self, task_input: TaskInputDTO) -> TaskOutputDTO:
        """
        Add a new task to TaskWarrior.

        Args:
            task_input: The task input data

        Returns:
            TaskOutputDTO: The created task object
        """
        task = self.taskwarrior_client.add_task(task_input)
        self.storage.store_task(task.uuid, task)
        return task

    def update_task(self, task_id: str, task_input: TaskInputDTO) -> TaskOutputDTO:
        """
        Update an existing task in TaskWarrior.

        Can be used for both triage classification (project, priority, due, tags) and
        advanced field modification (description, recurrence, dependencies, etc.).

        Validates that at least one field would be modified before applying changes.

        Args:
            task_id: The ID of the task to update
            task_input: The updated task data

        Returns:
            TaskOutputDTO: The updated task object

        Raises:
            ValueError: If no fields would be modified (new values match current state)
        """
        # Get current task to validate that at least one field would change
        current_task = self.taskwarrior_client.get_task(task_id)
        if not current_task:
            raise ValueError(f"Task {task_id} not found")

        # Check which fields are being updated
        fields_to_update = task_input.model_dump(exclude_unset=True)

        # Validate that at least one field would actually change
        has_changes = False
        for field, new_value in fields_to_update.items():
            current_value = getattr(current_task, field, None)
            # For list/set fields, compare as sets to handle order differences
            if isinstance(new_value, list) and isinstance(current_value, (list, set)):
                if set(new_value) != set(current_value or []):
                    has_changes = True
                    break
            # For dict fields (udas), compare as dicts
            elif isinstance(new_value, dict) and isinstance(current_value, dict):
                if new_value != (current_value or {}):
                    has_changes = True
                    break
            # For scalar fields, direct comparison
            elif new_value != current_value:
                has_changes = True
                break

        if not has_changes:
            raise ValueError("No changes detected: at least one field must be modified")

        task = self.taskwarrior_client.modify_task(task_input, task_id)
        self.storage.refresh_task(task_id, task)
        return task

    def delete_task(self, task_id: str) -> bool:
        """
        Mark a task as deleted (soft delete).

        Args:
            task_id: The ID of the task to delete

        Returns:
            bool: True if task was successfully marked as deleted, False otherwise
        """
        if task_id not in self.storage.list_tasks():
            task = self.taskwarrior_client.get_task(task_id)
            if not task:
                return False
        self.taskwarrior_client.delete_task(task_id)
        self.storage.delete_task(task_id)
        return True

    def start_task(self, task_id: str) -> bool:
        """
        Start working on a task.

        Args:
            task_id: The ID of the task to start

        Returns:
            bool: True if task was successfully started, False otherwise
        """
        try:
            task = self.storage.get_task(task_id)

            if not task:
                fetched_task = self.taskwarrior_client.get_task(task_id)
                if not fetched_task:
                    return False
                self.storage.store_task(task_id, fetched_task)

            self.taskwarrior_client.start_task(task_id)
            return True

        except Exception:
            self.logger.exception("Failed to start task %s", task_id)
            return False

    def stop_task(self, task_id: str) -> bool:
        """
        Stop working on a task.

        Args:
            task_id: The ID of the task to stop

        Returns:
            bool: True if task was successfully stopped, False otherwise
        """
        try:
            task = self.storage.get_task(task_id)

            if not task:
                fetched_task = self.taskwarrior_client.get_task(task_id)
                if not fetched_task:
                    return False
                self.storage.store_task(task_id, fetched_task)

            self.taskwarrior_client.stop_task(task_id)
            return True

        except Exception:
            self.logger.exception("Failed to stop task %s", task_id)
            return False

    def list_completed_tasks(self) -> list[TaskOutputDTO]:
        """
        Get all completed tasks.

        Returns:
            list[TaskOutputDTO]: A list of completed tasks
        """
        return self.storage.list_completed_tasks()

    def list_deleted_tasks(self) -> list[TaskOutputDTO]:
        """
        Get all deleted tasks.

        Returns:
            list[TaskOutputDTO]: A list of deleted tasks
        """
        return self.storage.list_deleted_tasks()

    def list_contexts(self) -> list[ContextDTO]:
        """
        Get the contexts.

        Returns:
            str | None: Name of current context or None if no context is active
        """
        try:
            contexts = self.taskwarrior_client.get_contexts()
        except Exception:
            self.logger.warning("Failed to fetch contexts from TaskWarrior", exc_info=True)
            return []

        if not contexts:
            return []

        try:
            return [context for context in contexts if getattr(context, "name", None)]
        except TypeError:
            return []

    def get_current_context(self) -> str | None:
        """
        Get the currently active context name.

        Returns:
            str | None: Name of current context or None if no context is active
        """
        try:
            current = self.taskwarrior_client.get_current_context()
        except Exception:
            self.logger.debug("Failed to get current context", exc_info=True)
            return None

        return current if isinstance(current, str) and current else None

    def set_context(self, context_name: str) -> bool:
        """
        Set the active context.

        Args:
            context_name: Name of the context to activate

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.taskwarrior_client.apply_context(context_name)
            self.storage = TaskStorage()
            return True
        except Exception:
            self.logger.exception("Failed to set context '%s'", context_name)
            return False

    def unset_context(self) -> bool:
        """
        Unset the current context.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.taskwarrior_client.unset_context()
            self.storage = TaskStorage()
            return True
        except Exception:
            self.logger.exception("Failed to unset context")
            return False

    def query_tasks(
        self,
        filters: TaskQueryFilters | Mapping[str, Any] | None = None,
        filter: str | None = None,
        sort: Sequence[str] | str | None = None,
        limit: int | None = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Return a paginated list of tasks matching the provided filters.

        Args:
            filters: Optional structured filters. Accepts either a
                TaskQueryFilters instance or a plain mapping with keys from
                TaskQueryFilters (project, projects, priority, status,
                tags_any, tags_all, due_before, due_after, text).
                Examples:
                    {"status": "pending"}
                    {"project": "Inbox", "tags_any": ["urgent"]}

            filter: Optional raw TaskWarrior filter string passed directly to
                the TaskWarrior CLI. Takes precedence over `filters` when both
                are provided. Supports the full TaskWarrior filter language,
                including date math, annotations and complex expressions.
                Example: "status:pending +feature due.before:tomorrow"

            sort: Optional sort order. Either a single sort string or a
                sequence of sort strings. Supported values include:
                'due', '-due', 'priority', '-priority', 'project', 'urgency',
                'description', 'status', 'entry'.
                Prefix '-' for descending order. Example: ['-urgency', 'due']

            limit: Maximum number of tasks to return (None for no limit).
                Must be >= 0. Defaults to 50.

            offset: Zero-based index of the first task to return. Must be >= 0.
                Defaults to 0.

        Returns:
            dict: Canonical MCP-style response with keys:
                - "tasks": list of serialized task objects (dicts)
                - "total": integer total number of matching tasks

        Raises:
            ValueError: If `limit` or `offset` are negative, or if filters are
                invalid (e.g., mutually exclusive 'project' and 'projects').

        Notes:
            - When `filters` is a plain mapping, it will be normalized using
              TaskQueryFilters. Unknown keys are rejected by the Pydantic model
              and will raise a validation error — do not pass arbitrary keys
              such as a top-level "description" field in the call payload.
            - Pagination is performed after sorting and filtering.
        """
        if offset < 0:
            raise ValueError("'offset' must be greater than or equal to 0.")
        if limit is not None and limit < 0:
            raise ValueError("'limit' must be greater than or equal to 0.")

        tasks = self._query_task_objects(filters=filters, filter=filter, sort=sort)
        total = len(tasks)
        end = None if limit is None else offset + limit
        page = tasks[offset:end]
        return {
            "tasks": [self.serialize_task(task) for task in page],
            "total": total,
        }

    def get_stats(
        self,
        filters: TaskQueryFilters | Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return aggregate counts for the filtered task selection."""
        tasks = self._query_task_objects(filters=filters)
        by_status = Counter(task.status for task in tasks)
        by_project = Counter(task.project or "(none)" for task in tasks)
        by_priority = Counter(task.priority or "(none)" for task in tasks)

        return {
            "total": len(tasks),
            "by_status": dict(by_status),
            "by_project": dict(by_project),
            "by_priority": dict(by_priority),
            "overdue": sum(1 for task in tasks if self._is_overdue(task)),
        }

    def get_tasks_by_scope(
        self,
        scope: str,
        filters: TaskQueryFilters | Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Group filtered tasks into buckets by scope."""
        if scope not in SUPPORTED_TASK_BY_SCOPE:
            raise ValueError(
                f"Unsupported scope '{scope}'. "
                f"Use one of: {', '.join(sorted(SUPPORTED_TASK_BY_SCOPE))}."
            )

        tasks = self._query_task_objects(filters=filters)
        groups = defaultdict(list)
        for task in tasks:
            groups[self._roadmap_key(task, scope)].append(task)

        roadmap_groups = [
            {
                "key": key,
                "tasks": [self.serialize_task(task) for task in bucket],
                "total": len(bucket),
            }
            for key, bucket in sorted(groups.items(), key=lambda item: item[0])
        ]

        return {
            "scope": scope,
            "groups": roadmap_groups,
            "total": len(tasks),
        }

    def next_task(
        self,
        filters: TaskQueryFilters | Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return the next recommended task using the canonical list response.

        Excludes tasks that are blocked by unresolved dependencies.
        """
        normalized = normalize_filters(filters).model_copy(deep=True)
        if normalized.status is None:
            normalized.status = "pending"

        # Get full TaskOutputDTO objects so we can inspect dependencies
        tasks = self._query_task_objects(
            filters=normalized, sort=["-urgency", "due", "priority", "description"]
        )

        # Exclude tasks that are blocked by unresolved dependencies
        actionable = [t for t in tasks if not self._is_blocked(t)]
        total_actionable = len(actionable)
        page = actionable[:1]

        result: dict[str, Any] = {
            "tasks": [self.serialize_task(t) for t in page],
            "total": total_actionable,
        }
        if page:
            result["selection_reason"] = "highest_urgency"
        return result

    def get_metadata(self) -> dict[str, Any]:
        """Return metadata collections useful for autocomplete and navigation."""
        tasks = self._query_task_objects(filters={"status": "pending"})
        active_context = self.get_current_context()
        available_contexts = {
            context.name for context in self.list_contexts() if getattr(context, "name", None)
        }
        if active_context:
            available_contexts.add(active_context)

        projects = sorted(
            {task.project for task in tasks if task.project},
            key=str.casefold,
        )
        tags = sorted(
            {format_tag(tag) for task in tasks for tag in (task.tags or [])},
            key=str.casefold,
        )
        context_tags = [
            tag for tag in tags if tag.startswith(METADATA_TAG_CONVENTIONS["contexts"]["prefix"])
        ]
        priorities = list(PRIORITY_ORDER)

        return {
            "projects": projects,
            "tags": tags,
            "context_tags": context_tags,
            "available_contexts": sorted(available_contexts, key=str.casefold),
            "active_context": active_context,
            "priorities": priorities,
            "recurrence_formats": ["daily", "2weeks", "every 3 days"],
            "views": list(METADATA_VIEWS),
            "supported_filters": list(METADATA_SUPPORTED_FILTERS),
            "supported_sorts": list(METADATA_SUPPORTED_SORTS),
            "tag_conventions": METADATA_TAG_CONVENTIONS,
            "resource_uris": METADATA_RESOURCE_URIS,
            "api_version": METADATA_API_VERSION,
        }

    def get_projects(self) -> dict[str, Any]:
        """Return all projects currently in use by pending tasks."""
        tasks = self._query_task_objects(filters={"status": "pending"})
        projects = sorted(
            {task.project for task in tasks if task.project},
            key=str.casefold,
        )
        return {
            "projects": projects,
            "total": len(projects),
        }

    def get_tags(self) -> dict[str, Any]:
        """Return all tags currently in use by pending tasks."""
        tasks = self._query_task_objects(filters={"status": "pending"})
        tags = sorted(
            {format_tag(tag) for task in tasks for tag in (task.tags or [])},
            key=str.casefold,
        )
        return {
            "tags": tags,
            "total": len(tags),
        }

    def get_udas(self) -> dict[str, Any]:
        """Return all UDAs defined in TaskWarrior configuration."""
        try:
            udas = self.taskwarrior_client.get_udas()
            return {
                "udas": udas,
                "total": len(udas),
            }
        except (AttributeError, NotImplementedError):
            self.logger.warning("get_udas not yet implemented in taskwarrior client")
            return {
                "udas": [],
                "total": 0,
                "note": "UDA support requires pytaskwarrior >= next version",
            }

    def serialize_task(self, task: TaskOutputDTO) -> dict[str, Any]:
        """Serialize a TaskWarrior task to the canonical MCP task shape.

        Always includes: uuid, description, project, priority, tags, due, status, depends.
        Includes annotations and udas if present.
        """
        base: dict[str, Any] = {
            "uuid": str(task.uuid),
            "description": task.description,
            "project": task.project,
            "priority": task.priority,
            "tags": list(task.tags or []),
            "due": serialize_datetime(task.due),
            "status": task.status,
            # critical fields
            "depends": list(getattr(task, "depends", []) or []),
        }

        # Conditionally include annotations to avoid noise
        annotations = getattr(task, "annotations", []) or []
        if annotations:
            base["annotations"] = [
                {
                    "id": getattr(a, "id", None),
                    "entry": serialize_datetime(getattr(a, "entry", None)),
                    "description": getattr(a, "description", None),
                }
                for a in annotations
            ]

        # Conditionally include udas
        udas = getattr(task, "udas", {}) or {}
        if udas:
            base["udas"] = dict(udas)

        return base

    def _query_task_objects(
        self,
        filters: TaskQueryFilters | Mapping[str, Any] | None = None,
        filter: str | None = None,
        sort: Sequence[str] | str | None = None,
    ) -> list[TaskOutputDTO]:
        if filter is not None:
            tasks = self._load_tasks_raw(filter)
            self._sort_tasks(tasks, sort)
            return tasks

        normalized = normalize_filters(filters)

        # If either due_before or due_after looks like a TaskWarrior date expression
        # (non-ISO string), construct a raw TaskWarrior filter and load via _load_tasks_raw.
        if (
            (isinstance(normalized.due_before, str) and is_taskwarrior_date_expr(normalized.due_before))
            or (isinstance(normalized.due_after, str) and is_taskwarrior_date_expr(normalized.due_after))
        ):
            parts: list[str] = []
            # include status filter(s)
            statuses = normalize_statuses(normalized.status)
            for s in statuses:
                parts.append(f"status:{s}")
            # include project
            if normalized.project:
                parts.append(f"project:{normalized.project}")
            # include tags_any (as +tag)
            if normalized.tags_any:
                parts.extend(format_tag(t) for t in normalized.tags_any)
            # include tags_all (all tags must be present; include as +tag)
            if normalized.tags_all:
                parts.extend(format_tag(t) for t in normalized.tags_all)
            # include due expressions
            if isinstance(normalized.due_before, str) and is_taskwarrior_date_expr(normalized.due_before):
                parts.append(f"due.before:{normalized.due_before}")
            if isinstance(normalized.due_after, str) and is_taskwarrior_date_expr(normalized.due_after):
                parts.append(f"due.after:{normalized.due_after}")

            filter_string = " ".join(parts)
            tasks = self._load_tasks_raw(filter_string)
            self._sort_tasks(tasks, sort)
            return tasks

        due_before = coerce_datetime(normalized.due_before)
        due_after = coerce_datetime(normalized.due_after)
        statuses = normalize_statuses(normalized.status)

        tasks = [
            task
            for task in self._load_tasks(statuses)
            if self._matches_filters(task, normalized, due_before=due_before, due_after=due_after)
        ]
        self._sort_tasks(tasks, sort)
        return tasks

    def _load_tasks_raw(self, filter_string: str) -> list[TaskOutputDTO]:
        """Load tasks using a raw TaskWarrior filter string."""
        return list(self.taskwarrior_client.get_tasks(filter_string))

    def _load_tasks(self, statuses: Sequence[str]) -> list[TaskOutputDTO]:
        include_completed = "completed" in statuses
        include_deleted = "deleted" in statuses
        tasks = self.taskwarrior_client.get_tasks(
            "",
            include_completed=include_completed,
            include_deleted=include_deleted,
        )
        return [task for task in tasks if task.status in statuses]

    def _matches_filters(
        self,
        task: TaskOutputDTO,
        filters: TaskQueryFilters,
        *,
        due_before: datetime | None,
        due_after: datetime | None,
    ) -> bool:
        tags = set(task.tags or [])

        if filters.project and task.project != filters.project:
            return False
        if filters.projects and task.project not in filters.projects:
            return False
        if filters.priority and (task.priority or "").upper() != filters.priority.upper():
            return False
        if filters.tags_any and tags.isdisjoint(filters.tags_any):
            return False
        if filters.tags_all and not set(filters.tags_all).issubset(tags):
            return False

        task_due = coerce_datetime(task.due)
        if due_before is not None:
            if task_due is None or task_due >= due_before:
                return False
        if due_after is not None:
            if task_due is None or task_due <= due_after:
                return False

        if filters.text:
            text = filters.text.lower()
            haystack = " ".join(
                part
                for part in [
                    task.description or "",
                    task.project or "",
                    " ".join(task.tags or []),
                ]
                if part
            ).lower()
            if text not in haystack:
                return False

        if filters.has_depends is not None:
            has_dep = bool(getattr(task, "depends", []) or [])
            if has_dep != filters.has_depends:
                return False

        if filters.is_blocked is not None:
            blocked = self._is_blocked(task)
            if blocked != filters.is_blocked:
                return False

        return True

    def _sort_tasks(self, tasks: list[TaskOutputDTO], sort: Sequence[str] | str | None) -> None:
        # Python's sort is stable, so applying sorts in reverse priority order
        # (last spec = highest priority) achieves correct multi-key sort even
        # when different fields have different sort directions (asc vs desc).
        specs = normalize_sort_specs(sort)
        for spec in reversed(specs):
            reverse = spec.startswith("-")
            field = spec[1:] if reverse else spec
            tasks.sort(key=lambda task: self._sort_key(task, field), reverse=reverse)

    def _sort_key(self, task: TaskOutputDTO, field: str) -> Any:
        if field == "description":
            return (task.description or "").lower()
        if field == "project":
            return (task.project or "~").lower()
        if field == "priority":
            return PRIORITY_ORDER.get(task.priority or "", Priority.NONE.value)
        if field == "due":
            due = coerce_datetime(task.due)
            return due or datetime.max.replace(tzinfo=UTC)
        if field == "status":
            return task.status
        if field == "urgency":
            return task.urgency or 0
        if field == "entry":
            entry = coerce_datetime(task.entry)
            return entry or datetime.max.replace(tzinfo=UTC)
        raise ValueError(
            "Unsupported sort field "
            f"'{field}'. Use one of: description, project, priority, due, status, urgency, entry."
        )

    def _is_overdue(self, task: TaskOutputDTO) -> bool:
        due = coerce_datetime(task.due)
        if due is None:
            return False
        return due < datetime.now(UTC)

    def _is_blocked(self, task: TaskOutputDTO) -> bool:
        """Return True if the given task is blocked by any dependency that is not completed.

        Uses the in-memory storage as a cache and falls back to the TaskWarrior
        client to fetch missing dependent tasks.
        """
        deps = getattr(task, "depends", []) or []
        for dep in deps:
            dep_id = str(dep)
            # Check cache first
            dep_task = self.storage.get_task(dep_id)
            if dep_task is None:
                try:
                    fetched = self.taskwarrior_client.get_task(dep_id)
                    if fetched:
                        dep_task = fetched
                        # cache for subsequent calls
                        try:
                            self.storage.store_task(dep_id, fetched)
                        except (KeyError, ValueError):
                            # Storage cache is best-effort
                            pass
                except Exception:
                    self.logger.warning(
                        "Failed to fetch dependency %s for task %s — skipping block check",
                        dep_id,
                        task.uuid,
                        exc_info=True,
                    )
                    dep_task = None
            if dep_task and getattr(dep_task, "status", None) != "completed":
                return True
        return False

    def _roadmap_key(self, task: TaskOutputDTO, scope: str) -> str:
        if scope == "project":
            return task.project or "(none)"
        if scope == "priority":
            return task.priority or "(none)"
        due = coerce_datetime(task.due)
        if due is None:
            return "(unscheduled)"
        if scope == "day":
            return due.date().isoformat()
        if scope == "week":
            year, week, _ = due.isocalendar()
            return f"{year}-W{week:02d}"
        raise ValueError(f"Unsupported roadmap scope '{scope}'.")

    def today_window_filters(self) -> dict[str, datetime]:
        """Return a half-open [start, end) window for today's due dates."""
        now = datetime.now().astimezone()
        start = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
        end = start + timedelta(days=1)
        return {"due_after": start - timedelta(microseconds=1), "due_before": end}

    def week_window_filters(self) -> dict[str, datetime]:
        """Return a half-open (now, now+7d) window for the upcoming week."""
        now = datetime.now().astimezone()
        end = now + timedelta(days=7)
        return {"due_after": now, "due_before": end}
