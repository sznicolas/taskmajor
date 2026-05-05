"""
Server-side undo stack for task actions.

Tracks recent done/delete operations with sequential numbers so the agent
can call undo_recent([1, 2]) without needing to remember UUIDs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_MAX_STACK_SIZE = 20

@dataclass
class UndoEntry:
    n: int
    uuid: str
    description: str
    action: str  # "done" | "deleted"

class UndoStack:
    """In-memory stack of recent reversible task actions."""

    def __init__(self, max_size: int = _MAX_STACK_SIZE) -> None:
        self._entries: list[UndoEntry] = []
        self._counter: int = 0
        self._max_size = max_size

    def push(self, uuid: str, description: str, action: str) -> int:
        """Push an entry and return its sequential number."""
        self._counter += 1
        entry = UndoEntry(n=self._counter, uuid=uuid, description=description, action=action)
        self._entries.append(entry)
        if len(self._entries) > self._max_size:
            self._entries.pop(0)
        return self._counter

    def get_by_number(self, n: int) -> UndoEntry | None:
        return next((e for e in self._entries if e.n == n), None)

    def get_recent(self) -> list[dict[str, Any]]:
        return [
            {"n": e.n, "uuid": e.uuid, "description": e.description, "action": e.action}
            for e in reversed(self._entries)
        ]

    def clear(self) -> None:
        self._entries.clear()
