"""Tests for TaskCommandSerializer.

Covers:
- Sequential execution: two concurrent threads do not overlap
- Lock release on exception: no deadlock after a failed call
- Idempotency: double-install is a no-op
- Keyword argument forwarding: no_opt and other kwargs pass through unchanged
- Metrics tracking: calls_total and errors_total are correct
- Module-level install_serializer sets the sentinel
"""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest

from taskmajor.utils.task_serializer import (
    _SENTINEL,
    TaskCommandSerializer,
    install_serializer,
)


def _make_client() -> MagicMock:
    """Return a fake TaskWarrior client with a plain run_task_command."""
    adapter = MagicMock()
    adapter.run_task_command = MagicMock(return_value="ok")
    # Remove sentinel so each test starts fresh regardless of import-time state.
    try:
        delattr(adapter, _SENTINEL)
    except AttributeError:
        pass
    client = MagicMock()
    client.adapter = adapter
    return client


class TestTaskCommandSerializerConcurrency:
    def test_concurrent_calls_are_sequential(self) -> None:
        """Two threads calling run_task_command must not overlap in time."""
        serializer = TaskCommandSerializer()
        intervals: list[tuple[float, float]] = []
        lock = threading.Lock()

        def slow_run(*args: object, **kwargs: object) -> str:
            start = time.monotonic()
            time.sleep(0.06)
            end = time.monotonic()
            with lock:
                intervals.append((start, end))
            return "ok"

        client = _make_client()
        client.adapter.run_task_command = slow_run
        serializer.install(client)

        threads = [
            threading.Thread(target=client.adapter.run_task_command, args=(["add", "x"],))
            for _ in range(2)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert len(intervals) == 2, "Both calls must complete"
        (s1, e1), (s2, e2) = sorted(intervals, key=lambda iv: iv[0])
        assert e1 <= s2 + 1e-3, (
            f"Calls must not overlap: [{s1:.3f}, {e1:.3f}] and [{s2:.3f}, {e2:.3f}]"
        )


class TestTaskCommandSerializerErrorHandling:
    def test_lock_released_after_exception(self) -> None:
        """The lock must be released even when run_task_command raises."""
        serializer = TaskCommandSerializer()
        client = _make_client()
        client.adapter.run_task_command = MagicMock(side_effect=RuntimeError("boom"))
        serializer.install(client)

        with pytest.raises(RuntimeError, match="boom"):
            client.adapter.run_task_command(["add", "test"])

        # A subsequent call must not deadlock — the lock must be free.
        completed = threading.Event()

        def follow_up() -> None:
            try:
                client.adapter.run_task_command(["list"])
            except RuntimeError:
                pass
            completed.set()

        t = threading.Thread(target=follow_up)
        t.start()
        t.join(timeout=2.0)
        assert completed.is_set(), "Lock was not released after an exception"


class TestTaskCommandSerializerIdempotency:
    def test_double_install_is_noop(self) -> None:
        """Installing the serializer twice must not double-wrap the method."""
        serializer = TaskCommandSerializer()
        client = _make_client()

        serializer.install(client)
        first_wrapper = client.adapter.run_task_command

        serializer.install(client)  # second call — must be a no-op
        assert client.adapter.run_task_command is first_wrapper, (
            "Second install must not replace the already-wrapped method"
        )

    def test_sentinel_is_set_after_install(self) -> None:
        """The sentinel attribute must be True on the adapter after install."""
        serializer = TaskCommandSerializer()
        client = _make_client()
        serializer.install(client)
        assert getattr(client.adapter, _SENTINEL, False) is True


class TestTaskCommandSerializerArgForwarding:
    def test_positional_args_are_forwarded(self) -> None:
        """Positional arguments must reach the original function unchanged."""
        serializer = TaskCommandSerializer()
        received: list[object] = []

        def capture(*args: object, **kwargs: object) -> str:
            received.extend(args)
            return "ok"

        client = _make_client()
        client.adapter.run_task_command = capture
        serializer.install(client)

        client.adapter.run_task_command(["task", "list"], False)
        assert received == [["task", "list"], False]

    def test_keyword_args_are_forwarded(self) -> None:
        """Keyword arguments such as no_opt must reach the original function."""
        serializer = TaskCommandSerializer()
        received_kwargs: dict[str, object] = {}

        def capture(*args: object, **kwargs: object) -> str:
            received_kwargs.update(kwargs)
            return "ok"

        client = _make_client()
        client.adapter.run_task_command = capture
        serializer.install(client)

        client.adapter.run_task_command(["list"], no_opt=True)
        assert received_kwargs == {"no_opt": True}


class TestTaskCommandSerializerMetrics:
    def test_calls_and_errors_counted(self) -> None:
        """calls_total and errors_total must reflect successful and failed calls."""
        serializer = TaskCommandSerializer()
        client = _make_client()

        call_count = 0

        def sometimes_fails(*args: object, **kwargs: object) -> str:
            nonlocal call_count
            call_count += 1
            if kwargs.get("no_opt"):
                raise RuntimeError("fail")
            return "ok"

        client.adapter.run_task_command = sometimes_fails
        serializer.install(client)

        client.adapter.run_task_command(["list"])  # success
        with pytest.raises(RuntimeError):
            client.adapter.run_task_command(["list"], no_opt=True)  # error

        snap = serializer.metrics.snapshot()
        assert snap["calls_total"] == 2
        assert snap["errors_total"] == 1

    def test_wait_and_run_times_are_positive(self) -> None:
        """Timing metrics must be non-negative after at least one call."""
        serializer = TaskCommandSerializer()
        client = _make_client()

        def quick(*args: object, **kwargs: object) -> str:
            return "ok"

        client.adapter.run_task_command = quick
        serializer.install(client)

        client.adapter.run_task_command(["list"])

        snap = serializer.metrics.snapshot()
        assert snap["wait_seconds_total"] >= 0.0
        assert snap["run_seconds_total"] >= 0.0


class TestInstallSerializerFunction:
    def test_uses_module_singleton(self) -> None:
        """install_serializer() must delegate to the module-level task_serializer."""
        client = _make_client()
        install_serializer(client)
        assert getattr(client.adapter, _SENTINEL, False) is True
