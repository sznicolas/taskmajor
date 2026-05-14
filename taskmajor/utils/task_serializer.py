"""TaskWarrior call serializer.

TaskWarrior 3.x (TaskChampion backend) has known concurrency issues when
multiple processes access the same ``taskchampion.sqlite3`` simultaneously
(GitHub issues #3676, #3325, #3329). Even with WAL mode enabled, concurrent
``task`` subprocesses corrupt the database.

This module provides a ``threading.Lock``-based serializer that ensures only
one ``task`` subprocess runs at a time. It works by monkey-patching the
``run_task_command`` method on a ``TaskWarriorAdapter`` instance — the single
choke-point through which all subprocess calls flow in pytaskwarrior.

Note on async vs threads:
    FastMCP (≥3.x) runs synchronous tool handlers via
    ``call_sync_fn_in_threadpool``. Thread workers cannot ``await`` asyncio
    primitives, so ``threading.Lock`` is the correct primitive here, not
    ``asyncio.Lock``.

Usage::

    from taskmajor.utils.task_serializer import install_serializer

    taskwarrior_client = TaskWarrior(...)
    install_serializer(taskwarrior_client)   # one call in bootstrap
"""

from __future__ import annotations

import functools
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Sentinel attribute set on the adapter after patching to prevent double-wrapping.
_SENTINEL = "_taskmajor_serializer_installed"


@dataclass
class SerializerMetrics:
    """Counters and timings accumulated by the serializer."""

    calls_total: int = 0
    errors_total: int = 0
    wait_seconds_total: float = 0.0
    run_seconds_total: float = 0.0
    # Separate lock so metrics updates don't contend with the command lock.
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record(self, wait: float, run: float, *, error: bool = False) -> None:
        with self._lock:
            self.calls_total += 1
            self.wait_seconds_total += wait
            self.run_seconds_total += run
            if error:
                self.errors_total += 1

    def snapshot(self) -> dict[str, Any]:
        """Return a point-in-time copy of the metrics."""
        with self._lock:
            avg_wait = (
                round(self.wait_seconds_total / self.calls_total, 3)
                if self.calls_total
                else 0.0
            )
            return {
                "calls_total": self.calls_total,
                "errors_total": self.errors_total,
                "wait_seconds_total": round(self.wait_seconds_total, 3),
                "run_seconds_total": round(self.run_seconds_total, 3),
                "avg_wait_seconds": avg_wait,
            }


class TaskCommandSerializer:
    """Serializes all ``task`` subprocess calls to prevent concurrent SQLite access.

    Wraps ``TaskWarriorAdapter.run_task_command`` on a given client with a
    ``threading.Lock`` so that at most one subprocess runs at a time regardless
    of how many agent threads are active.

    Example::

        serializer = TaskCommandSerializer()
        serializer.install(taskwarrior_client)
        # All subsequent calls to taskwarrior_client go through the lock.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.metrics = SerializerMetrics()

    def install(self, taskwarrior_client: Any) -> None:
        """Wrap ``taskwarrior_client.adapter.run_task_command`` with serialization.

        This is **idempotent**: calling ``install()`` more than once on the same
        client is a no-op after the first call, preventing double-wrapping and
        potential deadlocks.

        Args:
            taskwarrior_client: A ``TaskWarrior`` instance (pytaskwarrior).
        """
        adapter = taskwarrior_client.adapter
        if getattr(adapter, _SENTINEL, False):
            logger.debug("[TaskSerializer] Already installed on adapter, skipping.")
            return

        original = adapter.run_task_command
        serializer = self

        @functools.wraps(original)
        def _serialized(*args: Any, **kwargs: Any) -> Any:
            cmd_repr = " ".join(str(a) for a in (args[0] if args else []))
            logger.debug("[TaskSerializer] Queued: task %s", cmd_repr)

            wait_start = time.monotonic()
            with serializer._lock:
                wait_time = time.monotonic() - wait_start
                if wait_time > 0.5:
                    logger.warning(
                        "[TaskSerializer] Lock waited %.2fs for: task %s",
                        wait_time,
                        cmd_repr,
                    )

                run_start = time.monotonic()
                error = False
                try:
                    return original(*args, **kwargs)
                except Exception:
                    error = True
                    raise
                finally:
                    run_time = time.monotonic() - run_start
                    serializer.metrics.record(wait_time, run_time, error=error)
                    logger.debug(
                        "[TaskSerializer] Done (wait=%.3fs run=%.3fs error=%s): task %s",
                        wait_time,
                        run_time,
                        error,
                        cmd_repr,
                    )

        adapter.run_task_command = _serialized
        setattr(adapter, _SENTINEL, True)
        logger.info("[TaskSerializer] Installed on %r", adapter)


# Module-level singleton — used by install_serializer() and shareable across tests.
task_serializer = TaskCommandSerializer()


def install_serializer(taskwarrior_client: Any) -> None:
    """Install the module-level serializer on a ``TaskWarrior`` client.

    Convenience wrapper around ``task_serializer.install()``. Call this once
    in ``create_mcp()`` right after constructing the ``TaskWarrior`` client.

    Args:
        taskwarrior_client: A ``TaskWarrior`` instance (pytaskwarrior).
    """
    task_serializer.install(taskwarrior_client)
