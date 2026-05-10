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

            Examples:
                ```json
                {
                  "filters": {"status": "pending", "project": "Work"},
                  "sort": ["-urgency", "due"],
                  "limit": 10
                }
                ```
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

            Examples:
                ```json
                {
                  "filters": {"status": "pending", "project": "Work"}
                }
                ```
            """
            return task_service.get_stats(filters=filters)

    if _allowed("next_task"):

        @mcp.tool
        def next_task(filters: TaskQueryFilters | None = None) -> dict[str, Any]:
            """
            Return the next recommended actionable task.

            Args:
                filters: Optional filters to narrow the selection.

            Examples:
                ```json
                {
                  "filters": {"status": "pending"}
                }
                ```
            """
            return task_service.next_task(filters=filters)

    if _allowed("get_task"):

        @mcp.tool
        def get_task(task_id: str) -> dict[str, Any]:
            """
            Get a single task with full details (depends, annotations, UDAs).

            Args:
                task_id: The ID or UUID of the task to retrieve

            Examples:
                ```json
                {
                  "task_id": "12345678-1234-1234-1234-123456789abc"
                }
                ```
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

            Examples:
                ```json
                {
                  "task_id": "12345678-1234-1234-1234-123456789abc"
                }
                ```
            """
            if task_service.complete_task(task_id):
                return f"Task {task_id} marked as completed successfully."
            return f"Failed to complete task {task_id}. Task may not exist."

    if _allowed("add_task"):

        @mcp.tool
        def add_task(task_input: TaskInputDTO) -> dict[str, Any]:
            """
            Add a new task to TaskWarrior.

            IMPORTANT: All task fields must be nested inside the `task_input` object.
            Do NOT send fields like `priority`, `project`, `due` as top-level parameters.

            Args:
                task_input: The task input data containing all task fields.
                    Supported fields:
                    - description (required): Task description text
                    - project: Project name (e.g., "Work", "Home", "santé")
                    - priority: Priority level ("H", "M", "L")
                    - due: Due date (ISO format like "2026-05-15" or TaskWarrior expressions like "today", "tomorrow", "eod", "now+1d")
                    - tags: List of tags (e.g., ["+work", "+urgent"])
                    - depends: List of task UUIDs this task depends on
                    - annotations: List of annotation objects
                    - recur: Recurrence period for recurring tasks (string). Examples: 'daily', '2weeks', 'every 3 days'
                    - udas: Custom UDA fields

            Examples:
                ```json
                {
                  "task_input": {
                    "description": "Appeler le médecin",
                    "project": "santé",
                    "priority": "H",
                    "due": "2026-05-15"
                  }
                }
                ```

                ```json
                {
                  "task_input": {
                    "description": "Chercher le numéro du docteur Madri",
                    "project": "santé",
                    "priority": "M",
                    "tags": ["+call", "+urgent"],
                    "due": "today"
                  }
                }
                ```

                ```json
                {
                  "task_input": {
                    "description": "Review API documentation",
                    "project": "Work.ProjectA",
                    "priority": "M",
                    "due": "tomorrow",
                    "tags": ["+computer", "+review"]
                  }
                }
                ```

            Notes:
                - Use `project: "Inbox"` for quick capture without organization
                - Date expressions like "today", "now+1d", "eod" are supported
                - Recurrence expressions examples: 'daily', '2weeks', 'every 3 days'
                - Tags should include the '+' prefix (e.g., "+work", not "work")
            """
            created_task = task_service.add_task(task_input)
            return task_service.serialize_task(created_task)

    if _allowed("update_task"):

        @mcp.tool
        def update_task(task_id: str, task_input: TaskInputDTO) -> dict[str, Any]:
            """
            Update an existing task in TaskWarrior.

            IMPORTANT: All task fields must be nested inside the `task_input` object.
            Do NOT send fields like `priority`, `project`, `due` as top-level parameters.

            Args:
                task_id: The ID or UUID of the task to update
                task_input: The updated task data. At least one field must be modified.
                    Supported fields:
                    - description: Task description text
                    - project: Project name
                    - priority: Priority level ("H", "M", "L")
                    - due: Due date (ISO format or TaskWarrior expressions)
                    - tags: List of tags
                    - depends: List of task UUIDs
                    - annotations: List of annotation objects
                    - recur: Recurrence period for recurring tasks (string). Examples: 'daily', '2weeks', 'every 3 days'
                    - udas: Custom UDA fields

            Examples:
                ```json
                {
                  "task_id": "12345678-1234-1234-1234-123456789abc",
                  "task_input": {
                    "priority": "H",
                    "due": "tomorrow"
                  }
                }
                ```

                ```json
                {
                  "task_id": "12345678-1234-1234-1234-123456789abc",
                  "task_input": {
                    "project": "Work",
                    "tags": ["+urgent", "+call"]
                  }
                }
                ```

            Notes:
                - At least one field must be different from current task values
                - Recurrence expressions examples: 'daily', '2weeks', 'every 3 days'
                - Use this for both triage (assigning project/priority) and modifications
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

            Examples:
                ```json
                {
                  "task_id": "12345678-1234-1234-1234-123456789abc"
                }
                ```
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

            Examples:
                ```json
                {
                  "task_id": "12345678-1234-1234-1234-123456789abc"
                }
                ```
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

            Examples:
                ```json
                {
                  "task_id": "12345678-1234-1234-1234-123456789abc"
                }
                ```
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

            Examples:
                ```json
                {}
                ```

            Returns:
                List of project names and total count
            """
            return task_service.get_projects()

    if _allowed("get_tags"):

        @mcp.tool
        def get_tags() -> dict[str, Any]:
            """
            List all tags currently in use by pending tasks.

            Use this to discover existing tags before creating tasks.

            Examples:
                ```json
                {}
                ```

            Returns:
                List of tags (with '+' prefix) and total count
            """
            return task_service.get_tags()

    if _allowed("get_udas"):

        @mcp.tool
        def get_udas() -> dict[str, Any]:
            """
            List all UDAs defined in TaskWarrior configuration.

            Use this to discover available UDAs and their types before using them.

            Examples:
                ```json
                {}
                ```

            Returns:
                List of UDAs and total count
            """
            return task_service.get_udas()
