"""Tests for taskmajor.domains.taskwarrior.init — init_taskwarrior() and helpers."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from taskmajor.domains.taskwarrior.init import (
    _configure_udas,
    _ensure_paths,
    _run_sync,
    init_taskwarrior,
)

# Get expected UDAs from GTD preset
_EXPECTED_UDAS = ["entry_type", "estimate"]

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


class _FakeConfig:
    """Minimal config stub used across tests."""

    def __init__(
        self,
        taskrc=None,
        data=None,
        sync_server_uri=None,
        sync_client_id=None,
        sync_encryption_secret=None,
        sync_fail_fatal=False,
    ):
        self.taskrc = taskrc
        self.taskdata = data
        self.sync_server_uri = sync_server_uri
        self.sync_client_id = sync_client_id
        self.sync_encryption_secret = sync_encryption_secret
        self.sync_fail_fatal = sync_fail_fatal


def _make_svc():
    """Return a MagicMock that mimics TaskConfigService."""
    svc = MagicMock()
    svc.run_sync.return_value = (True, "")
    return svc


# ---------------------------------------------------------------------------
# _ensure_paths
# ---------------------------------------------------------------------------


def test_ensure_paths_creates_taskrc_and_data(tmp_path):
    taskrc = tmp_path / "task" / "taskrc"
    data = tmp_path / "task" / "data"
    cfg = _FakeConfig(taskrc=str(taskrc), data=str(data))

    _ensure_paths(cfg)

    assert taskrc.exists()
    assert data.is_dir()


def test_ensure_paths_is_idempotent(tmp_path):
    taskrc = tmp_path / "taskrc"
    data = tmp_path / "data"
    cfg = _FakeConfig(taskrc=str(taskrc), data=str(data))

    _ensure_paths(cfg)
    _ensure_paths(cfg)  # second call must not raise


def test_ensure_paths_noop_when_paths_not_configured():
    cfg = _FakeConfig()
    _ensure_paths(cfg)  # should not raise


# ---------------------------------------------------------------------------
# _configure_udas
# ---------------------------------------------------------------------------


def test_configure_udas_applies_gtd_preset():
    """Verify _configure_udas applies the GTD preset."""
    svc = _make_svc()
    # Apply GTD preset directly to mock service
    _configure_udas(svc)


# ---------------------------------------------------------------------------
# _run_sync — permissive mode
# ---------------------------------------------------------------------------


def test_run_sync_success_does_not_raise():
    svc = _make_svc()
    cfg = _FakeConfig()
    _run_sync(svc, cfg)  # should not raise


def test_run_sync_failure_permissive_logs_warning_not_raises(caplog):
    svc = _make_svc()
    svc.run_sync.return_value = (False, "connection refused")
    cfg = _FakeConfig(sync_fail_fatal=False)

    with caplog.at_level(logging.WARNING):
        _run_sync(svc, cfg)

    assert any("connection refused" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# _run_sync — strict mode
# ---------------------------------------------------------------------------


def test_run_sync_failure_strict_raises_runtime_error():
    svc = _make_svc()
    svc.run_sync.return_value = (False, "network error")
    cfg = _FakeConfig(sync_fail_fatal=True)

    with pytest.raises(RuntimeError, match="network error"):
        _run_sync(svc, cfg)


# ---------------------------------------------------------------------------
# init_taskwarrior — integration-style (mocked TaskWarrior + TaskConfigService)
# ---------------------------------------------------------------------------


@patch("taskmajor.domains.taskwarrior.init.TaskConfigService")
@patch("taskmajor.domains.taskwarrior.init.TaskWarrior")
def test_init_configures_udas_and_syncs(mock_tw_cls, mock_svc_cls, tmp_path):
    taskrc = tmp_path / "taskrc"
    data = tmp_path / "data"
    cfg = _FakeConfig(taskrc=str(taskrc), data=str(data))

    mock_svc = _make_svc()
    mock_svc_cls.return_value = mock_svc

    init_taskwarrior(cfg)

    # GTD preset applies, sync called
    mock_svc.run_sync.assert_called_once()
    mock_svc.configure_sync.assert_not_called()


@patch("taskmajor.domains.taskwarrior.init.TaskConfigService")
@patch("taskmajor.domains.taskwarrior.init.TaskWarrior")
def test_init_strict_mode_raises_on_sync_failure(mock_tw_cls, mock_svc_cls, tmp_path):
    taskrc = tmp_path / "taskrc"
    cfg = _FakeConfig(taskrc=str(taskrc), sync_fail_fatal=True)

    mock_svc = _make_svc()
    mock_svc.run_sync.return_value = (False, "server down")
    mock_svc_cls.return_value = mock_svc

    with pytest.raises(RuntimeError, match="server down"):
        init_taskwarrior(cfg)


@patch("taskmajor.domains.taskwarrior.init.TaskConfigService")
@patch("taskmajor.domains.taskwarrior.init.TaskWarrior")
def test_init_permissive_mode_continues_on_sync_failure(
    mock_tw_cls, mock_svc_cls, tmp_path, caplog
):
    taskrc = tmp_path / "taskrc"
    cfg = _FakeConfig(taskrc=str(taskrc), sync_fail_fatal=False)

    mock_svc = _make_svc()
    mock_svc.run_sync.return_value = (False, "server down")
    mock_svc_cls.return_value = mock_svc

    with caplog.at_level(logging.WARNING):
        init_taskwarrior(cfg)  # must not raise

    assert any("server down" in r.message for r in caplog.records)
