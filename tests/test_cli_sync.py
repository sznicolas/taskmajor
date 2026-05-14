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

from taskmajor.bootstrap.core import resolve_sync_config
from taskmajor.domains.taskwarrior.config import (
    LocalSyncConfig,
    RemoteSyncConfig,
    SyncConfig,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ns(**kwargs) -> argparse.Namespace:
    """Build a Namespace with all sync fields defaulted to None."""
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
    """Build a SyncConfig representing a YAML-loaded state."""
    return SyncConfig(**kwargs)


# ---------------------------------------------------------------------------
# Pass-through: no CLI args
# ---------------------------------------------------------------------------


class TestPassThrough:
    def test_no_overrides_preserves_enabled_false(self):
        cfg = _yaml_sync(enabled=False, mode="manual")
        result = resolve_sync_config(cfg, _ns())
        assert result.enabled is False
        assert result.mode == "manual"

    def test_no_overrides_preserves_enabled_true(self):
        cfg = _yaml_sync(enabled=True, mode="periodic", interval_seconds=120)
        result = resolve_sync_config(cfg, _ns())
        assert result.enabled is True
        assert result.mode == "periodic"
        assert result.interval_seconds == 120

    def test_no_overrides_preserves_on_exit(self):
        cfg = _yaml_sync(on_exit=False)
        result = resolve_sync_config(cfg, _ns())
        assert result.on_exit is False


# ---------------------------------------------------------------------------
# --sync-enabled / --no-sync
# ---------------------------------------------------------------------------


class TestSyncEnabledFlag:
    def test_no_sync_disables_enabled_true_yaml(self):
        cfg = _yaml_sync(enabled=True)
        result = resolve_sync_config(cfg, _ns(sync_enabled=False))
        assert result.enabled is False

    def test_sync_enabled_enables_disabled_yaml(self):
        cfg = _yaml_sync(enabled=False)
        result = resolve_sync_config(cfg, _ns(sync_enabled=True))
        assert result.enabled is True

    def test_sync_enabled_none_does_not_override(self):
        cfg = _yaml_sync(enabled=True)
        result = resolve_sync_config(cfg, _ns(sync_enabled=None))
        assert result.enabled is True


# ---------------------------------------------------------------------------
# --sync-mode
# ---------------------------------------------------------------------------


class TestSyncModeFlag:
    def test_manual_overrides_periodic_yaml(self):
        cfg = _yaml_sync(mode="periodic")
        result = resolve_sync_config(cfg, _ns(sync_mode="manual"))
        assert result.mode == "manual"

    def test_periodic_overrides_manual_yaml(self):
        cfg = _yaml_sync(mode="manual")
        result = resolve_sync_config(cfg, _ns(sync_mode="periodic"))
        assert result.mode == "periodic"

    def test_none_does_not_override_mode(self):
        cfg = _yaml_sync(mode="periodic")
        result = resolve_sync_config(cfg, _ns(sync_mode=None))
        assert result.mode == "periodic"


# ---------------------------------------------------------------------------
# --sync-interval
# ---------------------------------------------------------------------------


class TestSyncIntervalFlag:
    def test_interval_overrides_yaml(self):
        cfg = _yaml_sync(interval_seconds=300)
        result = resolve_sync_config(cfg, _ns(sync_interval=60))
        assert result.interval_seconds == 60

    def test_none_does_not_override_interval(self):
        cfg = _yaml_sync(interval_seconds=600)
        result = resolve_sync_config(cfg, _ns(sync_interval=None))
        assert result.interval_seconds == 600


# ---------------------------------------------------------------------------
# --sync-local-dir
# ---------------------------------------------------------------------------


class TestSyncLocalDir:
    def test_sets_server_dir(self, tmp_path: Path):
        cfg = _yaml_sync()
        result = resolve_sync_config(cfg, _ns(sync_local_dir=str(tmp_path)))
        assert result.local.server_dir == str(tmp_path)

    def test_enables_local(self):
        cfg = _yaml_sync()
        assert cfg.local.enabled is False
        result = resolve_sync_config(cfg, _ns(sync_local_dir="/tmp/sync"))
        assert result.local.enabled is True

    def test_auto_enables_top_level_sync(self):
        cfg = _yaml_sync(enabled=False)
        result = resolve_sync_config(cfg, _ns(sync_local_dir="/tmp/sync"))
        assert result.enabled is True

    def test_no_sync_still_wins_over_local_dir(self):
        # --no-sync is applied after --sync-local-dir sets enabled=True
        # The user explicitly says no-sync so it wins
        cfg = _yaml_sync(enabled=False)
        result = resolve_sync_config(cfg, _ns(sync_enabled=False, sync_local_dir="/tmp/sync"))
        assert result.enabled is False


# ---------------------------------------------------------------------------
# --sync-remote-origin
# ---------------------------------------------------------------------------


class TestSyncRemoteOrigin:
    def test_sets_origin(self):
        cfg = _yaml_sync()
        result = resolve_sync_config(cfg, _ns(sync_remote_origin="https://example.com"))
        assert result.remote.origin == "https://example.com"

    def test_enables_remote(self):
        cfg = _yaml_sync()
        assert cfg.remote.enabled is False
        result = resolve_sync_config(cfg, _ns(sync_remote_origin="https://example.com"))
        assert result.remote.enabled is True

    def test_auto_enables_top_level_sync(self):
        cfg = _yaml_sync(enabled=False)
        result = resolve_sync_config(cfg, _ns(sync_remote_origin="https://example.com"))
        assert result.enabled is True


# ---------------------------------------------------------------------------
# --sync-remote-client-id
# ---------------------------------------------------------------------------


class TestSyncRemoteClientId:
    def test_sets_client_id_only(self):
        cfg = _yaml_sync()
        result = resolve_sync_config(
            cfg, _ns(sync_remote_client_id="my-uuid")
        )
        assert result.remote.client_id == "my-uuid"
        # Does not auto-enable remote or top-level sync
        assert result.remote.enabled is False
        assert result.enabled is False

    def test_client_id_combined_with_origin(self):
        cfg = _yaml_sync()
        result = resolve_sync_config(
            cfg, _ns(sync_remote_origin="https://example.com", sync_remote_client_id="my-uuid")
        )
        assert result.remote.origin == "https://example.com"
        assert result.remote.client_id == "my-uuid"
        assert result.remote.enabled is True


# ---------------------------------------------------------------------------
# Cascade priority: CLI > YAML > defaults
# ---------------------------------------------------------------------------


class TestCascadePriority:
    def test_cli_overrides_yaml_which_overrides_defaults(self):
        # Pydantic default: enabled=False, mode="manual"
        # YAML: enabled=True, mode="periodic"
        yaml_sync = _yaml_sync(enabled=True, mode="periodic", interval_seconds=600)
        # CLI: mode=manual
        result = resolve_sync_config(yaml_sync, _ns(sync_mode="manual"))
        assert result.enabled is True      # from YAML
        assert result.mode == "manual"     # from CLI
        assert result.interval_seconds == 600  # from YAML

    def test_cli_false_wins_over_yaml_true(self):
        yaml_sync = _yaml_sync(enabled=True)
        result = resolve_sync_config(yaml_sync, _ns(sync_enabled=False))
        assert result.enabled is False


# ---------------------------------------------------------------------------
# SyncConfig validation
# ---------------------------------------------------------------------------


class TestSyncConfigValidation:
    def test_invalid_mode_raises(self):
        with pytest.raises(ValidationError):
            SyncConfig.model_validate({"mode": "auto"})

    def test_non_positive_interval_raises(self):
        with pytest.raises(ValidationError):
            SyncConfig.model_validate({"interval_seconds": 0})

    def test_negative_interval_raises(self):
        with pytest.raises(ValidationError):
            SyncConfig.model_validate({"interval_seconds": -1})

    def test_positive_interval_ok(self):
        cfg = SyncConfig.model_validate({"interval_seconds": 1})
        assert cfg.interval_seconds == 1

    def test_remote_enabled_without_origin_raises(self):
        with pytest.raises(ValidationError):
            RemoteSyncConfig.model_validate({"enabled": True, "origin": ""})

    def test_remote_enabled_with_origin_ok(self):
        cfg = RemoteSyncConfig.model_validate({"enabled": True, "origin": "https://example.com"})
        assert cfg.enabled is True

    def test_extra_fields_forbidden_in_sync_config(self):
        with pytest.raises(ValidationError):
            SyncConfig.model_validate({"unknown_key": "boom"})

    def test_extra_fields_forbidden_in_local(self):
        with pytest.raises(ValidationError):
            LocalSyncConfig.model_validate({"unknown_key": "boom"})

    def test_extra_fields_forbidden_in_remote(self):
        with pytest.raises(ValidationError):
            RemoteSyncConfig.model_validate({"unknown_key": "boom"})


# ---------------------------------------------------------------------------
# LocalSyncConfig path expansion
# ---------------------------------------------------------------------------


class TestLocalSyncConfigPathExpansion:
    def test_tilde_expanded_in_server_dir(self):
        cfg = LocalSyncConfig.model_validate({"server_dir": "~/.task_sync"})
        assert "~" not in cfg.server_dir
        assert str(Path.home()) in cfg.server_dir

    def test_absolute_path_unchanged(self):
        cfg = LocalSyncConfig.model_validate({"server_dir": "/absolute/path"})
        assert cfg.server_dir == "/absolute/path"
