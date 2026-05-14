"""Unit tests for taskmajor.bootstrap.server

These tests execute the module as a -m style script using runpy.run_module
while stubbing out heavy imports and asyncio.run to avoid starting the server.
"""

from __future__ import annotations

import asyncio
import logging
import runpy
import sys
import types
from unittest.mock import Mock


def _run_server_with_config(monkeypatch, *, taskrc: str = "/tmp/taskrc", taskdata: str | None = None, config_file: str | None = None):
    """Execute taskmajor.bootstrap.server as __main__ with stubbed dependencies.

    Returns (basic_config_mock, logger_mocks_dict, asyncio_run_mock)
    """
    # Stub core.main to avoid importing the real core module
    core_mod = types.ModuleType("taskmajor.bootstrap.core")

    async def fake_main():
        return "ok"

    def fake_create_mcp(*args, **kwargs):
        return (None, None, None)

    async def fake_start_mcp(*args, **kwargs):
        return None

    setattr(core_mod, "main", fake_main)
    setattr(core_mod, "create_mcp", fake_create_mcp)
    setattr(core_mod, "start_mcp", fake_start_mcp)
    monkeypatch.setitem(sys.modules, "taskmajor.bootstrap.core", core_mod)

    # Stub the taskwarrior config module used by the server entrypoint
    cfg_mod = types.ModuleType("taskmajor.domains.taskwarrior.config")
    setattr(cfg_mod, "taskrc", taskrc)
    setattr(cfg_mod, "taskdata", taskdata)
    if config_file is not None:
        setattr(cfg_mod, "config_file", config_file)

    pkg_mod = types.ModuleType("taskmajor.domains.taskwarrior")
    setattr(pkg_mod, "config", cfg_mod)
    monkeypatch.setitem(sys.modules, "taskmajor.domains.taskwarrior.config", cfg_mod)
    monkeypatch.setitem(sys.modules, "taskmajor.domains.taskwarrior", pkg_mod)

    # Patch logging.basicConfig and logging.getLogger to capture calls
    basic_config_mock = Mock()
    logger_mocks: dict[str, Mock] = {}
    original_get_logger = logging.getLogger

    def fake_get_logger(name: str | None = None):
        # Delegate root logger requests to the original getLogger to avoid
        # interfering with pytest internals that call logging.getLogger() without args.
        if name is None:
            return original_get_logger()
        if name not in logger_mocks:
            m = Mock()
            # Provide commonly used logging methods so callers won't fail
            m.info = Mock()
            m.debug = Mock()
            m.warning = Mock()
            m.error = Mock()
            m.exception = Mock()
            logger_mocks[name] = m
        return logger_mocks[name]

    monkeypatch.setattr(logging, "basicConfig", basic_config_mock)
    monkeypatch.setattr(logging, "getLogger", fake_get_logger)

    # Patch asyncio.run so main() is not actually executed
    asyncio_run_mock = Mock()
    monkeypatch.setattr(asyncio, "run", asyncio_run_mock)

    # Run the module as if invoked with `python -m taskmajor.bootstrap.server`
    runpy.run_module("taskmajor.bootstrap.server", run_name="__main__")

    return basic_config_mock, logger_mocks, asyncio_run_mock


def test_logs_with_isolated_taskdata(monkeypatch):
    basic_config, logger_mocks, asyncio_run = _run_server_with_config(monkeypatch, taskrc="/rc", taskdata=None, config_file=None)

    basic_config.assert_called_once_with(level=logging.INFO)
    # Ensure the server logged its startup message as __main__
    assert "__main__" in logger_mocks
    logger_mocks["__main__"].info.assert_any_call(
        "Starting TaskMajor (taskrc=%s, taskdata=%s, config=%s)",
        "/rc",
        "<isolated>",
        "<default>",
    )
    asyncio_run.assert_called_once()


def test_logs_with_taskdata_and_config(monkeypatch):
    basic_config, logger_mocks, asyncio_run = _run_server_with_config(monkeypatch, taskrc="/rc2", taskdata="/data", config_file="/etc/taskmajor/config.yaml")

    basic_config.assert_called_once_with(level=logging.INFO)
    assert "__main__" in logger_mocks
    logger_mocks["__main__"].info.assert_any_call(
        "Starting TaskMajor (taskrc=%s, taskdata=%s, config=%s)",
        "/rc2",
        "/data",
        "/etc/taskmajor/config.yaml",
    )
    asyncio_run.assert_called_once()
