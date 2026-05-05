"""
Date resource template: taskmajor://date/{expression}
"""

from __future__ import annotations

from fastmcp import FastMCP
from taskwarrior import TaskWarrior


def register_date_templates(mcp: FastMCP, taskwarrior_client: TaskWarrior) -> None:
    """Register date resource templates."""

    @mcp.resource(
        "taskmajor://date/{expression}",
        name="Resolved Date",
        description="Resolve any TaskWarrior date expression to an ISO datetime string",
        mime_type="application/json",
    )
    def get_date(expression: str) -> str:
        """Resolve a TaskWarrior date expression and return ISO datetime."""
        import json
        try:
            resolved = taskwarrior_client.task_calc(expression)
            date_part, _, time_part = resolved.partition("T")
            return json.dumps({
                "expression": expression,
                "resolved": resolved,
                "date": date_part,
                "time": time_part or None,
            })
        except Exception as e:
            return json.dumps({"expression": expression, "error": str(e)})
