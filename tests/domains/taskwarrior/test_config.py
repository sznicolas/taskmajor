from __future__ import annotations

from pathlib import Path

from taskmajor.domains.taskwarrior import TaskMajorConfig


def test_default_config_values():
    """Test all default configuration values are set correctly."""
    config = TaskMajorConfig()

    # Server defaults
    assert config.server_host == "localhost"
    assert config.server_port == 8888

    # Config defaults
    assert config.profile == "standard"
    # Default profiles_dir is the project-local profiles directory
    assert config.profiles_dir.endswith("taskmajor/profiles")

    # Log defaults
    assert config.log_level == "DEBUG"
    assert config.log_format == "text"


def test_agent_errors_path_validation():
    """Test agent error path is in home directory with correct filename."""
    config = TaskMajorConfig()
    home = str(Path.home())

    assert not config.agent_errors_path.startswith("/tmp")
    assert config.agent_errors_path.startswith(home)
    assert config.agent_errors_path.endswith("agent_errors.jsonl")
