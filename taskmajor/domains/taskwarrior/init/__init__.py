"""TaskWarrior initialization helpers."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from taskwarrior.dto.context_dto import ContextDTO
from taskwarrior.dto.uda_dto import UdaConfig

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from taskwarrior import TaskWarrior as _TaskWarrior  # noqa: F401

    from ..task_config import TaskConfigService as _TaskConfigService  # noqa: F401

# Expose TaskWarrior and TaskConfigService names at module level so tests can
# monkeypatch them before import-time heavy dependencies are required.
TaskWarrior: Any = None  # type: ignore[assignment]
TaskConfigService: Any = None  # type: ignore[assignment]

__all__ = [
    "TaskWarrior",
    "TaskConfigService",
    "init_taskwarrior",
]


def init_taskwarrior(config) -> None:
    """Initialize the TaskWarrior environment. Idempotent and blocking."""
    _ensure_paths(config)

    global TaskWarrior, TaskConfigService

    if TaskWarrior is None:
        _TW: Any = None
        try:
            from taskwarrior import TaskWarrior as _TW
        except ImportError:
            _TW = None
        TaskWarrior = cast(Any, _TW)  # type: ignore[assignment]

    if TaskConfigService is None:
        _TCS: Any = None
        try:
            from ..task_config import TaskConfigService as _TCS
        except ImportError:
            _TCS = None
        TaskConfigService = cast(Any, _TCS)  # type: ignore[assignment]

    if TaskWarrior is None:
        raise RuntimeError("py-taskwarrior library not available")
    if TaskConfigService is None:
        raise RuntimeError("TaskConfigService not available")

    tw = None
    signatures = [
        {"taskrc_file": config.taskrc, "data_location": config.taskdata},
        {"taskrc": config.taskrc, "data_location": config.taskdata},
        {"taskrc_file": config.taskrc},
        {"taskrc": config.taskrc},
        {"data_location": config.taskdata},
        {},
    ]
    for sig in signatures:
        kwargs = {k: v for k, v in sig.items() if v is not None}
        try:
            tw = TaskWarrior(**kwargs)
            log.debug("Instantiated TaskWarrior with kwargs: %s", list(kwargs.keys()))
            break
        except TypeError:
            continue
    if tw is None:
        try:
            tw = TaskWarrior()
            log.debug("Instantiated TaskWarrior with no kwargs (fallback)")
        except Exception as exc:
            raise RuntimeError(f"Could not instantiate TaskWarrior: {exc}") from exc
    svc = TaskConfigService(tw)

    _run_sync(svc, config)

    log.info("TaskWarrior initialization complete")


def _ensure_paths(config) -> None:
    """Create the taskrc file and data directory if they do not yet exist."""
    if config.taskrc:
        taskrc = Path(config.taskrc).expanduser()
        taskrc.parent.mkdir(parents=True, exist_ok=True)
        taskrc.touch(exist_ok=True)
        log.debug("taskrc path ready: %s", taskrc)

    if config.taskdata:
        data_dir = Path(config.taskdata).expanduser()
        data_dir.mkdir(parents=True, exist_ok=True)
        log.debug("task data dir ready: %s", data_dir)

    if getattr(config, "agent_errors_path", None):
        agent_errors = Path(config.agent_errors_path).expanduser()
        agent_errors.parent.mkdir(parents=True, exist_ok=True)
        log.debug("agent_errors path ready: %s", agent_errors)


def _configure_udas(svc: Any, udas=None) -> None:
    """Apply UDAs from provided presets data by building UdaConfig DTOs."""
    if not udas:
        return

    for uda in udas:
        try:
            uda_config = UdaConfig(**uda)
            svc.add_uda(uda_config)
        except (TypeError, ValueError):
            log.exception("Failed to configure UDA %s", uda.get("name"))


def _configure_contexts(svc: Any, contexts=None) -> None:
    """Apply context definitions from provided presets data."""
    if not contexts:
        return

    for ctx in contexts:
        try:
            context_dto = ContextDTO(**ctx)
            svc.define_context(context_dto)
        except (TypeError, ValueError):
            log.exception("Failed to define context %s", ctx.get("name"))


def _run_sync(svc: Any, cfg) -> None:
    """Run TaskWarrior sync and handle failures according to cfg.sync_fail_fatal."""
    try:
        ok, msg = svc.run_sync()
    except Exception as exc:  # pragma: no cover - defensive
        ok = False
        msg = str(exc)

    if ok:
        return

    if getattr(cfg, "sync_fail_fatal", False):
        raise RuntimeError(msg)

    log.warning("TaskWarrior sync failed: %s", msg)
