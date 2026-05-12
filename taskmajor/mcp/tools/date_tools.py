"""
Date-related MCP tools: resolve and validate TaskWarrior date expressions.
"""

from __future__ import annotations

from fastmcp import FastMCP
from taskwarrior import TaskWarrior

# Expressions that are valid but task_calc returns a normalized duration
# rather than an absolute ISO datetime.
_ISO_DURATION_PREFIX = ("P", "PT")

# Known broken minute-stacking patterns
_BROKEN_MINUTE_PATTERN = (
    "+h",  # catches today+9h30m style
)


def _is_iso_duration(expr: str) -> bool:
    return any(expr.lstrip().upper().startswith(p) for p in _ISO_DURATION_PREFIX)


def _has_broken_minutes(expr: str) -> bool:
    """Detect today+9h30m style which is broken in TaskWarrior."""
    import re

    return bool(re.search(r"\+\d+h\d+m", expr))


def register_date_tools(
    mcp: FastMCP,
    taskwarrior_client: TaskWarrior,
    whitelist: set[str] | None = None,
) -> None:
    """Register date utility tools.

    Args:
        whitelist: If provided, only tools whose names appear in this set are registered.
                   Pass None to register all tools (used in tests).
    """

    def _allowed(name: str) -> bool:
        return whitelist is None or name in whitelist

    if _allowed("resolve_date"):

        @mcp.tool
        def resolve_date(expression: str) -> dict:
            """
            Resolve a TaskWarrior date expression to an ISO datetime string.

            Use this to preview what a date expression means before passing it
            to add_task or update_task. Examples: 'eom', 'friday', 'today+17h',
            'now+3d', 'P2W'.

            Args:
                expression: Any TaskWarrior date expression or synonym.

            Returns:
                dict with 'resolved' (ISO string), 'date', 'time', and optional 'warning'.
            """
            warning = None

            if _has_broken_minutes(expression):
                warning = (
                    f"'{expression}' uses broken minute syntax (+Xh YYm). "
                    "Use total minutes instead: e.g. 'today+570min' or 'today+9.5h'."
                )

            if _is_iso_duration(expression):
                warning = (
                    f"'{expression}' is an ISO duration — task_calc normalizes it "
                    "but does not resolve it to an absolute date. "
                    "It is valid as a due/scheduled/wait field value."
                )
                normalized = taskwarrior_client.task_calc(expression)
                return {"expression": expression, "resolved": normalized, "warning": warning}

            try:
                resolved = taskwarrior_client.task_calc(expression)
            except Exception as e:
                return {"expression": expression, "error": str(e)}

            date_part, _, time_part = resolved.partition("T")
            result: dict = {
                "expression": expression,
                "resolved": resolved,
                "date": date_part,
                "time": time_part or None,
            }
            if warning:
                result["warning"] = warning
            return result

    if _allowed("validate_date"):

        @mcp.tool
        def validate_date(expression: str) -> dict:
            """
            Check whether a string is a valid TaskWarrior date expression.

            Always validate user-supplied dates before passing them to add_task
            or update_task to avoid silent failures.

            Args:
                expression: The date string to validate.

            Returns:
                dict with 'valid' (bool), 'expression', and optional 'warning'.
            """
            warning = None

            if _has_broken_minutes(expression):
                warning = (
                    f"'{expression}' matches the broken '+Xh YYm' pattern. "
                    "TaskWarrior may accept it but produce wrong results. "
                    "Use 'today+570min' or 'today+9.5h' for 9h30."
                )

            valid = taskwarrior_client.date_validator(expression)
            result: dict = {"expression": expression, "valid": valid}
            if warning:
                result["warning"] = warning
            return result
