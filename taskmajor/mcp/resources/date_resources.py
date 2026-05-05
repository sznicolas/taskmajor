"""
Date-related MCP resources.
"""

from __future__ import annotations

import json
from datetime import datetime

from fastmcp import FastMCP
from taskwarrior import TaskWarrior

from taskmajor.domains.taskwarrior import TaskConfigService


def register_date_resources(
    mcp: FastMCP,
    taskwarrior_client: TaskWarrior,
    task_config: TaskConfigService,
) -> None:
    """Register date-related MCP resources."""

    @mcp.resource(
        "taskmajor://now",
        name="Current Date & Time",
        description="Current datetime with timezone and common date shortcuts",
        mime_type="application/json",
    )
    def get_now() -> str:
        """Return current datetime with timezone and common shortcuts."""
        tz_name = task_config.get_timezone()
        now = datetime.now()

        shortcuts: dict[str, str | None] = {}
        for name, expr in [("eod", "eod"), ("eow", "eow"), ("eom", "eom")]:
            try:
                shortcuts[name] = taskwarrior_client.task_calc(expr)
            except Exception:
                shortcuts[name] = None

        return json.dumps({
            "now": now.strftime("%Y-%m-%dT%H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "weekday": now.strftime("%A"),
            "timezone": tz_name,
            "shortcuts": shortcuts,
        })
