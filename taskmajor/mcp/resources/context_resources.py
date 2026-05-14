"""
Context-related MCP resource.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP
from taskwarrior import TaskWarrior

from taskmajor.mcp.resources._utils import resource_response


def register_context_resources(mcp: FastMCP, taskwarrior_client: TaskWarrior) -> None:
    """Register context resource."""

    @mcp.resource(
        "taskmajor://context/current",
        name="TaskWarrior Context",
        description="Current active context and list of all defined contexts",
        mime_type="application/json",
    )
    def get_context_current() -> str:
        def _payload() -> dict[str, Any]:
            contexts = taskwarrior_client.get_contexts()
            current = taskwarrior_client.get_current_context()
            return {
                "active": current,
                "contexts": [
                    {
                        "name": c.name,
                        "read_filter": c.read_filter,
                        "write_filter": c.write_filter,
                        "active": c.active,
                    }
                    for c in contexts
                ],
            }

        return resource_response(_payload)
