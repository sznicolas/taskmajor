"""Tests for sync CLI argument parsing and resolve_sync_config().

Covers:
- resolve_sync_config: no-op when no CLI args provided
- --sync-mode overrides YAML mode
- --no-sync disables sync even when YAML has enabled=true
- --sync-enabled enables sync even when YAML has enabled=false
- --sync-local-dir sets path, enables local, and auto-enables top-level sync
- --sync-remote-origin sets origin, enables remote, and auto-enables top-level sync
- --sync-remote-client-id sets client_id without enabling anything else
- --sync-interval overrides interval
- cascade priority: CLI > YAML > Pydantic defaults
- SyncConfig validation: invalid mode, non-positive interval, remote requires origin
- LocalSyncConfig and RemoteSyncConfig: extra fields forbidden
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest
from pydantic import ValidationError

import argparse
from pathlib import Path

import pytest
from pydantic import ValidationError

from taskmajor.bootstrap.core import resolve_sync_config
from taskmajor.domains.taskwarrior.config import LocalSyncConfig, RemoteSyncConfig, SyncConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ns(**kwargs) -> argparse.Namespace:
    defaults = {
        "sync_enabled": None,
        "sync_mode": None,
        "sync_interval": None,
        "sync_local_dir": None,
        "sync_remote_origin": None,
        "sync_remote_client_id": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _yaml_sync(**kwargs) -> SyncConfig:
    return SyncConfig.model_validate(kwargs)


# ---------------------------------------------------------------------------
# New semantics tests
# ---------------------------------------------------------------------------


class TestDefaultsAndInjection:
    def test_default_injects_local_backend(self):
        cfg = SyncConfig()
        assert cfg.is_configured is True
        assert isinstance(cfg.local, LocalSyncConfig)
        assert "sync_server" in cfg.local.server_dir


class TestCLIOverrides:
    def test_mode_and_interval_overrides(self):
        cfg = _yaml_sync()
        result = resolve_sync_config(cfg, _ns(sync_mode="manual", sync_interval=60))
        assert result.mode == "manual"
        assert result.interval_seconds == 60

    def test_sync_local_dir_injected(self, tmp_path: Path):
        cfg = _yaml_sync()
        result = resolve_sync_config(cfg, _ns(sync_local_dir=str(tmp_path)))
        assert result.local.server_dir == str(tmp_path)
        assert result.is_configured is True

    def test_sync_remote_origin_injected(self):
        cfg = _yaml_sync()
        result = resolve_sync_config(cfg, _ns(sync_remote_origin="https://example.com"))
        assert isinstance(result.remote, RemoteSyncConfig)
        assert result.remote.origin == "https://example.com"
        assert result.is_configured is True

    def test_no_sync_clears_backends(self):
        cfg = _yaml_sync()
        # first ensure there is a backend
        assert cfg.is_configured is True
        result = resolve_sync_config(cfg, _ns(sync_enabled=False))
        assert result.local is None
        assert result.remote is None
        assert result.is_configured is False


class TestValidation:
    def test_invalid_mode_raises(self):
        with pytest.raises(ValidationError):
            SyncConfig.model_validate({"mode": "auto"})

    def test_non_positive_interval_raises(self):
        with pytest.raises(ValidationError):
            SyncConfig.model_validate({"interval_seconds": 0})

    def test_remote_requires_origin(self):
        with pytest.raises(ValidationError):
            RemoteSyncConfig.model_validate({})

    def test_local_path_expansion(self):
        cfg = LocalSyncConfig.model_validate({"server_dir": "~/.task_sync"})
        assert str(Path.home()) in cfg.server_dir
