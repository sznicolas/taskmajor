"""
Debug/Diagnostic MCP resources (error log).
"""

from __future__ import annotations

import json

from fastmcp import FastMCP

from taskmajor.domains.observability import AgentErrorLog


def register_debug_resources(mcp: FastMCP, error_log: AgentErrorLog) -> None:
    """Register debug-related resources."""

    @mcp.resource(
        "taskmajor://debug/errors",
        name="Agent Error Log",
        description="Errors reported by the agent, newest first",
        mime_type="application/json",
    )
    def get_debug_errors() -> str:
        return json.dumps({"errors": error_log.read_all()}, default=str)
