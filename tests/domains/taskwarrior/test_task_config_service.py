"""Tests for domains/taskwarrior/task_config.py (TaskConfigService)."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from taskmajor.domains.taskwarrior.task_config import TaskConfigService


def _mock_tw(config: dict | None = None) -> MagicMock:
    """Build a minimal TaskWarrior mock for TaskConfigService."""
    tw = MagicMock()
    tw.config_store.config = config or {}
    return tw


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestInit:
    def test_stores_client_and_config(self):
        tw = _mock_tw({"rc.timezone": "UTC"})
        svc = TaskConfigService(tw)

        assert svc._tw is tw
        assert svc._config["rc.timezone"] == "UTC"


# ---------------------------------------------------------------------------
# get_timezone
# ---------------------------------------------------------------------------


class TestGetTimezone:
    def test_returns_config_value_when_set(self):
        tw = _mock_tw({"rc.timezone": "America/New_York"})
        svc = TaskConfigService(tw)

        assert svc.get_timezone() == "America/New_York"

    def test_returns_system_default_when_not_configured(self):
        tw = _mock_tw({})
        svc = TaskConfigService(tw)

        tz = svc.get_timezone()
        assert isinstance(tz, str)
        assert len(tz) > 0


# ---------------------------------------------------------------------------
# set_timezone
# ---------------------------------------------------------------------------


class TestSetTimezone:
    def test_valid_timezone_calls_config_store_set_value(self):
        tw = _mock_tw()
        svc = TaskConfigService(tw)

        svc.set_timezone("UTC")

        tw.config_store.set_value.assert_called_once_with("timezone", "UTC")

    def test_invalid_iana_timezone_raises_value_error(self):
        tw = _mock_tw()
        svc = TaskConfigService(tw)

        with pytest.raises(ValueError, match="Unknown timezone"):
            svc.set_timezone("Not/A/Real/Zone/At/All")


# ---------------------------------------------------------------------------
# add_uda
# ---------------------------------------------------------------------------


class TestAddUda:
    def test_happy_path_calls_define_uda(self):
        tw = _mock_tw()
        svc = TaskConfigService(tw)
        uda_config = SimpleNamespace(name="complexity", uda_type="numeric", values=[])

        svc.add_uda(uda_config)

        tw.define_uda.assert_called_once_with(uda_config)

    def test_numeric_uda_with_values_logs_warning_and_still_calls_define_uda(self, caplog):
        tw = _mock_tw()
        svc = TaskConfigService(tw)
        uda_config = SimpleNamespace(name="severity", uda_type="numeric", values=["1", "2", "3"])

        with caplog.at_level(logging.WARNING):
            svc.add_uda(uda_config)

        assert any("numeric" in r.getMessage() or "values" in r.getMessage() for r in caplog.records)
        tw.define_uda.assert_called_once()

    def test_inspection_exception_is_swallowed_and_define_uda_still_called(self):
        """A non-fatal exception during UDA type inspection does not block define_uda."""
        tw = _mock_tw()
        svc = TaskConfigService(tw)

        # __bool__ on values raises so `if type_name in (...) and values` propagates
        class BadBool:
            def __bool__(self):
                raise TypeError("unexpected bool evaluation")

        uda_config = SimpleNamespace(name="myuda", uda_type="numeric", values=BadBool())

        svc.add_uda(uda_config)  # must not raise

        tw.define_uda.assert_called_once()


# ---------------------------------------------------------------------------
# delete_uda
# ---------------------------------------------------------------------------


class TestDeleteUda:
    def test_existing_uda_is_deleted(self):
        tw = _mock_tw()
        existing_uda = MagicMock()
        tw.get_uda_config.return_value = existing_uda
        svc = TaskConfigService(tw)

        svc.delete_uda("complexity")

        tw.delete_uda.assert_called_once_with(existing_uda)

    def test_nonexistent_uda_logs_warning_without_raising(self):
        tw = _mock_tw()
        tw.get_uda_config.return_value = None
        svc = TaskConfigService(tw)

        svc.delete_uda("nonexistent")  # must not raise

        tw.delete_uda.assert_not_called()


# ---------------------------------------------------------------------------
# get_all_config
# ---------------------------------------------------------------------------


class TestGetAllConfig:
    def test_returns_copy_of_config_dict(self):
        tw = _mock_tw({"rc.timezone": "UTC", "rc.editor": "vim"})
        svc = TaskConfigService(tw)

        result = svc.get_all_config()

        assert result == {"rc.timezone": "UTC", "rc.editor": "vim"}


# ---------------------------------------------------------------------------
# get_contexts
# ---------------------------------------------------------------------------


class TestGetContexts:
    def test_delegates_to_config_store(self):
        tw = _mock_tw()
        tw.config_store.get_contexts.return_value = [SimpleNamespace(name="work")]
        svc = TaskConfigService(tw)

        result = svc.get_contexts()

        assert len(result) == 1
        assert result[0].name == "work"
        tw.config_store.get_contexts.assert_called_once()


# ---------------------------------------------------------------------------
# define_context / delete_context
# ---------------------------------------------------------------------------


class TestDefineContext:
    def test_delegates_to_define_context_facade(self):
        tw = _mock_tw()
        svc = TaskConfigService(tw)
        ctx = SimpleNamespace(name="work", read_filter="+work", write_filter="+work")

        svc.define_context(ctx)

        tw.define_context.assert_called_once_with(ctx)


class TestDeleteContext:
    def test_delegates_to_delete_context_facade(self):
        tw = _mock_tw()
        svc = TaskConfigService(tw)

        svc.delete_context("work")

        tw.delete_context.assert_called_once_with("work")


# ---------------------------------------------------------------------------
# run_sync
# ---------------------------------------------------------------------------


class TestRunSync:
    def test_sync_not_configured_returns_false_with_message(self):
        tw = _mock_tw()
        tw.is_sync_configured.return_value = False
        svc = TaskConfigService(tw)

        success, msg = svc.run_sync()

        assert success is False
        assert "not configured" in msg.lower()
        tw.synchronize.assert_not_called()

    def test_sync_success_returns_true_with_message(self):
        tw = _mock_tw()
        tw.is_sync_configured.return_value = True
        svc = TaskConfigService(tw)

        success, msg = svc.run_sync()

        assert success is True
        assert "success" in msg.lower()
        tw.synchronize.assert_called_once()

    def test_sync_exception_returns_false_with_error_message(self):
        tw = _mock_tw()
        tw.is_sync_configured.return_value = True
        tw.synchronize.side_effect = RuntimeError("connection refused")
        svc = TaskConfigService(tw)

        success, msg = svc.run_sync()

        assert success is False
        assert "failed" in msg.lower()
        assert "connection refused" in msg
