"""SyncEngine — periodic or manual TaskWarrior synchronization.

Runs independently of TaskWarriorProxy: the engine holds a reference to the
proxy and calls ``synchronize()`` through the normal queue, so thread-safety
is handled automatically.

Modes
-----
- ``periodic``: schedules a recurring ``threading.Timer`` every
  ``interval_seconds`` seconds, starting after the first interval (not
  immediately, to avoid a sync burst at startup).
- ``manual``: no automatic timer; callers use ``force_sync()`` explicitly.

On exit, ``stop()`` can optionally perform a final sync (``on_exit=True``).
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from taskmajor.utils.taskwarrior_proxy import TaskWarriorProxy

logger = logging.getLogger(__name__)


@dataclass
class SyncHealth:
    last_sync: datetime | None = None
    last_error: Exception | None = None
    consecutive_failures: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record_success(self) -> None:
        with self._lock:
            self.last_sync = datetime.now()
            self.consecutive_failures = 0
            self.last_error = None

    def record_failure(self, exc: Exception) -> None:
        with self._lock:
            self.last_error = exc
            self.consecutive_failures += 1


class SyncEngine:
    """Orchestrates TaskWarrior synchronization.

    Args:
        tw_proxy: Thread-safe proxy to the TaskWarrior instance.
        config:   Dict from ``SyncConfig.model_dump()``
                  (keys: mode, interval_seconds, on_exit, enabled).
    """

    def __init__(self, tw_proxy: TaskWarriorProxy, config: Any) -> None:
        """Initialize SyncEngine.

        Accepts either a mapping (dict) as before or a SyncConfig model instance.
        """
        self._tw = tw_proxy
        self._raw_config = config
        # Detect whether config is a SyncConfig model with `is_configured` property
        self._config_is_model = hasattr(config, "is_configured")

        if self._config_is_model:
            cfg = config
            self._mode = getattr(cfg, "mode", "manual")
            self._interval = int(getattr(cfg, "interval_seconds", 300))
            self._on_exit = bool(getattr(cfg, "on_exit", True))
        else:
            # legacy dict-like config
            self._mode = config.get("mode", "manual")
            self._interval = int(config.get("interval_seconds", 300))
            self._on_exit = bool(config.get("on_exit", True))

        self._timer: threading.Timer | None = None
        self._running = False
        self._health = SyncHealth()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the engine. Schedules timer if mode is ``periodic``.

        If no backend is configured (local or remote) the engine will not start
        automatic syncs and logs that sync is disabled for clarity.
        """
        # Mark running early so stop() behaves sensibly if called
        self._running = True

        # Determine whether a backend is configured
        if self._config_is_model:
            configured = bool(getattr(self._raw_config, "is_configured", False))
        else:
            # Legacy dict config: consider local/remote keys or the legacy 'enabled' flag
            configured = bool(
                self._raw_config.get("local") or self._raw_config.get("remote") or self._raw_config.get("enabled")
            )

        if not configured:
            logger.info("[SyncEngine] Sync disabled: no local or remote backend configured.")
            return

        if self._mode == "periodic":
            self._schedule_next()
            logger.info(
                "[SyncEngine] Started in periodic mode (interval=%ds)", self._interval
            )
        else:
            logger.info("[SyncEngine] Started in manual mode")

    def stop(self) -> None:
        """Stop the timer and optionally run a final sync."""
        self._running = False
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        if self._on_exit:
            logger.info("[SyncEngine] Performing final sync on exit")
            self._do_sync()

    # ------------------------------------------------------------------
    # Sync execution
    # ------------------------------------------------------------------

    def force_sync(self) -> None:
        """Trigger an immediate sync (for the MCP tool)."""
        self._do_sync()

    def _do_sync(self) -> None:
        """Execute sync and update health metrics.

        Skips silently if sync is not configured on the TaskWarrior side.
        """
        try:
            if not self._tw.is_sync_configured():
                logger.debug("[SyncEngine] Sync not configured, skipping")
                return
            self._tw.synchronize()
            self._health.record_success()
            logger.debug("[SyncEngine] Sync completed successfully")
        except Exception as exc:
            self._health.record_failure(exc)
            logger.error("[SyncEngine] Sync failed: %s", exc)

    def _schedule_next(self) -> None:
        """Schedule the next sync after ``interval_seconds``."""
        if not self._running:
            return
        self._timer = threading.Timer(self._interval, self._tick)
        self._timer.daemon = True
        self._timer.start()

    def _tick(self) -> None:
        """Timer callback: run sync then schedule the next tick."""
        if not self._running:
            return
        self._do_sync()
        if self._running:
            self._schedule_next()

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    @property
    def health(self) -> dict[str, Any]:
        """Point-in-time health snapshot."""
        with self._health._lock:
            return {
                "mode": self._mode,
                "running": self._running,
                "interval_seconds": self._interval if self._mode == "periodic" else None,
                "last_sync": (
                    self._health.last_sync.isoformat() if self._health.last_sync else None
                ),
                "consecutive_failures": self._health.consecutive_failures,
                "last_error": str(self._health.last_error) if self._health.last_error else None,
                "sync_configured": self._is_sync_configured(),
            }

    def _is_sync_configured(self) -> bool:
        try:
            return bool(self._tw.is_sync_configured())
        except Exception:
            return False
