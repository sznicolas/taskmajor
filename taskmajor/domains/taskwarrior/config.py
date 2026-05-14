"""TaskMajor configuration loaded from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class LocalSyncConfig(BaseModel):
    """Local sync server configuration (taskchampion-sync-server or compatible)."""

    model_config = ConfigDict(extra="forbid")

    server_dir: str = "~/.task_mcp/sync_server"

    @field_validator("server_dir", mode="before")
    @classmethod
    def _expand_path(cls, value: Any) -> Any:
        if not value:
            return value
        return str(Path(value).expanduser())


class RemoteSyncConfig(BaseModel):
    """Remote sync server configuration."""

    model_config = ConfigDict(extra="forbid")

    origin: str | None = None
    client_id: str | None = None
    encryption_secret: str | None = None

    @model_validator(mode="after")
    def _remote_requires_origin(self) -> RemoteSyncConfig:
        # If RemoteSyncConfig exists, origin must be provided
        if not getattr(self, "origin", None):
            raise ValueError("remote sync requires 'origin' when remote is configured")
        return self


class SyncConfig(BaseModel):
    """Synchronization configuration for TaskWarrior."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["periodic", "manual"] = "periodic"
    interval_seconds: int = 300
    on_exit: bool = True
    local: LocalSyncConfig | None = None
    remote: RemoteSyncConfig | None = None

    @field_validator("interval_seconds", mode="before")
    @classmethod
    def _positive_interval(cls, value: Any) -> Any:
        if isinstance(value, int) and value <= 0:
            raise ValueError("interval_seconds must be > 0")
        return value


class TaskMajorConfig(BaseModel):
    """Configuration settings for TaskMajor."""

    model_config = ConfigDict(extra="forbid")

    server_host: str = "localhost"
    server_port: int = 8888
    server_transport: str = "streamable-http"
    server_name: str = "TaskMajor Server"

    # TaskWarrior configuration
    taskrc: str = "~/.taskrc_mcp"
    # If None, uses isolated mode (auto-derived from taskrc)
    # If set to a path like "~/.task", agent shares user's real task database
    taskdata: str | None = None
    profiles_dir: str = str((Path(__file__).parent.parent.parent / "profiles").resolve())
    profile: str = "standard"

    # Path to the loaded TaskMajor config file (config.yaml) or the path that would be used
    config_file: str | None = None

    log_level: str = "DEBUG"
    log_format: str = "text"

    agent_errors_path: str = str(Path.home() / ".taskmajor" / "agent_errors.jsonl")

    # Synchronization configuration
    sync: SyncConfig = SyncConfig()

    otel_service_name: str | None = None
    otel_enabled: bool = True
    otel_transport: str = "grpc"
    otel_exporter_endpoint: str | None = None
    otel_traces_endpoint: str | None = None
    otel_metrics_endpoint: str | None = None
    otel_logs_endpoint: str | None = None

    @field_validator(
        "taskrc", "taskdata", "agent_errors_path", "profiles_dir", "config_file", mode="before"
    )
    @classmethod
    def _expand_path(cls, value: Any) -> Any:
        if value in (None, ""):
            return None if value == "" else value
        return str(Path(value).expanduser())

    @classmethod
    def load(cls, path: str | Path | None = None) -> TaskMajorConfig:
        """Load configuration from YAML, using fixed project path."""
        # Always use the fixed config path relative to project root
        project_root = Path(__file__).parent.parent.parent.resolve()
        # Prefer working-directory app config (for local development/testing)
        cwd_app_config = Path.cwd() / "app" / "config" / "config.yaml"
        config_file = (
            cwd_app_config if cwd_app_config.exists() else project_root / "config" / "config.yaml"
        )
        if path is not None:
            candidate = Path(path).expanduser()
            if candidate.exists():
                # If a directory was provided, look for config.yaml inside it.
                if candidate.is_dir():
                    config_file = candidate / "config.yaml"
                else:
                    config_file = candidate
            else:
                raise FileNotFoundError(f"Configuration file not found: {candidate}")

        import logging

        log = logging.getLogger(__name__)

        # Always record which config path was considered, even if the file doesn't exist.
        if not config_file.exists():
            log.info("No TaskMajor config file found at: %s (using defaults)", config_file)
            inst = cls()
            inst.config_file = str(config_file)
            return inst

        log.info("****** Loading TaskMajor config from: %s", config_file)
        with config_file.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

        if not isinstance(data, dict):
            raise ValueError(f"Configuration file must contain a mapping: {config_file}")

        cfg = cls.model_validate(data)
        # store the path used to load the configuration
        cfg.config_file = str(config_file)
        return cfg


config = TaskMajorConfig.load()
