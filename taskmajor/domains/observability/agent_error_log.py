"""Agent error log that persists reported errors to a JSONL file."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path


class AgentErrorLog:
    """Append-only log of errors reported by MCP agents."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, tool_name: str, parameters: dict, error: str) -> dict:
        """Append one error entry and return it."""
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "tool_name": tool_name,
            "parameters": parameters,
            "error": error,
        }
        try:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except OSError as exc:
            logging.error(f"AgentErrorLog: could not write to {self._path}: {exc}")
        return entry

    def read_all(self) -> list[dict]:
        """Return all logged entries, newest first."""
        if not self._path.exists():
            return []
        entries: list[dict] = []
        try:
            with self._path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
        except OSError as exc:
            logging.error(f"AgentErrorLog: could not read {self._path}: {exc}")
        return list(reversed(entries))
