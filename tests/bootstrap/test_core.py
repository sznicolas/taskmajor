"""Tests for bootstrap/core.py — parse_profile_args, _apply_profile, start_mcp, main."""

from __future__ import annotations

import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from taskmajor.bootstrap.core import _apply_profile, main, parse_profile_args, start_mcp
from taskmajor.domains.profiles.models import (
    ContextDefinition,
    PromptDefinition,
    ResourceDefinition,
    UdaDefinition,
)
from taskmajor.domains.taskwarrior import TaskMajorConfig


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# parse_profile_args
# ---------------------------------------------------------------------------


class TestParseProfileArgs:
    def test_defaults_when_no_args(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["taskmajor"])
        args = parse_profile_args()

        assert args.profile is None
        assert args.no_profiles is False
        assert args.transport is None

    def test_profile_flag(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["taskmajor", "--profile", "productivity"])
        args = parse_profile_args()

        assert args.profile == "productivity"

    def test_no_profiles_flag(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["taskmajor", "--no-profiles"])
        args = parse_profile_args()

        assert args.no_profiles is True

    def test_transport_flag(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["taskmajor", "--transport", "sse"])
        args = parse_profile_args()

        assert args.transport == "sse"

    def test_unknown_args_are_ignored(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["taskmajor", "--unknown-flag", "value"])
        args = parse_profile_args()  # must not raise

        assert args.profile is None


# ---------------------------------------------------------------------------
# _apply_profile helpers
# ---------------------------------------------------------------------------


def _empty_manifest(name="base"):
    return SimpleNamespace(name=name, version="1.0", udas=[], contexts=[], tools=[])


def _make_profile_manager(manifests=None, prompts=None, resources=None):
    """Build a profile_manager mock with configurable manifests, prompts, and resources."""
    pm = MagicMock()
    pm.get_loaded_profiles.return_value = manifests or []

    prompt_loader = MagicMock()
    prompt_loader.list_prompts.return_value = list(prompts.keys()) if prompts else []
    if prompts:
        prompt_loader.get_prompt_definition.side_effect = lambda name: prompts.get(name)
        prompt_loader.get_prompt.side_effect = lambda name: prompts[name].content if name in prompts else None
    pm.get_prompt_loader.return_value = prompt_loader

    resource_mapper = MagicMock()
    resource_mapper.list_resources.return_value = list(resources.keys()) if resources else []
    if resources:
        resource_mapper.get_resource.side_effect = lambda uri: resources.get(uri)
        resource_mapper.create_handler.return_value = lambda: '{"ok": true}'
    pm.get_resource_mapper.return_value = resource_mapper

    return pm


# ---------------------------------------------------------------------------
# _apply_profile
# ---------------------------------------------------------------------------


class TestApplyProfile:
    def test_no_loaded_profiles_is_noop(self):
        mcp = MagicMock()
        task_service = MagicMock()
        pm = _make_profile_manager(manifests=[])

        _apply_profile(mcp, task_service, pm)

        task_service.task_config.add_uda.assert_not_called()
        task_service.task_config.define_context.assert_not_called()

    def test_uda_from_profile_calls_add_uda(self):
        mcp = MagicMock()
        task_service = MagicMock()
        uda = UdaDefinition(name="complexity", type="numeric", label="Complexity")
        manifest = SimpleNamespace(name="base", version="1.0", udas=[uda], contexts=[], tools=[])
        pm = _make_profile_manager(manifests=[manifest])

        _apply_profile(mcp, task_service, pm)

        task_service.task_config.add_uda.assert_called_once()

    def test_uda_registration_failure_is_swallowed(self):
        mcp = MagicMock()
        task_service = MagicMock()
        task_service.task_config.add_uda.side_effect = RuntimeError("UDA error")
        uda = UdaDefinition(name="bad", type="numeric", label="Bad")
        manifest = SimpleNamespace(name="base", version="1.0", udas=[uda], contexts=[], tools=[])
        pm = _make_profile_manager(manifests=[manifest])

        _apply_profile(mcp, task_service, pm)  # must not raise

    def test_context_from_profile_calls_define_context(self):
        mcp = MagicMock()
        task_service = MagicMock()
        ctx = ContextDefinition(name="work", read_filter="+work", write_filter="+work")
        manifest = SimpleNamespace(name="base", version="1.0", udas=[], contexts=[ctx], tools=[])
        pm = _make_profile_manager(manifests=[manifest])

        _apply_profile(mcp, task_service, pm)

        task_service.task_config.define_context.assert_called_once()

    def test_context_registration_failure_is_swallowed(self):
        mcp = MagicMock()
        task_service = MagicMock()
        task_service.task_config.define_context.side_effect = RuntimeError("ctx error")
        ctx = ContextDefinition(name="bad")
        manifest = SimpleNamespace(name="base", version="1.0", udas=[], contexts=[ctx], tools=[])
        pm = _make_profile_manager(manifests=[manifest])

        _apply_profile(mcp, task_service, pm)  # must not raise

    def test_empty_prompt_name_is_skipped(self):
        mcp = MagicMock()
        task_service = MagicMock()
        manifest = _empty_manifest()
        # Prompt with empty name → should be skipped
        pm = _make_profile_manager(manifests=[manifest], prompts={"": None})

        _apply_profile(mcp, task_service, pm)

        mcp.prompt.assert_not_called()

    def test_whitespace_prompt_name_is_skipped(self):
        mcp = MagicMock()
        task_service = MagicMock()
        manifest = _empty_manifest()
        pm = MagicMock()
        pm.get_loaded_profiles.return_value = [manifest]
        prompt_loader = MagicMock()
        prompt_loader.list_prompts.return_value = ["   "]  # whitespace-only
        pm.get_prompt_loader.return_value = prompt_loader
        resource_mapper = MagicMock()
        resource_mapper.list_resources.return_value = []
        pm.get_resource_mapper.return_value = resource_mapper

        _apply_profile(mcp, task_service, pm)

        mcp.prompt.assert_not_called()

    def test_none_prompt_definition_is_skipped(self):
        mcp = MagicMock()
        task_service = MagicMock()
        manifest = _empty_manifest()
        pm = MagicMock()
        pm.get_loaded_profiles.return_value = [manifest]
        prompt_loader = MagicMock()
        prompt_loader.list_prompts.return_value = ["orphan"]
        prompt_loader.get_prompt_definition.return_value = None
        pm.get_prompt_loader.return_value = prompt_loader
        resource_mapper = MagicMock()
        resource_mapper.list_resources.return_value = []
        pm.get_resource_mapper.return_value = resource_mapper

        _apply_profile(mcp, task_service, pm)

        mcp.prompt.assert_not_called()

    def test_valid_prompt_is_registered_on_mcp(self):
        mcp = MagicMock()
        task_service = MagicMock()
        manifest = _empty_manifest()
        defn = PromptDefinition(name="triage", content="Do triage tasks.", source_profile="base")
        pm = _make_profile_manager(manifests=[manifest], prompts={"triage": defn})

        _apply_profile(mcp, task_service, pm)

        mcp.prompt.assert_called_once()

    def test_resource_from_profile_is_added_to_mcp(self):
        mcp = MagicMock()
        task_service = MagicMock()
        manifest = _empty_manifest()
        resource_def = ResourceDefinition(
            uri="taskmajor://custom",
            name="Custom Resource",
            description="A test resource",
            backend_function="some_func",
        )
        pm = _make_profile_manager(
            manifests=[manifest],
            resources={"taskmajor://custom": resource_def},
        )

        _apply_profile(mcp, task_service, pm)

        mcp.add_resource.assert_called_once()

    def test_none_resource_definition_is_skipped(self):
        mcp = MagicMock()
        task_service = MagicMock()
        manifest = _empty_manifest()
        pm = MagicMock()
        pm.get_loaded_profiles.return_value = [manifest]
        prompt_loader = MagicMock()
        prompt_loader.list_prompts.return_value = []
        pm.get_prompt_loader.return_value = prompt_loader
        resource_mapper = MagicMock()
        resource_mapper.list_resources.return_value = ["taskmajor://orphan"]
        resource_mapper.get_resource.return_value = None  # no definition
        pm.get_resource_mapper.return_value = resource_mapper

        _apply_profile(mcp, task_service, pm)

        mcp.add_resource.assert_not_called()

    def test_multiple_profiles_apply_udas_from_all(self):
        mcp = MagicMock()
        task_service = MagicMock()
        uda1 = UdaDefinition(name="complexity", type="numeric", label="Complexity")
        uda2 = UdaDefinition(name="severity", type="string", label="Severity")
        manifest1 = SimpleNamespace(name="parent", version="1.0", udas=[uda1], contexts=[], tools=[])
        manifest2 = SimpleNamespace(name="child", version="1.0", udas=[uda2], contexts=[], tools=[])
        pm = _make_profile_manager(manifests=[manifest1, manifest2])

        _apply_profile(mcp, task_service, pm)

        assert task_service.task_config.add_uda.call_count == 2

    def test_dynamic_prompt_callable_returns_content(self):
        """The _dynamic_prompt closure captured by mcp.prompt should return the prompt text."""
        mcp = MagicMock()
        task_service = MagicMock()
        manifest = _empty_manifest()
        defn = PromptDefinition(name="triage", content="Do triage tasks.", source_profile="base")
        pm = _make_profile_manager(manifests=[manifest], prompts={"triage": defn})

        _apply_profile(mcp, task_service, pm)

        # Capture the callable that was registered with mcp.prompt(...)(callable)
        captured_fn = mcp.prompt.return_value.call_args[0][0]
        pm.get_prompt_loader.return_value.get_prompt.return_value = "Do triage tasks."

        result = captured_fn()
        assert result == "Do triage tasks."

    def test_dynamic_prompt_raises_key_error_when_prompt_not_found(self):
        """_dynamic_prompt raises KeyError when get_prompt returns None."""
        mcp = MagicMock()
        task_service = MagicMock()
        manifest = _empty_manifest()
        defn = PromptDefinition(name="missing", content="Gone.", source_profile="base")
        pm = _make_profile_manager(manifests=[manifest], prompts={"missing": defn})

        _apply_profile(mcp, task_service, pm)

        captured_fn = mcp.prompt.return_value.call_args[0][0]
        # Clear side_effect set by _make_profile_manager so return_value takes effect
        pm.get_prompt_loader.return_value.get_prompt.side_effect = None
        pm.get_prompt_loader.return_value.get_prompt.return_value = None

        with pytest.raises(KeyError, match="missing"):
            captured_fn()


# ---------------------------------------------------------------------------
# start_mcp
# ---------------------------------------------------------------------------


class TestStartMcp:
    def test_stdio_transport_calls_run_async_without_host_port(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["taskmajor"])
        mock_mcp = MagicMock()
        mock_mcp.run_async = AsyncMock()
        mock_ts = MagicMock()
        mock_ts.taskwarrior_client.get_info.return_value = {"backend_type": "taskchampion"}

        with patch("taskmajor.bootstrap.core.create_mcp", return_value=(mock_mcp, mock_ts, MagicMock())):
            cfg = TaskMajorConfig()
            cfg.server_transport = "stdio"
            _run_async(start_mcp(config_override=cfg))

        mock_mcp.run_async.assert_called_once_with(transport="stdio")

    def test_http_transport_calls_run_async_with_host_and_port(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["taskmajor"])
        mock_mcp = MagicMock()
        mock_mcp.run_async = AsyncMock()
        mock_ts = MagicMock()
        mock_ts.taskwarrior_client.get_info.return_value = {"backend_type": "taskchampion"}

        with patch("taskmajor.bootstrap.core.create_mcp", return_value=(mock_mcp, mock_ts, MagicMock())):
            cfg = TaskMajorConfig()
            cfg.server_transport = "streamable-http"
            _run_async(start_mcp(config_override=cfg))

        mock_mcp.run_async.assert_called_once_with(
            transport="streamable-http",
            port=cfg.server_port,
            host=cfg.server_host,
        )

    def test_task_config_error_exits_with_code_1(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["taskmajor"])
        from taskwarrior import TaskConfigurationError

        with patch(
            "taskmajor.bootstrap.core.create_mcp",
            side_effect=TaskConfigurationError("task not found"),
        ):
            with pytest.raises(SystemExit) as exc_info:
                _run_async(start_mcp(config_override=TaskMajorConfig()))

        assert exc_info.value.code == 1

    def test_bad_taskwarrior_version_exits_with_code_1(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["taskmajor"])
        mock_mcp = MagicMock()
        mock_ts = MagicMock()
        # CLI adapter with an old version should trigger the version check failure
        mock_ts.taskwarrior_client.get_info.return_value = {
            "backend_type": "taskwarrior-cli",
            "backend_version": "2.6.3",
        }

        with patch("taskmajor.bootstrap.core.create_mcp", return_value=(mock_mcp, mock_ts, MagicMock())):
            with pytest.raises(SystemExit) as exc_info:
                _run_async(start_mcp(config_override=TaskMajorConfig()))

        assert exc_info.value.code == 1

    def test_non_task_config_error_is_reraised(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["taskmajor"])

        with patch(
            "taskmajor.bootstrap.core.create_mcp",
            side_effect=RuntimeError("unexpected"),
        ):
            with pytest.raises(RuntimeError, match="unexpected"):
                _run_async(start_mcp(config_override=TaskMajorConfig()))

    def test_cli_transport_flag_overrides_config(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["taskmajor", "--transport", "stdio"])
        mock_mcp = MagicMock()
        mock_mcp.run_async = AsyncMock()
        mock_ts = MagicMock()
        mock_ts.taskwarrior_client.get_info.return_value = {"backend_type": "taskchampion"}

        with patch("taskmajor.bootstrap.core.create_mcp", return_value=(mock_mcp, mock_ts, MagicMock())):
            cfg = TaskMajorConfig()
            cfg.server_transport = "streamable-http"  # config says http
            _run_async(start_mcp(config_override=cfg))

        # CLI --transport stdio should win
        mock_mcp.run_async.assert_called_once_with(transport="stdio")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


class TestMain:
    def test_main_delegates_to_start_mcp(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["taskmajor"])
        with patch("taskmajor.bootstrap.core.start_mcp", new_callable=AsyncMock) as mock_start:
            _run_async(main())
            mock_start.assert_called_once_with()
