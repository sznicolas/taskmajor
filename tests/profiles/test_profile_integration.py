from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path

import pytest
import yaml

from taskmajor.bootstrap.core import parse_profile_args
from taskmajor.domains.taskwarrior import TaskMajorConfig


class DummyTaskService:
    class DummyTaskConfig:
        def __init__(self) -> None:
            self.added_udas: list[object] = []

        def add_uda(self, uda_config) -> None:
            self.added_udas.append(uda_config)

    def __init__(self, *args, **kwargs) -> None:
        self.task_config = self.DummyTaskConfig()

    def get_stats(self, **kwargs):
        return {"ok": True, "kwargs": kwargs}


class DummyTaskWarrior:
    def __init__(self, *args, **kwargs) -> None:
        pass


class DummyErrorLog:
    def __init__(self, path: str) -> None:
        self.path = path


def write_profile(
    profile_dir: Path,
    *,
    name: str,
    prompts: list[dict] | None = None,
    resources: list[dict] | None = None,
    instructions: str | None = None,
) -> Path:
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / "prompts").mkdir(parents=True, exist_ok=True)
    (profile_dir / "instructions").mkdir(parents=True, exist_ok=True)

    for prompt in prompts or []:
        (profile_dir / "prompts" / prompt["source"]).write_text("# prompt\n", encoding="utf-8")

    if instructions is not None:
        (profile_dir / "instructions" / "010_objective.md").write_text(
            instructions, encoding="utf-8"
        )

    manifest = {
        "name": name,
        "version": "1.0.0",
        "resources": resources or [],
    }
    (profile_dir / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )
    return profile_dir


def make_config(profiles_root: Path, profile: str | None = None) -> TaskMajorConfig:
    return TaskMajorConfig(profiles_dir=str(profiles_root), profile=profile or "standard")


def _resolve(value):
    if inspect.isawaitable(value):
        return asyncio.run(value)
    return value


# Placeholders used by skipped tests to satisfy linters
mcp = None
task_service = None


def test_profile_loading_flow(tmp_path):
    pytest.skip(
        "Custom profile paths are no longer supported. Profiles must be in taskmajor/profiles/"
    )


def test_conflict_detection(tmp_path):
    pytest.skip(
        "Custom profile paths are no longer supported. Profiles must be in taskmajor/profiles/"
    )


def test_cli_args_parsing(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "taskmajor",
            "--profile",
            "/tmp/alpha",
            "--profile",
            "/tmp/beta",
            "--no-profiles",
        ],
    )

    args = parse_profile_args()

    # With single-profile support the last provided --profile wins (argparse behavior)
    assert args.profile == "/tmp/beta"
    assert args.no_profiles is True


def test_dynamic_registration(tmp_path, monkeypatch):
    pytest.skip(
        "Custom profile paths are no longer supported. Profiles must be in taskmajor/profiles/"
    )

    prompt_names = {
        getattr(prompt, "name", str(prompt))
        for prompt in _resolve(mcp.list_prompts(run_middleware=False))
    }
    resource_uris = {
        str(getattr(resource, "uri", resource))
        for resource in _resolve(mcp.list_resources(run_middleware=False))
    }

    assert "hello" in prompt_names
    assert "taskmajor://alpha/stats" in resource_uris


def test_profile_uda_requirements_are_applied(tmp_path, monkeypatch):
    pytest.skip(
        "Custom profile paths are no longer supported. Profiles must be in taskmajor/profiles/"
    )

    assert [uda.name for uda in task_service.task_config.added_udas] == ["ticket_id"]
