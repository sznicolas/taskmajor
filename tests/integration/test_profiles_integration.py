from __future__ import annotations

import json
from pathlib import Path

import pytest

import taskmajor.domains.profiles as profiles_pkg
from taskmajor.domains.profiles import ProfileManager
from taskmajor.domains.taskwarrior import TaskMajorConfig

pytestmark = pytest.mark.integration


def _discover_builtin_profiles() -> list[str]:
    """Return sorted list of built-in profile directory names under taskmajor/profiles.
    Only include directories that contain a manifest.yaml file."""
    pkg_file = Path(profiles_pkg.__file__)
    built_in_root = pkg_file.parent.parent.parent / "profiles"
    if not built_in_root.exists():
        return []
    profiles = []
    for p in built_in_root.iterdir():
        if not p.is_dir():
            continue
        if (p / "manifest.yaml").is_file():
            profiles.append(p.name)
    return sorted(profiles)


BUILTIN_PROFILES = _discover_builtin_profiles()

# Derive PROMPT_PROFILES and INSTRUCTIONS_PROFILES by probing each profile with ProfileManager
PROMPT_PROFILES: list[str] = []
INSTRUCTIONS_PROFILES: list[str] = []
for _p in BUILTIN_PROFILES:
    cfg = TaskMajorConfig(profile=_p)
    pm = ProfileManager(cfg)
    try:
        # Phase 1: load_all() will load prompts and instructions without task_service
        pm.load_all()
        prompts = pm.get_prompt_loader().get_all_definitions()
        instr = pm.get_instructions()
        if prompts:
            PROMPT_PROFILES.append(_p)
        if instr and isinstance(instr, str) and instr.strip():
            INSTRUCTIONS_PROFILES.append(_p)
    except Exception:
        # Skip profiles that fail to load
        continue


@pytest.fixture
def mock_task_service():
    """Minimal TaskService stub: methods accept **kwargs so ResourceMapper validation is permissive."""

    class MinimalTaskService:
        def query_tasks(self, **kwargs):
            return []

        def get_stats(self, **kwargs):
            return {"ok": True}

        def get_tasks_by_scope(self, **kwargs):
            return {}

        def get_projects(self, **kwargs):
            return []

        def get_tags(self, **kwargs):
            return []

        def get_udas(self, **kwargs):
            return []

        def get_metadata(self, **kwargs):
            return {}

        def next_task(self, **kwargs):
            return None

        # Additional backends occasionally referenced
        def add_task(self, **kwargs):
            return {"id": "t1"}

        def update_task(self, **kwargs):
            return True

        def delete_task(self, **kwargs):
            return True

        def get_task(self, **kwargs):
            return {}

    return MinimalTaskService()


@pytest.mark.parametrize("profile_name", BUILTIN_PROFILES)
def test_profile_loads_successfully(profile_name, mock_task_service):
    cfg = TaskMajorConfig(profile=profile_name)
    pm = ProfileManager(cfg)
    pm.set_task_service(mock_task_service)
    manifests = pm.load_all()
    assert manifests, f"Loading profile '{profile_name}' returned empty manifests list"


@pytest.mark.parametrize("profile_name", BUILTIN_PROFILES)
def test_all_resources_registered(profile_name, mock_task_service):
    cfg = TaskMajorConfig(profile=profile_name)
    pm = ProfileManager(cfg)
    pm.set_task_service(mock_task_service)
    pm.load_all()
    rm = pm.get_resource_mapper()
    uris = rm.list_resources()
    assert len(uris) == len(set(uris)), f"Duplicate URIs detected in profile '{profile_name}'"


@pytest.mark.parametrize("profile_name", BUILTIN_PROFILES)
def test_all_resources_callable(profile_name, mock_task_service):
    cfg = TaskMajorConfig(profile=profile_name)
    pm = ProfileManager(cfg)
    pm.set_task_service(mock_task_service)
    pm.load_all()
    rm = pm.get_resource_mapper()
    for uri in rm.list_resources():
        try:
            handler = rm.create_handler(uri)
            payload_str = handler()
            # Ensure valid JSON string
            parsed = json.loads(payload_str)
            assert parsed is not None
        except Exception as exc:
            pytest.fail(f"Resource handler failed for profile='{profile_name}', uri='{uri}': {exc}")


@pytest.mark.parametrize("profile_name", INSTRUCTIONS_PROFILES)
def test_instructions_loaded(profile_name, mock_task_service):
    cfg = TaskMajorConfig(profile=profile_name)
    pm = ProfileManager(cfg)
    pm.set_task_service(mock_task_service)
    pm.load_all()
    instructions = pm.get_instructions()
    assert instructions and isinstance(instructions, str) and instructions.strip(), (
        f"No instructions loaded for profile '{profile_name}'"
    )


@pytest.mark.parametrize("profile_name", PROMPT_PROFILES)
def test_prompts_loaded(profile_name, mock_task_service):
    cfg = TaskMajorConfig(profile=profile_name)
    pm = ProfileManager(cfg)
    pm.set_task_service(mock_task_service)
    pm.load_all()
    prompts = pm.get_prompt_loader().get_all_definitions()
    assert isinstance(prompts, dict)
    assert prompts, f"No prompts found for profile '{profile_name}'"


@pytest.mark.skipif(
    "coding-assistant" not in BUILTIN_PROFILES,
    reason="'coding-assistant' profile not available in built-ins",
)
def test_extends_chain_resolved_correctly(mock_task_service):
    # coding-assistant extends standard; validate chain order
    cfg = TaskMajorConfig(profile="coding-assistant")
    pm = ProfileManager(cfg)
    pm.set_task_service(mock_task_service)
    chain = pm.load_all()
    names = [m.name for m in chain]
    assert "standard" in names and names[-1] == "coding-assistant", (
        f"Unexpected extends chain: {names}"
    )


@pytest.mark.skipif(
    "coding-assistant" not in BUILTIN_PROFILES,
    reason="'coding-assistant' profile not available in built-ins",
)
def test_inherited_resources_merged(mock_task_service):
    cfg = TaskMajorConfig(profile="coding-assistant")
    pm = ProfileManager(cfg)
    pm.set_task_service(mock_task_service)
    pm.load_all()
    rm = pm.get_resource_mapper()
    uris = set(rm.list_resources())
    # Parent resource from 'standard'
    assert "taskmajor://agenda/today" in uris
    # Child-specific resource from 'coding-assistant'
    assert "taskmajor://dashboard/my-tasks" in uris
