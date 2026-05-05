from __future__ import annotations

import pytest
import yaml
from pydantic import ValidationError

from taskmajor.domains.taskwarrior import TaskMajorConfig


def test_taskmajor_config_profile_defaults_to_default():
    config = TaskMajorConfig()

    assert config.profile == "standard"


def test_taskmajor_config_profiles_dir_default():
    config = TaskMajorConfig()

    assert config.profiles_dir.endswith("taskmajor/profiles")


def test_taskmajor_config_loads_profile_key(tmp_path):
    config_yaml = {
        "profiles_dir": str(tmp_path / "profiles"),
        "profile": "alpha",
    }
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(config_yaml, sort_keys=False), encoding="utf-8")

    config = TaskMajorConfig.load(tmp_path)

    assert config.profiles_dir == str(tmp_path / "profiles")
    assert config.profile == "alpha"


def test_unknown_profile_keys_are_ignored():
    # New single-profile model ignores profile schema; ensure loading unknown top-level keys errors via pydantic
    with pytest.raises(ValidationError):
        TaskMajorConfig.model_validate({"profile": "alpha", "unknown": "value"})
