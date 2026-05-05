"""
Project resource template: taskmajor://project/{project_name}/tasks
"""

from __future__ import annotations

import json

from fastmcp import FastMCP

from taskmajor.domains.tasks import TaskService


def register_project_templates(mcp: FastMCP, task_service: TaskService) -> None:
    """Register project resource templates."""

    @mcp.resource(
        "taskmajor://project/{project_name}/tasks",
        name="Project Tasks",
        description="Tasks filtered by project name",
        mime_type="application/json",
    )
    def get_project_tasks(project_name: str) -> str:
        try:
            payload = task_service.query_tasks(
                filters={"project": project_name},
                sort=["due", "priority", "description"],
                limit=None,
            )
            return json.dumps(payload, default=str)
        except Exception as e:
            return json.dumps({"project": project_name, "error": str(e)})
