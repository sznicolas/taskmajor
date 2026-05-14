"""
taskmajor.mcp.resources - Static MCP resource registrations

This module registers the 4 static resources that cannot be declaratively defined
in profile YAML because they require backends that are not TaskService methods:
- taskmajor://now (taskwarrior_client.task_calc + task_config.get_timezone)
- taskmajor://debug/errors (AgentErrorLog service)
- taskmajor://context/current (taskwarrior_client.get_contexts / get_current_context)
- taskmajor://history/undo (conditional undo_stack on TaskService)

All other resources (agenda, status, queue, roadmap, analytics, config) are
declared in profile manifests and registered dynamically by _apply_profile().
"""

from __future__ import annotations

from fastmcp import FastMCP

from taskmajor.domains.observability import AgentErrorLog
from taskmajor.domains.tasks import TaskService


def register_resources(mcp: FastMCP, task_service: TaskService, error_log: AgentErrorLog) -> None:
    """Register static MCP resources.

    Args:
        mcp: FastMCP instance
        task_service: TaskService for context
        error_log: AgentErrorLog for error resource
    """
    # Contexts (uses raw taskwarrior_client)
    from taskmajor.mcp.resources.context_resources import register_context_resources

    # Date resources (requires low-level taskwarrior client & config)
    from taskmajor.mcp.resources.date_resources import register_date_resources

    # Debug / Diagnostic (uses AgentErrorLog)
    from taskmajor.mcp.resources.debug_resources import register_debug_resources

    # History (undo) — optional (uses TaskService.undo_stack if available)
    from taskmajor.mcp.resources.history_resources import register_history_resources

    register_context_resources(mcp, task_service.taskwarrior_client)
    register_date_resources(mcp, task_service.taskwarrior_client, task_service.task_config)
    register_debug_resources(mcp, error_log)
    register_history_resources(mcp, task_service)
