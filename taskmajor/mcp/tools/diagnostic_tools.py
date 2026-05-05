"""
Diagnostic tools — let the agent report errors it encountered.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from taskmajor.domains.observability import AgentErrorLog


def register_diagnostic_tools(
    mcp: FastMCP,
    error_log: AgentErrorLog,
    whitelist: set[str] | None = None,
) -> None:
    """Register diagnostic tools.

    Args:
        whitelist: If provided, only tools whose names appear in this set are registered.
                   Pass None to register all tools (used in tests).
    """

    def _allowed(name: str) -> bool:
        return whitelist is None or name in whitelist

    if _allowed("report_error"):

        @mcp.tool
        def report_error(tool_name: str, parameters: dict[str, Any], error: str) -> str:
            """
            Report an error encountered while using a tool.

            Call this whenever a tool returns an unexpected error or behaves
            incorrectly, so the issue can be investigated.

            Args:
                tool_name:  Name of the tool that failed (e.g. "add_task").
                parameters: The exact arguments that were passed to the tool.
                error:      The error message or unexpected response received.

            Returns:
                Confirmation that the error has been logged.
            """
            entry = error_log.append(tool_name, parameters, error)
            return f"Error logged at {entry['timestamp']}."

