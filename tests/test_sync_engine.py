"""Tests for SyncEngine.

Covers:
- periodic mode: timer fires, synchronize() is called
- manual mode: no timer is created
- on_exit=True: synchronize() called on stop()
- on_exit=False: synchronize() not called on stop()
- force_sync: synchronize() called once
- health: last_sync / consecutive_failures updated correctly
- is_sync_configured() guard: synchronize() skipped when not configured
- enabled=False: SyncEngine not created in config (config-level test)
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from taskmajor.domains.sync.sync_engine import SyncEngine, SyncHealth
from taskmajor.domains.taskwarrior.config import SyncConfig, TaskMajorConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_proxy(*, is_sync_configured: bool = True) -> MagicMock:
    proxy = MagicMock()
    proxy.is_sync_configured.return_value = is_sync_configured
    proxy.synchronize.return_value = None
    return proxy


def _engine(
    proxy: MagicMock,
    mode: str = "manual",
    interval: int = 60,
    on_exit: bool = True,
) -> SyncEngine:
    return SyncEngine(
        proxy,
        {"mode": mode, "interval_seconds": interval, "on_exit": on_exit, "enabled": True},
    )


# ---------------------------------------------------------------------------
# SyncHealth
# ---------------------------------------------------------------------------


class TestSyncHealth:
    def test_initial_state(self):
        h = SyncHealth()
        assert h.last_sync is None
        assert h.consecutive_failures == 0
        assert h.last_error is None

    def test_record_success_resets_failures(self):
        h = SyncHealth()
        h.record_failure(RuntimeError("boom"))
        h.record_failure(RuntimeError("boom"))
        h.record_success()
        assert h.consecutive_failures == 0
        assert h.last_error is None
        assert h.last_sync is not None

    def test_record_failure_increments(self):
        h = SyncHealth()
        h.record_failure(RuntimeError("first"))
        h.record_failure(RuntimeError("second"))
        assert h.consecutive_failures == 2
        assert str(h.last_error) == "second"


# ---------------------------------------------------------------------------
# Manual mode
# ---------------------------------------------------------------------------


class TestManualMode:
    def test_no_timer_created(self):
        proxy = _make_proxy()
        engine = _engine(proxy, mode="manual")
        with patch("taskmajor.domains.sync.sync_engine.threading.Timer") as mock_timer:
            engine.start()
            mock_timer.assert_not_called()

    def test_start_does_not_call_synchronize(self):
        proxy = _make_proxy()
        engine = _engine(proxy, mode="manual")
        engine.start()
        proxy.synchronize.assert_not_called()


# ---------------------------------------------------------------------------
# Periodic mode
# ---------------------------------------------------------------------------


class TestPeriodicMode:
    def test_timer_created_on_start(self):
        proxy = _make_proxy()
        engine = _engine(proxy, mode="periodic", interval=300)
        with patch("taskmajor.domains.sync.sync_engine.threading.Timer") as mock_timer_cls:
            mock_timer_instance = MagicMock()
            mock_timer_cls.return_value = mock_timer_instance
            engine.start()
            mock_timer_cls.assert_called_once_with(300, engine._tick)
            mock_timer_instance.start.assert_called_once()

    def test_timer_is_daemon(self):
        proxy = _make_proxy()
        engine = _engine(proxy, mode="periodic", interval=60)
        with patch("taskmajor.domains.sync.sync_engine.threading.Timer") as mock_timer_cls:
            mock_timer_instance = MagicMock()
            mock_timer_cls.return_value = mock_timer_instance
            engine.start()
            assert mock_timer_instance.daemon is True

    def test_tick_calls_synchronize_and_reschedules(self):
        proxy = _make_proxy()
        engine = _engine(proxy, mode="periodic", interval=60)
        engine._running = True

        with patch.object(engine, "_schedule_next") as mock_schedule:
            engine._tick()

        proxy.synchronize.assert_called_once()
        mock_schedule.assert_called_once()

    def test_tick_does_not_reschedule_when_stopped(self):
        proxy = _make_proxy()
        engine = _engine(proxy, mode="periodic", interval=60)
        engine._running = False

        with patch.object(engine, "_schedule_next") as mock_schedule:
            engine._tick()

        mock_schedule.assert_not_called()

    def test_stop_cancels_timer(self):
        proxy = _make_proxy()
        engine = _engine(proxy, mode="periodic", interval=60, on_exit=False)
        mock_timer = MagicMock()
        engine._timer = mock_timer
        engine._running = True

        engine.stop()

        mock_timer.cancel.assert_called_once()
        assert engine._running is False


# ---------------------------------------------------------------------------
# on_exit behaviour
# ---------------------------------------------------------------------------


class TestOnExit:
    def test_on_exit_true_calls_synchronize(self):
        proxy = _make_proxy()
        engine = _engine(proxy, on_exit=True)
        engine.start()
        engine.stop()
        proxy.synchronize.assert_called_once()

    def test_on_exit_false_does_not_call_synchronize(self):
        proxy = _make_proxy()
        engine = _engine(proxy, on_exit=False)
        engine.start()
        engine.stop()
        proxy.synchronize.assert_not_called()


# ---------------------------------------------------------------------------
# force_sync
# ---------------------------------------------------------------------------


class TestForceSync:
    def test_force_sync_calls_synchronize_once(self):
        proxy = _make_proxy()
        engine = _engine(proxy)
        engine.force_sync()
        proxy.synchronize.assert_called_once()

    def test_force_sync_updates_health(self):
        proxy = _make_proxy()
        engine = _engine(proxy)
        assert engine.health["last_sync"] is None
        engine.force_sync()
        assert engine.health["last_sync"] is not None

    def test_force_sync_records_failure_on_exception(self):
        proxy = _make_proxy()
        proxy.synchronize.side_effect = RuntimeError("network error")
        engine = _engine(proxy)
        engine.force_sync()  # must not raise
        assert engine.health["consecutive_failures"] == 1
        assert "network error" in engine.health["last_error"]


# ---------------------------------------------------------------------------
# Health property
# ---------------------------------------------------------------------------


class TestHealth:
    def test_initial_health_shape(self):
        proxy = _make_proxy()
        engine = _engine(proxy, mode="periodic", interval=120)
        h = engine.health
        assert h["mode"] == "periodic"
        assert h["running"] is False
        assert h["interval_seconds"] == 120
        assert h["last_sync"] is None
        assert h["consecutive_failures"] == 0
        assert h["last_error"] is None

    def test_health_after_successful_sync(self):
        proxy = _make_proxy()
        engine = _engine(proxy)
        engine.force_sync()
        h = engine.health
        assert h["consecutive_failures"] == 0
        assert h["last_sync"] is not None

    def test_health_last_sync_is_iso_format(self):
        proxy = _make_proxy()
        engine = _engine(proxy)
        engine.force_sync()
        # Should not raise
        datetime.fromisoformat(engine.health["last_sync"])

    def test_manual_mode_has_none_interval(self):
        proxy = _make_proxy()
        engine = _engine(proxy, mode="manual")
        assert engine.health["interval_seconds"] is None


# ---------------------------------------------------------------------------
# is_sync_configured() guard
# ---------------------------------------------------------------------------


class TestSyncConfiguredGuard:
    def test_synchronize_not_called_when_not_configured(self):
        proxy = _make_proxy(is_sync_configured=False)
        engine = _engine(proxy, on_exit=True)
        engine.start()
        engine.stop()
        proxy.synchronize.assert_not_called()

    def test_force_sync_skips_when_not_configured(self):
        proxy = _make_proxy(is_sync_configured=False)
        engine = _engine(proxy)
        engine.force_sync()
        proxy.synchronize.assert_not_called()

    def test_no_failure_recorded_when_not_configured(self):
        proxy = _make_proxy(is_sync_configured=False)
        engine = _engine(proxy)
        engine.force_sync()
        assert engine.health["consecutive_failures"] == 0


# ---------------------------------------------------------------------------
# SyncConfig / TaskMajorConfig integration
# ---------------------------------------------------------------------------


class TestSyncConfigModel:
    def test_defaults(self):
        cfg = SyncConfig()
        assert cfg.enabled is False
        assert cfg.mode == "manual"
        assert cfg.interval_seconds == 300
        assert cfg.on_exit is True

    def test_taskmajorconfig_has_sync_field(self):
        cfg = TaskMajorConfig()
        assert isinstance(cfg.sync, SyncConfig)
        assert cfg.sync.enabled is False

    def test_sync_config_parsed_from_dict(self):
        cfg = SyncConfig.model_validate(
            {"enabled": True, "mode": "periodic", "interval_seconds": 60, "on_exit": False}
        )
        assert cfg.enabled is True
        assert cfg.mode == "periodic"
        assert cfg.interval_seconds == 60
        assert cfg.on_exit is False

    def test_extra_fields_forbidden(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SyncConfig.model_validate({"enabled": True, "unknown_field": "oops"})
