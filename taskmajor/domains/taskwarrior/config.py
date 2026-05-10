"""TaskMajor configuration loaded from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, field_validator


class TaskMajorConfig(BaseModel):
    """Configuration settings for TaskMajor."""

    model_config = ConfigDict(extra="forbid")

    server_host: str = "localhost"
    server_port: int = 8888
    server_transport: str = "streamable-http"
    server_name: str = "TaskMajor Server"

    taskrc: str | None = None
    taskdata: str | None = None
    profiles_dir: str = str((Path(__file__).parent.parent.parent / "profiles").resolve())
    profile: str = "standard"

    log_level: str = "DEBUG"
    log_format: str = "text"

    agent_errors_path: str = str(Path.home() / ".taskmajor" / "agent_errors.jsonl")

    otel_service_name: str | None = None
    otel_enabled: bool = True
    otel_transport: str = "grpc"
    otel_exporter_endpoint: str | None = None
    otel_traces_endpoint: str | None = None
    otel_metrics_endpoint: str | None = None
    otel_logs_endpoint: str | None = None

    @field_validator("taskrc", "taskdata", "agent_errors_path", "profiles_dir", mode="before")
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
        config_file = cwd_app_config if cwd_app_config.exists() else project_root / "config" / "config.yaml"
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
        if not config_file.exists():
            return cls()

        import logging
        log = logging.getLogger(__name__)
        log.info(f"****** Loading TaskMajor config from: {config_file}")
        with config_file.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

        if not isinstance(data, dict):
            raise ValueError(f"Configuration file must contain a mapping: {config_file}")

        return cls.model_validate(data)


config = TaskMajorConfig.load()
