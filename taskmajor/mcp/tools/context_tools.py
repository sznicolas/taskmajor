"""
Context management MCP tools (runtime).
"""

from __future__ import annotations

from fastmcp import FastMCP

from taskmajor.domains.tasks import TaskService


def register_context_tools(
    mcp: FastMCP,
    task_service: TaskService,
    whitelist: set[str] | None = None,
) -> None:
    """Register context management tools.

    Args:
        whitelist: If provided, only tools whose names appear in this set are registered.
                   Pass None to register all tools (used in tests).
    """

    def _allowed(name: str) -> bool:
        return whitelist is None or name in whitelist

    if _allowed("list_contexts"):

        @mcp.tool
        def list_contexts() -> dict:
            """
            List all defined TaskWarrior contexts and indicate which is active.

            Returns:
                dict with 'active' (str|None) and 'contexts' (list of {name, read_filter, write_filter, active}).
            """
            try:
                contexts = task_service.list_contexts()
                current = task_service.get_current_context()
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
            except Exception as e:
                return {"error": str(e)}

    if _allowed("set_context"):

        @mcp.tool
        def set_context(name: str) -> str:
            """
            Activate a TaskWarrior context. All subsequent task queries will be
            filtered by this context.

            Args:
                name: Name of the context to activate.
            """
            try:
                task_service.set_context(name)
                return f"Context '{name}' activated."
            except Exception as e:
                return f"Failed to set context '{name}': {e}"

    if _allowed("unset_context"):

        @mcp.tool
        def unset_context() -> str:
            """
            Deactivate the current TaskWarrior context. Queries will no longer
            be filtered.
            """
            try:
                task_service.unset_context()
                return "Context deactivated."
            except Exception as e:
                return f"Failed to unset context: {e}"

