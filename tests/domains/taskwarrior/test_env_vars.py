from __future__ import annotations


def test_default_config_loads_from_app_config(tmp_path, monkeypatch):
    """TaskMajor should load config.yaml from ./app/config by default."""
    app_config = tmp_path / "app" / "config"
    app_config.mkdir(parents=True)
    (app_config / "config.yaml").write_text(
        "server_port: 9999\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    from taskmajor.domains.taskwarrior.config import TaskMajorConfig

    cfg = TaskMajorConfig.load()

    assert cfg.server_port == 9999
