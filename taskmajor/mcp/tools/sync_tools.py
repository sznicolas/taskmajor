"""Sync MCP tools — force_sync and sync_status.

Registered only when a SyncEngine is active (i.e., when a sync backend is configured).
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from taskmajor.domains.sync.sync_engine import SyncEngine
from taskmajor.mcp.errors import INTERNAL_ERROR, fail, ok


def register_sync_tools(
    mcp: FastMCP,
    sync_engine: SyncEngine,
    whitelist: set[str] | None = None,
) -> None:
    """Register sync-related MCP tools.

    Args:
        mcp:         FastMCP instance to register tools on.
        sync_engine: Running SyncEngine instance (must not be None).
        whitelist:   If provided, only tools whose names are in this set are
                     registered. Pass None to register all (used in tests).
    """

    def _allowed(name: str) -> bool:
        return whitelist is None or name in whitelist

    if _allowed("force_sync"):

        @mcp.tool
        def force_sync() -> dict[str, Any]:
            """Force an immediate TaskWarrior synchronization.

            Useful when you want to push local changes to the sync server or
            pull remote changes without waiting for the next scheduled sync.

            Returns:
                Confirmation message with status.
            """
            try:
                sync_engine.force_sync()
                return ok("Sync completed successfully.")
            except Exception as exc:
                return fail(str(exc), INTERNAL_ERROR)

    if _allowed("sync_status"):

        @mcp.tool
        def sync_status() -> dict[str, Any]:
            """Return the current synchronization health status.

            Returns:
                Dict with: mode, running, interval_seconds, last_sync (ISO 8601
                or null), consecutive_failures, last_error, sync_configured.
            """
            return sync_engine.health
