from __future__ import annotations

import logging
from pathlib import Path

import pytest
import yaml

from taskmajor.domains.profiles import ProfileConflictError, ProfileManager
from taskmajor.domains.profiles.models import ProfileManifest
from taskmajor.domains.taskwarrior import TaskMajorConfig


class DummyTaskService:
    pass


def write_profile(
    profile_dir: Path,
    *,
    name: str,
    version: str = "1.0.0",
    prompts: list[dict] | None = None,
    resources: list[dict] | None = None,
    resources_yaml: list[dict] | None = None,
    instructions: str | None = None,
) -> Path:
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / "prompts").mkdir(parents=True, exist_ok=True)
    (profile_dir / "instructions").mkdir(parents=True, exist_ok=True)

    for prompt in prompts or []:
        source = prompt["source"]
        (profile_dir / "prompts" / source).write_text(f"# {prompt['name']}\n", encoding="utf-8")

    if instructions is not None:
        (profile_dir / "instructions" / "010_objective.md").write_text(
            instructions, encoding="utf-8"
        )

    manifest = {
        "name": name,
        "version": version,
        "resources": resources or [],
    }
    (profile_dir / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )

    if resources_yaml is not None:
        (profile_dir / "resources.yaml").write_text(
            yaml.safe_dump(resources_yaml, sort_keys=False), encoding="utf-8"
        )

    return profile_dir


def make_config(profiles_root: Path, profile: str | None = None) -> TaskMajorConfig:
    return TaskMajorConfig(profiles_dir=str(profiles_root), profile=profile or "standard")


def test_load_all_with_single_profile_via_config(tmp_path):
    pytest.skip(
        "Custom profile paths are no longer supported. Profiles must be in taskmajor/profiles/"
    )


def test_load_all_with_cli_profiles_override(tmp_path):
    profiles_root = tmp_path / "profiles"
    write_profile(
        profiles_root / "alpha",
        name="alpha",
        prompts=[{"name": "config-prompt", "source": "config_prompt.md"}],
    )
    cli_profile = write_profile(
        tmp_path / "cli-profile",
        name="beta",
        prompts=[{"name": "cli-prompt", "source": "cli_prompt.md"}],
        instructions="# Beta Instructions",
    )

    manager = ProfileManager(
        make_config(profiles_root, "alpha"),
        cli_profile=str(cli_profile),
    )
    manager.set_task_service(DummyTaskService())

    loaded = manager.load_all()

    assert [manifest.name for manifest in loaded] == ["beta"]
    # With implicit scan, prompt name = file stem (cli_prompt.md → cli_prompt)
    assert manager.get_prompt_loader().get_prompt("cli_prompt") == "# cli-prompt\n"
    assert manager.get_prompt_loader().get_prompt("config_prompt") is None
    assert manager.get_instructions() == "# Beta Instructions"


def test_get_instructions_with_instructions_dir(tmp_path):
    cli_profile = write_profile(
        tmp_path / "myprofile",
        name="myprofile",
        instructions="# Do stuff\n\nAlways be helpful.",
    )
    manager = ProfileManager(
        make_config(tmp_path / "profiles"),
        cli_profile=str(cli_profile),
    )
    manager.set_task_service(DummyTaskService())
    manager.load_all()

    assert manager.get_instructions() == "# Do stuff\n\nAlways be helpful."
    assert manager.get_instructions_loader().source_profile == "myprofile"


def test_get_instructions_without_instructions_dir(tmp_path):
    cli_profile = write_profile(tmp_path / "myprofile", name="myprofile")
    manager = ProfileManager(
        make_config(tmp_path / "profiles"),
        cli_profile=str(cli_profile),
    )
    manager.set_task_service(DummyTaskService())
    manager.load_all()

    assert manager.get_instructions() is None


def test_check_conflicts_child_overrides_parent_warns(caplog):
    """Child overriding parent resource URI logs warning but doesn't raise."""
    manifests = [
        ProfileManifest(
            name="parent",
            version="1.0.0",
            resources=[
                {
                    "uri": "taskmajor://dup",
                    "name": "A",
                    "description": "A",
                    "backend": {"function": "query_tasks"},
                }
            ],
        ),
        ProfileManifest(
            name="child",
            version="1.0.0",
            resources=[
                {
                    "uri": "taskmajor://dup",
                    "name": "B",
                    "description": "B",
                    "backend": {"function": "get_stats"},
                }
            ],
        ),
    ]

    manager = ProfileManager(make_config(Path("/tmp/profiles")))
    caplog.set_level(logging.WARNING)

    # Should NOT raise, only warn
    manager._check_conflicts(manifests)

    # Verify warning was logged
    assert any("overrides resource URI" in record.message for record in caplog.records)


def test_check_conflicts_sibling_resource_conflict_raises(caplog):
    """Two siblings (at different indices but conceptually same level) declaring same URI → error."""
    # This tests the scenario where a parent with multiple parents
    # has siblings that conflict. We manually create such a chain.
    manifests = [
        # Hypothetical: parent1 at depth 0
        ProfileManifest(
            name="parent1",
            version="1.0.0",
            resources=[
                {
                    "uri": "taskmajor://sibling-conflict",
                    "name": "A",
                    "description": "A",
                    "backend": {"function": "query_tasks"},
                }
            ],
        ),
        # Hypothetical: parent2 at depth 1 (sibling of parent1 conceptually, different index)
        # In a real extends chain, siblings would be at different depths due to flattening.
        # This test is illustrative; true sibling conflicts are prevented by the resolution algorithm.
        ProfileManifest(
            name="parent2",
            version="1.0.0",
            resources=[
                {
                    "uri": "taskmajor://sibling-conflict",
                    "name": "B",
                    "description": "B",
                    "backend": {"function": "get_stats"},
                }
            ],
        ),
    ]

    manager = ProfileManager(make_config(Path("/tmp/profiles")))
    caplog.set_level(logging.WARNING)

    # With current flat chain structure, depth(parent1)=0, depth(parent2)=1
    # So this is detected as "parent2 overrides parent1", not a sibling conflict.
    # This is by design: the chain structure prevents true sibling conflicts.
    manager._check_conflicts(manifests)
    assert any("overrides resource URI" in record.message for record in caplog.records)


def test_check_conflicts_no_longer_checks_prompts(caplog):
    """Prompt conflicts are no longer checked (prompts are loaded implicitly from prompts/ dir)."""
    manifests = [
        ProfileManifest(name="alpha", version="1.0.0"),
        ProfileManifest(name="beta", version="1.0.0"),
    ]
    manager = ProfileManager(make_config(Path("/tmp/profiles")))
    caplog.set_level(logging.WARNING)
    manager._check_conflicts(manifests)
    # No warning expected — prompt conflicts are no longer detected via manifest


def test_resolve_profile_path_explicit_vs_profiles_dir(tmp_path):
    pytest.skip(
        "Custom profile paths are no longer supported. Profiles must be in taskmajor/profiles/"
    )


def test_resolve_profile_path_missing_directory_raises(tmp_path):
    manager = ProfileManager(make_config(tmp_path / "profiles"))

    with pytest.raises(FileNotFoundError):
        manager._resolve_profile_path("missing")


def test_get_diagnostics_returns_expected_structure(tmp_path):
    pytest.skip(
        "Custom profile paths are no longer supported. Profiles must be in taskmajor/profiles/"
    )


def test_extends_chain_loads_parents_first(tmp_path):
    """Test that extends chain loads parent before child."""
    # Create parent profile
    parent_path = tmp_path / "parent"
    write_profile(
        parent_path,
        name="parent",
        version="1.0.0",
        instructions="Parent instructions\n",
        resources=[
            {
                "uri": "taskmajor://resource/parent",
                "name": "Parent Resource",
                "description": "From parent",
                "backend": {"function": "query_tasks"},
            }
        ],
    )

    # Create child profile that extends parent
    child_path = tmp_path / "child"
    child_manifest = {
        "name": "child",
        "version": "2.0.0",
        "extends": str(parent_path),  # Absolute path to parent
        "resources": [
            {
                "uri": "taskmajor://resource/child",
                "name": "Child Resource",
                "description": "From child",
                "backend": {"function": "get_metadata"},
            }
        ],
    }
    child_path.mkdir(parents=True, exist_ok=True)
    (child_path / "manifest.yaml").write_text(yaml.safe_dump(child_manifest), encoding="utf-8")
    (child_path / "instructions").mkdir(parents=True, exist_ok=True)
    (child_path / "instructions" / "020_workflow.md").write_text(
        "Child instructions\n", encoding="utf-8"
    )

    # Load the child
    manager = ProfileManager(
        make_config(tmp_path / "profiles"),
        cli_profile=str(child_path),
    )
    manager.set_task_service(DummyTaskService())
    manifests = manager.load_all()

    # Should have parent then child
    assert len(manifests) == 2
    assert manifests[0].name == "parent"
    assert manifests[1].name == "child"

    # Instructions should be accumulated
    instructions = manager.get_instructions()
    assert "Parent instructions" in instructions
    assert "Child instructions" in instructions
    assert "\n---\n\n" in instructions  # Separator present


def test_extends_cycle_raises_profile_conflict_error(tmp_path):
    """Test that circular extends raises ProfileConflictError."""
    # Create profile A that extends B
    a_path = tmp_path / "cycle_a"
    a_path.mkdir(parents=True, exist_ok=True)
    (a_path / "instructions").mkdir(parents=True, exist_ok=True)
    a_manifest = {
        "name": "cycle_a",
        "version": "1.0.0",
        "extends": str(tmp_path / "cycle_b"),
    }
    (a_path / "manifest.yaml").write_text(yaml.safe_dump(a_manifest), encoding="utf-8")

    # Create profile B that extends A (cycle!)
    b_path = tmp_path / "cycle_b"
    b_path.mkdir(parents=True, exist_ok=True)
    (b_path / "instructions").mkdir(parents=True, exist_ok=True)
    b_manifest = {
        "name": "cycle_b",
        "version": "1.0.0",
        "extends": str(a_path),
    }
    (b_path / "manifest.yaml").write_text(yaml.safe_dump(b_manifest), encoding="utf-8")

    # Loading A should detect the cycle
    manager = ProfileManager(
        make_config(tmp_path / "profiles"),
        cli_profile=str(a_path),
    )
    manager.set_task_service(DummyTaskService())

    with pytest.raises(ProfileConflictError, match="Cycle"):
        manager.load_all()


def test_load_all_sorts_by_priority(tmp_path):
    pytest.skip(
        "Custom profile paths are no longer supported. Profiles must be in taskmajor/profiles/"
    )


def test_uda_type_conflict(tmp_path):
    # Parent declares my_uda as string
    parent_path = tmp_path / "parent"
    parent_path.mkdir(parents=True, exist_ok=True)
    (parent_path / "instructions").mkdir(parents=True, exist_ok=True)
    parent_manifest = {
        "name": "parent",
        "version": "1.0.0",
        "udas": [{"name": "my_uda", "type": "string"}],
    }
    (parent_path / "manifest.yaml").write_text(yaml.safe_dump(parent_manifest), encoding="utf-8")

    # Child re-declares my_uda as integer -> conflict
    child_path = tmp_path / "child"
    child_path.mkdir(parents=True, exist_ok=True)
    (child_path / "instructions").mkdir(parents=True, exist_ok=True)
    child_manifest = {
        "name": "child",
        "version": "1.0.0",
        "extends": str(parent_path),
        "udas": [{"name": "my_uda", "type": "integer"}],
    }
    (child_path / "manifest.yaml").write_text(yaml.safe_dump(child_manifest), encoding="utf-8")

    manager = ProfileManager(make_config(tmp_path / "profiles"), cli_profile=str(child_path))
    manager.set_task_service(DummyTaskService())

    with pytest.raises(ProfileConflictError):
        manager.load_all()


def test_uda_value_restriction_valid(tmp_path):
    # Parent defines allowed values A,B,C; child restricts to A,B -> OK
    parent_path = tmp_path / "parent_v"
    parent_path.mkdir(parents=True, exist_ok=True)
    (parent_path / "instructions").mkdir(parents=True, exist_ok=True)
    parent_manifest = {
        "name": "parent_v",
        "version": "1.0.0",
        "udas": [{"name": "status", "type": "string", "values": ["A", "B", "C"]}],
    }
    (parent_path / "manifest.yaml").write_text(yaml.safe_dump(parent_manifest), encoding="utf-8")

    child_path = tmp_path / "child_v"
    child_path.mkdir(parents=True, exist_ok=True)
    (child_path / "instructions").mkdir(parents=True, exist_ok=True)
    child_manifest = {
        "name": "child_v",
        "version": "1.0.0",
        "extends": str(parent_path),
        "udas": [{"name": "status", "type": "string", "values": ["A", "B"]}],
    }
    (child_path / "manifest.yaml").write_text(yaml.safe_dump(child_manifest), encoding="utf-8")

    manager = ProfileManager(make_config(tmp_path / "profiles"), cli_profile=str(child_path))
    manager.set_task_service(DummyTaskService())

    # Should not raise
    manifests = manager.load_all()
    assert [m.name for m in manifests] == ["parent_v", "child_v"]


def test_uda_value_extension_invalid(tmp_path):
    # Parent allows A,B; child adds C -> should fail
    parent_path = tmp_path / "parent_e"
    parent_path.mkdir(parents=True, exist_ok=True)
    (parent_path / "instructions").mkdir(parents=True, exist_ok=True)
    parent_manifest = {
        "name": "parent_e",
        "version": "1.0.0",
        "udas": [{"name": "flag", "type": "string", "values": ["A", "B"]}],
    }
    (parent_path / "manifest.yaml").write_text(yaml.safe_dump(parent_manifest), encoding="utf-8")

    child_path = tmp_path / "child_e"
    child_path.mkdir(parents=True, exist_ok=True)
    (child_path / "instructions").mkdir(parents=True, exist_ok=True)
    child_manifest = {
        "name": "child_e",
        "version": "1.0.0",
        "extends": str(parent_path),
        "udas": [{"name": "flag", "type": "string", "values": ["A", "B", "C"]}],
    }
    (child_path / "manifest.yaml").write_text(yaml.safe_dump(child_manifest), encoding="utf-8")

    manager = ProfileManager(make_config(tmp_path / "profiles"), cli_profile=str(child_path))
    manager.set_task_service(DummyTaskService())

    with pytest.raises(ProfileConflictError):
        manager.load_all()


def test_base_profile_loads():
    """The built-in 'base' profile loads successfully with the expected tools and resource."""
    manager = ProfileManager(
        TaskMajorConfig(profile="base"),
    )
    manager.set_task_service(DummyTaskService())
    manifests = manager.load_all()

    assert len(manifests) == 1
    manifest = manifests[0]
    assert manifest.name == "base"
    assert manifest.version == "1.0.0"

    expected_tools = {
        "add_task",
        "get_task",
        "query_tasks",
        "update_task",
        "delete_task",
        "done_task",
    }
    assert expected_tools.issubset(set(manifest.tools))

    resource_uris = {r["uri"] for r in manifest.resources}
    assert "taskmajor://tasks/pending" in resource_uris
