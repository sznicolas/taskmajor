"""Pure helper functions for task data manipulation (no service state required)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, time


def coerce_datetime(value: str | date | datetime | None) -> datetime | None:
    """Coerce a date, datetime, or ISO string to a timezone-aware datetime.

    If the string cannot be parsed as ISO format, it's assumed to be a
    TaskWarrior date expression and should be passed as-is to TaskWarrior.
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=UTC)

    # Try to parse as ISO format
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        # Not an ISO format - assume it's a TaskWarrior expression
        # Return None to signal: "pass this string directly to TaskWarrior"
        return None


def serialize_datetime(value: date | datetime | None) -> str | None:
    """Serialize a date or datetime to an ISO 8601 string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return datetime.combine(value, time.min, tzinfo=UTC).isoformat()


def normalize_project_name(project: str | None) -> str | None:
    """Return a case-folded, stripped project name for comparison, or None."""
    if project is None:
        return None
    normalized = project.strip()
    return normalized.casefold() if normalized else None


def format_tag(tag: str) -> str:
    """Ensure a tag has a leading '+' prefix."""
    return tag if tag.startswith("+") else f"+{tag}"


def normalize_sort_specs(sort: Sequence[str] | str | None) -> list[str]:
    """Normalize sort input into a list of sort spec strings."""
    if sort is None:
        return ["due", "priority", "description"]
    if isinstance(sort, str):
        return [sort]
    return list(sort)


def is_taskwarrior_date_expr(value: str | None) -> bool:
    """Return True if value looks like a TaskWarrior date expression (not ISO)."""
    if value is None:
        return False
    # coerce_datetime returns None for non-ISO strings; treat non-empty non-ISO as TW expr
    return coerce_datetime(value) is None and bool(str(value).strip())
