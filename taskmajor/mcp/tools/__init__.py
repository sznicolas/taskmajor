"""
taskmajor.mcp.tools - MCP tool components

Each module in this package registers a set of related tools.
To add new tools, create a new module and import its register_* function
in this __init__.py.
"""

from __future__ import annotations

from fastmcp import FastMCP

from taskmajor.domains.observability import AgentErrorLog
from taskmajor.domains.tasks import TaskService


def register_tools(
    mcp: FastMCP,
    task_service: TaskService,
    error_log: AgentErrorLog,
    tool_whitelist: set[str] | None = None,
) -> None:
    """Register MCP tools filtered by whitelist.

    Args:
        tool_whitelist: Set of tool names to register. If None, all tools are
                        registered (useful for tests). In production, the whitelist
                        is derived from the active profile chain.
    """
    from taskmajor.mcp.tools.config_tools import register_config_tools
    from taskmajor.mcp.tools.context_tools import register_context_tools
    from taskmajor.mcp.tools.date_tools import register_date_tools
    from taskmajor.mcp.tools.diagnostic_tools import register_diagnostic_tools
    from taskmajor.mcp.tools.task_tools import register_task_tools

    register_task_tools(mcp, task_service, whitelist=tool_whitelist)
    register_diagnostic_tools(mcp, error_log, whitelist=tool_whitelist)
    register_context_tools(mcp, task_service, whitelist=tool_whitelist)
    register_date_tools(mcp, task_service.taskwarrior_client, whitelist=tool_whitelist)
    register_config_tools(mcp, task_service.task_config, whitelist=tool_whitelist)
