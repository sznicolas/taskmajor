"""
taskmajor.mcp.templates - MCP resource template components

Each module registers resource templates (dynamic URIs with parameters).
Example: taskmajor://project/{project_name}/tasks
"""

from __future__ import annotations

from fastmcp import FastMCP

from taskmajor.domains.tasks import TaskService


def register_templates(mcp: FastMCP, task_service: TaskService) -> None:
    """Register all MCP resource templates."""
    from taskmajor.mcp.templates.date_templates import register_date_templates
    from taskmajor.mcp.templates.project_templates import register_project_templates

    register_date_templates(mcp, task_service.taskwarrior_client)
    register_project_templates(mcp, task_service)
