"""Configuration tools."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP
from taskwarrior.dto.context_dto import ContextDTO
from taskwarrior.dto.uda_dto import UdaConfig

from taskmajor.domains.taskwarrior import TaskConfigService


def register_config_tools(
    mcp: FastMCP,
    task_config: TaskConfigService,
    whitelist: set[str] | None = None,
) -> None:
    """Register configuration tools.

    Args:
        whitelist: If provided, only tools whose names appear in this set are registered.
                   Pass None to register all tools (used in tests).
    """

    def _allowed(name: str) -> bool:
        return whitelist is None or name in whitelist

    if _allowed("get_config"):

        @mcp.tool
        def get_config() -> dict[str, Any]:
            """
            Return the current TaskWarrior configuration: timezone and UDAs.

            Use this to inspect the current setup before making changes.
            """
            return task_config.get_all_config()

    if _allowed("set_timezone"):

        @mcp.tool
        def set_timezone(timezone: str) -> str:
            """
            Set the timezone in the configuration.

            Args:
                timezone: IANA timezone name (e.g. 'Europe/Paris', 'America/New_York', 'UTC').

            Returns:
                Confirmation message.
            """
            try:
                task_config.set_timezone(timezone)
                return f"Timezone set to '{timezone}'."
            except Exception as e:
                return f"Failed to set timezone: {e}"

    if _allowed("add_uda"):

        @mcp.tool
        def add_uda(uda_config: UdaConfig) -> str:
            """
            Define or update a User Defined Attribute (UDA).

            Args:
                uda_config: A UdaConfig object specifying name, uda_type, label, and optional default/values.

            Returns:
                Confirmation or error message.
            """
            try:
                task_config.add_uda(uda_config)
                return f"UDA '{uda_config.name}' (type={uda_config.uda_type}) defined successfully."
            except Exception as e:
                return f"Failed to define UDA '{uda_config.name}': {e}"

    if _allowed("delete_uda"):

        @mcp.tool
        def delete_uda(name: str) -> str:
            """
            Delete a User Defined Attribute (UDA).

            ⚠ Warning: deleting a UDA will discard its value on all existing tasks.

            Args:
                name: The UDA key to delete.

            Returns:
                Confirmation or error message.
            """
            try:
                task_config.delete_uda(name)
                return f"UDA '{name}' deleted successfully."
            except Exception as e:
                return f"Failed to delete UDA '{name}': {e}"

    if _allowed("define_context"):

        @mcp.tool
        def define_context(context: ContextDTO) -> str:
            """
            Create or update a TaskWarrior context.

            A context is a named filter applied globally to all task queries.
            The filter is applied to both read and write operations.

            Args:
                context: A ContextDTO object specifying name, read_filter, and write_filter.

            Returns:
                Confirmation or error message.
            """
            try:
                task_config.define_context(context)
                return f"Context '{context.name}' defined successfully."
            except Exception as e:
                return f"Failed to define context '{context.name}': {e}"

    if _allowed("delete_context"):

        @mcp.tool
        def delete_context(name: str) -> str:
            """
            Delete a TaskWarrior context.

            Args:
                name: Name of the context to delete.

            Returns:
                Confirmation or error message.
            """
            try:
                task_config.delete_context(name)
                return f"Context '{name}' deleted."
            except Exception as e:
                return f"Failed to delete context '{name}': {e}"

