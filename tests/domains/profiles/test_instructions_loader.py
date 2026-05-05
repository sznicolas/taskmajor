from __future__ import annotations

from pathlib import Path

import pytest

from taskmajor.domains.profiles.instructions_loader import InstructionsLoader
from taskmajor.domains.profiles.models import ProfileManifest


def make_manifest(name: str = "profile") -> ProfileManifest:
    return ProfileManifest(name=name, version="1.0.0")


def write_profile(profile_dir: Path, fragments: dict[str, str]) -> Path:
    instructions_dir = profile_dir / "instructions"
    instructions_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in fragments.items():
        (instructions_dir / filename).write_text(content, encoding="utf-8")
    return profile_dir


def test_fragment_loading_order(tmp_path):
    profile_dir = write_profile(
        tmp_path / "profile",
        {
            "010_objective.md": "# Objective\n",
            "020_workflow.md": "# Workflow\n",
            "030_date_usage.md": "# Dates\n",
        },
    )

    loader = InstructionsLoader()
    loader.load_from_profile(profile_dir, make_manifest("profile"))

    assert loader.get_instructions() == "# Objective\n\n---\n\n# Workflow\n\n---\n\n# Dates\n"
    assert loader.source_profile == "profile"


def test_fragment_override(tmp_path):
    parent_dir = write_profile(
        tmp_path / "parent",
        {"020_workflow.md": "# Parent workflow\n"},
    )
    child_dir = write_profile(
        tmp_path / "child",
        {"020_workflow.md": "# Child workflow\n"},
    )

    loader = InstructionsLoader()
    loader.load_from_profile(parent_dir, make_manifest("parent"))
    loader.load_from_profile(child_dir, make_manifest("child"))

    assert loader.get_instructions() == "# Child workflow\n"
    assert loader.source_profile == "child"


def test_fragment_empty_annuls_parent(tmp_path):
    parent_dir = write_profile(
        tmp_path / "parent",
        {"020_workflow.md": "# Parent workflow\n"},
    )
    child_dir = write_profile(
        tmp_path / "child",
        {"020_workflow.md": ""},
    )

    loader = InstructionsLoader()
    loader.load_from_profile(parent_dir, make_manifest("parent"))
    loader.load_from_profile(child_dir, make_manifest("child"))

    assert loader.get_instructions() is None
    assert loader.source_profile is None


def test_missing_instructions_dir(tmp_path):
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    loader = InstructionsLoader()

    with pytest.raises(
        FileNotFoundError,
        match="Profile 'missing' must have an 'instructions/' directory",
    ):
        loader.load_from_profile(profile_dir, make_manifest("missing"))


def test_yaml_frontmatter_ignored(tmp_path):
    profile_dir = write_profile(
        tmp_path / "profile",
        {
            "030_date_usage.md": "---\nauthor: TaskMajor Team\nversion: 1.0\ndescription: Date rules\n---\n\n# TaskWarrior Date Expressions\n\nAlways call `resolve_date`.\n",
        },
    )

    loader = InstructionsLoader()
    loader.load_from_profile(profile_dir, make_manifest("profile"))

    instructions = loader.get_instructions()
    assert instructions is not None
    assert "author:" not in instructions
    assert "description:" not in instructions
    assert "# TaskWarrior Date Expressions" in instructions
    assert "Always call `resolve_date`." in instructions


def test_base_has_date_usage():
    base_dir = Path(__file__).resolve().parents[3] / "taskmajor" / "profiles" / "base"

    loader = InstructionsLoader()
    loader.load_from_profile(base_dir, make_manifest("base"))

    instructions = loader.get_instructions()
    assert instructions is not None
    assert "TaskWarrior Date Expressions" in instructions
    assert "resolve_date" in instructions
    assert loader.source_profile == "base"


def test_minimal_inherits_date_usage(tmp_path):
    base_dir = write_profile(
        tmp_path / "base",
        {
            "030_date_usage.md": "# TaskWarrior Date Expressions\n\nAlways call `resolve_date`.\n",
        },
    )
    minimal_dir = write_profile(
        tmp_path / "minimal",
        {
            "010_objective.md": "# Minimal Objective\n",
            "020_workflow.md": "# Minimal Workflow\n",
        },
    )

    loader = InstructionsLoader()
    loader.load_from_profile(base_dir, make_manifest("base"))
    loader.load_from_profile(minimal_dir, make_manifest("minimal"))

    instructions = loader.get_instructions()
    assert instructions is not None
    assert "TaskWarrior Date Expressions" in instructions
    assert "resolve_date" in instructions
    assert loader.source_profile == "minimal"
