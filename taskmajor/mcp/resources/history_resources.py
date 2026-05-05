"""
History MCP resources (undo stack).
"""

from __future__ import annotations

import json

from fastmcp import FastMCP

from taskmajor.domains.tasks import TaskService


def register_history_resources(mcp: FastMCP, task_service: TaskService) -> None:
    """Register history-related resources. This is optional and only active if an UndoStack is attached to TaskService."""

    undo_stack = getattr(task_service, "undo_stack", None)
    if undo_stack is None:
        # Nothing to register if undo stack isn't configured
        return

    @mcp.resource(
        "taskmajor://history/undo",
        name="Undo Stack",
        description="Recent reversible actions (done/deleted tasks)",
        mime_type="application/json",
    )
    def get_history_undo() -> str:
        entries = undo_stack.get_recent()
        return json.dumps(entries, default=str)
