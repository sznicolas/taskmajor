"""
Task-related MCP tools.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP
from taskwarrior import TaskInputDTO

from taskmajor.domains.tasks import TaskQueryFilters, TaskService


def register_task_tools(
    mcp: FastMCP,
    task_service: TaskService,
    whitelist: set[str] | None = None,
) -> None:
    """Register task management MCP tools.

    Args:
        whitelist: If provided, only tools whose names appear in this set are registered.
                   Pass None to register all tools (used in tests).
    """

    def _allowed(name: str) -> bool:
        return whitelist is None or name in whitelist

    if _allowed("query_tasks"):

        @mcp.tool
        def query_tasks(
            filters: TaskQueryFilters | None = None,
            sort: list[str] | None = None,
            limit: int = 50,
            offset: int = 0,
        ) -> dict[str, Any]:
            """
            Query tasks with the shared MCP business filters and canonical response shape.

            Args:
                filters: Supported filters such as project, projects, priority, status,
                    tags_any, tags_all, due_before, due_after, and text.
                sort: Sort fields such as due, priority, project, urgency.
                    Prefix a field with '-' for descending order.
                limit: Maximum number of tasks to return.
                offset: Number of matching tasks to skip before returning the page.
            """
            return task_service.query_tasks(filters=filters, sort=sort, limit=limit, offset=offset)

    if _allowed("get_stats"):

        @mcp.tool
        def get_stats(filters: TaskQueryFilters | None = None) -> dict[str, Any]:
            """
            Aggregate tasks by status, project, priority, and review queue membership.

            Args:
                filters: Optional filters applied before computing aggregates.
                    Returns counts by status, project, and priority plus overdue count.
            """
            return task_service.get_stats(filters=filters)

    if _allowed("next_task"):

        @mcp.tool
        def next_task(filters: TaskQueryFilters | None = None) -> dict[str, Any]:
            """
            Return the next recommended actionable task.

            Args:
                filters: Optional filters to narrow the selection.
            """
            return task_service.next_task(filters=filters)

    if _allowed("get_task"):

        @mcp.tool
        def get_task(task_id: str) -> dict[str, Any]:
            """
            Get a single task with full details (depends, annotations, UDAs).

            Args:
                task_id: The ID or UUID of the task to retrieve
            """
            try:
                task = task_service.taskwarrior_client.get_task(task_id)
            except Exception as e:
                return {"error": str(e)}
            if not task:
                return {"error": f"Task {task_id} not found"}

            serialized = task_service.serialize_task(task)

            entry = getattr(task, "entry", None)
            modified = getattr(task, "modified", None)
            if entry is not None and hasattr(entry, "isoformat"):
                serialized["entry"] = entry.isoformat()
            else:
                serialized["entry"] = None
            if modified is not None and hasattr(modified, "isoformat"):
                serialized["modified"] = modified.isoformat()
            else:
                serialized["modified"] = None

            return serialized

    if _allowed("done_task"):

        @mcp.tool
        def done_task(task_id: str) -> str:
            """
            Mark a task as completed.

            Args:
                task_id: The ID of the task to complete
            """
            if task_service.complete_task(task_id):
                return f"Task {task_id} marked as completed successfully."
            return f"Failed to complete task {task_id}. Task may not exist."

    if _allowed("add_task"):

        @mcp.tool
        def add_task(task_input: TaskInputDTO) -> dict[str, Any]:
            """
            Add a new task.

            Args:
                task_input: The task input data
            """
            created_task = task_service.add_task(task_input)
            return task_service.serialize_task(created_task)

    if _allowed("update_task"):

        @mcp.tool
        def update_task(task_id: str, task_input: TaskInputDTO) -> dict[str, Any]:
            """
            Update an existing task.

            Args:
                task_id: The ID of the task to update
                task_input: The updated task data
            """
            updated_task = task_service.update_task(task_id, task_input)
            return task_service.serialize_task(updated_task)

    if _allowed("delete_task"):

        @mcp.tool
        def delete_task(task_id: str) -> str:
            """
            Mark a task as deleted (soft delete).

            Args:
                task_id: The ID of the task to delete
            """
            if task_service.delete_task(task_id):
                return f"Task {task_id} marked as deleted successfully."
            return f"Failed to delete task {task_id}. Task may not exist."

    if _allowed("start_task"):

        @mcp.tool
        def start_task(task_id: str) -> str:
            """
            Start working on a task (sets start time).

            Args:
                task_id: The ID of the task to start
            """
            if task_service.start_task(task_id):
                return f"Task {task_id} started successfully."
            return f"Failed to start task {task_id}. Task may not exist."

    if _allowed("stop_task"):

        @mcp.tool
        def stop_task(task_id: str) -> str:
            """
            Stop working on a task (clears start time).

            Args:
                task_id: The ID of the task to stop
            """
            if task_service.stop_task(task_id):
                return f"Task {task_id} stopped successfully."
            return f"Failed to stop task {task_id}. Task may not exist."

    if _allowed("get_projects"):

        @mcp.tool
        def get_projects() -> dict[str, Any]:
            """
            List all projects currently in use by pending tasks.

            Use this to discover existing projects before creating tasks.
            """
            return task_service.get_projects()

    if _allowed("get_tags"):

        @mcp.tool
        def get_tags() -> dict[str, Any]:
            """
            List all tags currently in use by pending tasks.

            Use this to discover existing tags before creating tasks.
            """
            return task_service.get_tags()

    if _allowed("get_udas"):

        @mcp.tool
        def get_udas() -> dict[str, Any]:
            """
            List all UDAs defined in TaskWarrior configuration.

            Use this to discover available UDAs and their types before using them.
            """
            return task_service.get_udas()

