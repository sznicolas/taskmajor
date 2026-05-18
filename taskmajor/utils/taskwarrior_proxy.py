"""Thread-safe proxy for the TaskWarrior client.

pytaskwarrior with TaskChampionAdapter exposes a PyO3 ``Replica`` object that is
NOT thread-safe: it can only be used from the OS thread that created it.

FastMCP runs synchronous tool handlers via ``ThreadPoolExecutor``, so without
this proxy the ``Replica`` would be accessed from arbitrary threads, causing
crashes or data corruption.

This module solves the problem by **confining** the ``TaskWarrior`` instance to
a single dedicated worker thread and routing all calls through a ``queue.Queue``.

Usage::

    from taskmajor.utils.taskwarrior_proxy import TaskWarriorProxy
    from taskwarrior import TaskWarrior

    proxy = TaskWarriorProxy(factory=lambda: TaskWarrior(taskrc_file=...))
    proxy.add_task(...)   # blocks until the worker finishes, propagates exceptions
    proxy.config_store.set_value("key", "val")
    proxy.shutdown()      # clean stop
"""

from __future__ import annotations

import concurrent.futures
import logging
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Sentinel: a `None` placed on the queue requests the worker to exit.
_SHUTDOWN = None


@dataclass
class ProxyMetrics:
    """Counters and timings accumulated by the proxy."""

    calls_total: int = 0
    errors_total: int = 0
    wait_seconds_total: float = 0.0
    run_seconds_total: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record(self, wait: float, run: float, *, error: bool = False) -> None:
        with self._lock:
            self.calls_total += 1
            self.wait_seconds_total += wait
            self.run_seconds_total += run
            if error:
                self.errors_total += 1

    def snapshot(self) -> dict[str, Any]:
        """Return a point-in-time copy of the metrics as a plain dict."""
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


class _ConfigStoreProxy:
    """Proxy for TaskWarrior.config_store that routes all accesses through the worker.

    Exposes the same interface as the pytaskwarrior ConfigStore object, but
    all calls are executed on the TaskWarriorProxy worker thread so that any
    Replica access stays on the owning thread.
    """

    def __init__(self, tw_proxy: TaskWarriorProxy) -> None:
        self._tw_proxy = tw_proxy

    @property
    def config(self) -> dict[str, Any]:
        """Fetch the raw config dict from the worker thread."""
        return self._tw_proxy._call_chain(["config_store", "config"], is_call=False)

    def set_value(self, key: str, value: str) -> None:
        self._tw_proxy._call_chain(["config_store", "set_value"], True, key, value)

    def delete_value(self, key: str) -> None:
        self._tw_proxy._call_chain(["config_store", "delete_value"], True, key)

    def get_contexts(self) -> Any:
        return self._tw_proxy._call_chain(["config_store", "get_contexts"], True)

    def get_sync_config(self) -> Any:
        return self._tw_proxy._call_chain(["config_store", "get_sync_config"], True)


class TaskWarriorProxy:
    """Thread-safe proxy that confines a TaskWarrior instance to a worker thread.

    All calls to TaskWarrior methods are serialized through a ``queue.Queue``
    and executed on the single worker thread that owns the ``TaskWarrior``
    instance (and its underlying ``Replica``).

    The ``factory`` callable is invoked **inside the worker thread** so that the
    ``Replica`` object is created there — satisfying the PyO3 thread-affinity
    requirement.

    Example::

        proxy = TaskWarriorProxy(factory=lambda: TaskWarrior(taskrc_file=...))
        tasks = proxy.get_tasks()           # blocks, propagates exceptions
        proxy.config_store.set_value(...)   # config_store also routed through worker
        proxy.shutdown()
    """

    def __init__(self, factory: Callable[[], Any]) -> None:
        self._factory = factory
        self._queue: queue.Queue[Any] = queue.Queue()
        self._ready = threading.Event()
        self._init_error: BaseException | None = None
        self._dead: bool = False
        self._dead_lock = threading.Lock()
        self.metrics = ProxyMetrics()
        self.config_store = _ConfigStoreProxy(self)

        self._worker_thread = threading.Thread(
            target=self._worker_loop, daemon=True, name="taskwarrior-proxy-worker"
        )
        self._worker_thread.start()
        if not self._ready.wait(timeout=10.0):
            raise RuntimeError("TaskWarriorProxy: worker did not become ready within 10 seconds")
        if self._init_error is not None:
            raise self._init_error

    # ------------------------------------------------------------------
    # Internal dispatch helpers
    # ------------------------------------------------------------------

    def _enqueue(
        self,
        attr_chain: list[str],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        is_call: bool,
    ) -> Any:
        """Put a work item on the queue and block until the worker completes it."""
        with self._dead_lock:
            if self._dead:
                raise RuntimeError("TaskWarriorProxy: worker is no longer running")

        fut: concurrent.futures.Future[Any] = concurrent.futures.Future()
        enqueue_time = time.monotonic()
        self._queue.put((attr_chain, args, kwargs, is_call, enqueue_time, fut))
        return fut.result()  # blocks until worker sets result or exception

    def _call_chain(
        self,
        attr_chain: list[str],
        /,
        is_call: bool = True,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Dispatch a potentially chained attribute access or call to the worker."""
        # Re-entrancy guard: if we're already on the worker thread, call directly.
        if threading.current_thread() is self._worker_thread:
            obj: Any = self._tw  # type: ignore[attr-defined]
            for attr in attr_chain:
                obj = getattr(obj, attr)
            return obj(*args, **kwargs) if is_call else obj
        return self._enqueue(attr_chain, args, kwargs, is_call)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def __getattr__(self, name: str) -> Any:
        """Return a proxy callable for any TaskWarrior method not explicitly defined.

        This intercepts attribute lookups that are not already on the proxy
        (e.g. ``get_tasks``, ``add_task``, ``get_info``, etc.) and returns a
        function that routes the call through the worker queue.
        """
        # Guard against infinite recursion during __init__ before _worker_thread
        # is set, and for private/dunder names.
        if name.startswith("_"):
            raise AttributeError(name)

        def _proxied(*args: Any, **kwargs: Any) -> Any:
            return self._call_chain([name], True, *args, **kwargs)

        return _proxied

    def shutdown(self, timeout: float = 5.0) -> None:
        """Stop the worker thread gracefully.

        Idempotent: safe to call multiple times. Logs a warning if the worker
        does not exit within ``timeout`` seconds.
        """
        with self._dead_lock:
            if self._dead:
                return

        self._queue.put(_SHUTDOWN)
        self._worker_thread.join(timeout=timeout)
        if self._worker_thread.is_alive():
            logger.warning(
                "[TaskWarriorProxy] Worker did not exit within %.1fs after shutdown request",
                timeout,
            )
        else:
            logger.debug("[TaskWarriorProxy] Worker exited cleanly")

    def get_metrics(self) -> dict[str, Any]:
        """Return a point-in-time snapshot of proxy metrics."""
        return self.metrics.snapshot()

    # ------------------------------------------------------------------
    # Worker thread
    # ------------------------------------------------------------------

    def _worker_loop(self) -> None:
        """Worker loop: creates TaskWarrior and processes the queue indefinitely."""
        try:
            self._tw = self._factory()
        except Exception as exc:
            logger.exception("[TaskWarriorProxy] Factory failed: %s", exc)
            self._init_error = exc
            self._ready.set()
            return

        logger.debug("[TaskWarriorProxy] Worker ready, TaskWarrior instance created")
        self._ready.set()

        while True:
            # Use a short timeout so the loop can check for shutdown events.
            try:
                item = self._queue.get(timeout=0.05)
            except queue.Empty:
                continue

            if item is _SHUTDOWN:
                self._queue.task_done()
                break

            attr_chain, args, kwargs, is_call, enqueue_time, fut = item
            dequeue_time = time.monotonic()
            wait_time = dequeue_time - enqueue_time
            if wait_time > 0.5:
                logger.warning(
                    "[TaskWarriorProxy] High queue wait %.2fs for %s",
                    wait_time,
                    ".".join(attr_chain),
                )

            error = False
            run_start = time.monotonic()
            try:
                obj: Any = self._tw
                for attr in attr_chain:
                    obj = getattr(obj, attr)
                result = obj(*args, **kwargs) if is_call else obj
                fut.set_result(result)
            except Exception as exc:
                error = True
                fut.set_exception(exc)
            finally:
                run_time = time.monotonic() - run_start
                self.metrics.record(wait_time, run_time, error=error)
                self._queue.task_done()
                logger.debug(
                    "[TaskWarriorProxy] %s (wait=%.3fs run=%.3fs error=%s)",
                    ".".join(attr_chain),
                    wait_time,
                    run_time,
                    error,
                )

        # Worker is exiting — mark dead and drain any remaining queued futures.
        with self._dead_lock:
            self._dead = True
        self._drain_queue()
        logger.debug("[TaskWarriorProxy] Worker thread exited")

    def _drain_queue(self) -> None:
        """Reject all items remaining in the queue after the worker exits."""
        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break
            if item is _SHUTDOWN:
                self._queue.task_done()
                continue
            _, _, _, _, _, fut = item
            if not fut.done():
                fut.set_exception(RuntimeError("TaskWarriorProxy: worker exited before processing"))
            self._queue.task_done()
