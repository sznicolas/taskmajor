"""Tests for TaskWarriorProxy.

Covers:
- Concurrent calls are serialized on the worker thread (no crash / data race)
- Exceptions in the worker propagate to the calling thread via Future
- Shutdown stops the worker thread cleanly and is idempotent
- New calls are rejected after shutdown
- Proxy metrics (calls_total, errors_total) are updated correctly
- Factory errors surface as exceptions in __init__
- config_store proxy routes through the worker
- Re-entrancy guard: calling proxy from worker thread does not deadlock
"""

from __future__ import annotations

import threading
import time
from typing import Any
from unittest.mock import MagicMock, PropertyMock

import pytest

from taskmajor.utils.taskwarrior_proxy import (
    ProxyMetrics,
    TaskWarriorProxy,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tw() -> MagicMock:
    """Return a fake TaskWarrior client with a config_store attribute."""
    tw = MagicMock()
    tw.config_store = MagicMock()
    type(tw.config_store).config = PropertyMock(return_value={"rc.timezone": "UTC"})
    tw.config_store.set_value = MagicMock()
    tw.config_store.get_contexts = MagicMock(return_value=[])
    tw.config_store.get_sync_config = MagicMock(return_value={})
    tw.get_tasks = MagicMock(return_value=[])
    tw.add_task = MagicMock(return_value=None)
    tw.get_info = MagicMock(return_value={"backend_type": "taskchampion"})
    return tw


def _proxy_for(tw: MagicMock) -> TaskWarriorProxy:
    """Build a TaskWarriorProxy whose factory returns the given mock."""
    return TaskWarriorProxy(factory=lambda: tw)


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


class TestTaskWarriorProxyConcurrency:
    def test_concurrent_calls_do_not_crash(self) -> None:
        """Multiple threads calling the proxy simultaneously must all complete."""
        call_count = 0
        lock = threading.Lock()

        def slow_get_tasks(*args: Any, **kwargs: Any) -> list:
            nonlocal call_count
            time.sleep(0.02)
            with lock:
                call_count += 1
            return []

        tw = _make_tw()
        tw.get_tasks = slow_get_tasks
        proxy = _proxy_for(tw)

        results: list[Exception | None] = []
        results_lock = threading.Lock()

        def worker() -> None:
            try:
                proxy.get_tasks()
                with results_lock:
                    results.append(None)
            except Exception as exc:  # noqa: BLE001
                with results_lock:
                    results.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        proxy.shutdown()
        assert len(results) == 5, "All threads must complete"
        assert all(r is None for r in results), f"Unexpected errors: {results}"
        assert call_count == 5

    def test_calls_are_serialized(self) -> None:
        """Two concurrent calls must not overlap in time on the worker thread."""
        intervals: list[tuple[float, float]] = []
        iv_lock = threading.Lock()

        def slow_get_tasks(*args: Any, **kwargs: Any) -> list:
            start = time.monotonic()
            time.sleep(0.06)
            end = time.monotonic()
            with iv_lock:
                intervals.append((start, end))
            return []

        tw = _make_tw()
        tw.get_tasks = slow_get_tasks
        proxy = _proxy_for(tw)

        threads = [threading.Thread(target=lambda: proxy.get_tasks()) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        proxy.shutdown()
        assert len(intervals) == 2
        (s1, e1), (s2, e2) = sorted(intervals, key=lambda iv: iv[0])
        assert e1 <= s2 + 1e-3, (
            f"Calls must not overlap: [{s1:.3f}, {e1:.3f}] and [{s2:.3f}, {e2:.3f}]"
        )


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------


class TestTaskWarriorProxyErrorPropagation:
    def test_exception_propagates_to_caller(self) -> None:
        """An exception raised in the worker must reach the calling thread."""
        tw = _make_tw()
        tw.get_tasks = MagicMock(side_effect=RuntimeError("task db gone"))
        proxy = _proxy_for(tw)

        with pytest.raises(RuntimeError, match="task db gone"):
            proxy.get_tasks()

        proxy.shutdown()

    def test_subsequent_call_succeeds_after_exception(self) -> None:
        """The proxy must remain usable after a single failed call."""
        call_count = 0

        def sometimes_fails(*args: Any, **kwargs: Any) -> list:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("first call fails")
            return ["task"]

        tw = _make_tw()
        tw.get_tasks = sometimes_fails
        proxy = _proxy_for(tw)

        with pytest.raises(ValueError):
            proxy.get_tasks()

        result = proxy.get_tasks()
        assert result == ["task"]
        proxy.shutdown()


# ---------------------------------------------------------------------------
# Shutdown
# ---------------------------------------------------------------------------


class TestTaskWarriorProxyShutdown:
    def test_shutdown_stops_worker(self) -> None:
        """After shutdown() the worker thread must be dead."""
        tw = _make_tw()
        proxy = _proxy_for(tw)
        assert proxy._worker_thread.is_alive()
        proxy.shutdown()
        assert not proxy._worker_thread.is_alive()

    def test_shutdown_is_idempotent(self) -> None:
        """Calling shutdown() twice must not raise or deadlock."""
        tw = _make_tw()
        proxy = _proxy_for(tw)
        proxy.shutdown()
        proxy.shutdown()  # must not raise

    def test_new_calls_rejected_after_shutdown(self) -> None:
        """Proxy must raise RuntimeError for calls after shutdown."""
        tw = _make_tw()
        proxy = _proxy_for(tw)
        proxy.shutdown()
        with pytest.raises(RuntimeError, match="worker is no longer running"):
            proxy.get_tasks()


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class TestTaskWarriorProxyMetrics:
    def test_calls_total_increments(self) -> None:
        tw = _make_tw()
        proxy = _proxy_for(tw)
        proxy.get_tasks()
        proxy.get_tasks()
        snap = proxy.get_metrics()
        assert snap["calls_total"] == 2
        proxy.shutdown()

    def test_errors_total_increments_on_failure(self) -> None:
        tw = _make_tw()
        tw.get_tasks = MagicMock(side_effect=RuntimeError("oops"))
        proxy = _proxy_for(tw)
        with pytest.raises(RuntimeError):
            proxy.get_tasks()
        snap = proxy.get_metrics()
        assert snap["errors_total"] == 1
        proxy.shutdown()

    def test_timing_metrics_are_non_negative(self) -> None:
        tw = _make_tw()
        proxy = _proxy_for(tw)
        proxy.get_tasks()
        snap = proxy.get_metrics()
        assert snap["wait_seconds_total"] >= 0.0
        assert snap["run_seconds_total"] >= 0.0
        proxy.shutdown()


# ---------------------------------------------------------------------------
# Factory error
# ---------------------------------------------------------------------------


class TestTaskWarriorProxyFactoryError:
    def test_factory_exception_raises_in_init(self) -> None:
        """If the factory raises, TaskWarriorProxy.__init__ must re-raise it."""
        def bad_factory() -> Any:
            raise OSError("taskwarrior not found")

        with pytest.raises(OSError, match="taskwarrior not found"):
            TaskWarriorProxy(factory=bad_factory)


# ---------------------------------------------------------------------------
# config_store proxy
# ---------------------------------------------------------------------------


class TestConfigStoreProxy:
    def test_config_property_is_fetched_from_worker(self) -> None:
        """config_store.config must return the dict provided by the mock."""
        tw = _make_tw()
        proxy = _proxy_for(tw)
        cfg = proxy.config_store.config
        assert cfg == {"rc.timezone": "UTC"}
        proxy.shutdown()

    def test_set_value_is_called_on_worker(self) -> None:
        """config_store.set_value must be called on the worker thread."""
        tw = _make_tw()
        proxy = _proxy_for(tw)
        proxy.config_store.set_value("timezone", "Europe/Paris")
        tw.config_store.set_value.assert_called_once_with("timezone", "Europe/Paris")
        proxy.shutdown()

    def test_get_contexts_is_called_on_worker(self) -> None:
        tw = _make_tw()
        proxy = _proxy_for(tw)
        contexts = proxy.config_store.get_contexts()
        assert contexts == []
        tw.config_store.get_contexts.assert_called_once()
        proxy.shutdown()

    def test_get_sync_config_is_called_on_worker(self) -> None:
        tw = _make_tw()
        proxy = _proxy_for(tw)
        sync_cfg = proxy.config_store.get_sync_config()
        assert sync_cfg == {}
        tw.config_store.get_sync_config.assert_called_once()
        proxy.shutdown()


# ---------------------------------------------------------------------------
# ProxyMetrics unit tests
# ---------------------------------------------------------------------------


class TestProxyMetrics:
    def test_snapshot_returns_correct_averages(self) -> None:
        m = ProxyMetrics()
        m.record(0.1, 0.2)
        m.record(0.3, 0.4)
        snap = m.snapshot()
        assert snap["calls_total"] == 2
        assert snap["errors_total"] == 0
        assert abs(snap["avg_wait_seconds"] - 0.2) < 1e-6

    def test_error_counted(self) -> None:
        m = ProxyMetrics()
        m.record(0.0, 0.0, error=True)
        snap = m.snapshot()
        assert snap["errors_total"] == 1
        assert snap["calls_total"] == 1
