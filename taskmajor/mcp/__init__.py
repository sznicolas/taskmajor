"""
taskmajor.mcp - MCP component registry

Provides a central registry to register tools, resources, prompts, and
resource templates with a FastMCP instance.

Usage in server.py:
    from taskmajor.mcp import register_all
    register_all(mcp, task_service, error_log)
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from taskmajor.domains.observability import AgentErrorLog as AgentErrorLog
from taskmajor.domains.tasks import TaskService as TaskService


def register_all(
    mcp: FastMCP,
    task_service: Any,
    error_log: Any,
    tool_whitelist: set[str] | None = None,
) -> None:
    """Register all MCP components (tools, resources, prompts, templates)."""
    from taskmajor.mcp.resources import register_resources
    from taskmajor.mcp.templates import register_templates
    from taskmajor.mcp.tools import register_tools

    register_tools(mcp, task_service, error_log, tool_whitelist=tool_whitelist)
    register_resources(mcp, task_service, error_log)
    register_templates(mcp, task_service)


def register_resources(mcp: FastMCP, task_service: Any, error_log: Any) -> None:
    """Delegate to the package-level resources.register_resources implementation."""
    from taskmajor.mcp.resources import register_resources as _pkg_register_resources

    _pkg_register_resources(mcp, task_service, error_log)


def register_tools(
    mcp: FastMCP,
    task_service: Any,
    error_log: Any,
    tool_whitelist: set[str] | None = None,
) -> None:
    """Delegate to the package-level tools.register_tools implementation."""
    from taskmajor.mcp.tools import register_tools as _pkg_register_tools

    _pkg_register_tools(mcp, task_service, error_log, tool_whitelist=tool_whitelist)




def register_templates(mcp: FastMCP, task_service: Any) -> None:
    """Delegate to package-level templates.register_templates."""
    from taskmajor.mcp.templates import register_templates as _pkg_register_templates

    _pkg_register_templates(mcp, task_service)
