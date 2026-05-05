import logging
from pathlib import Path

import yaml

from taskmajor.domains.profiles.models import ProfileManifest
from taskmajor.domains.profiles.resource_mapper import ResourceMapper


class MinimalTaskService:
    def get_tasks_by_scope(self, scope=None, filters=None):
        return []

    def query_tasks(self, filter=None):
        return []


def _write_manifest(dir_path: Path, name: str, resources):
    manifest = {"name": name, "version": "1.0.0", "resources": resources}
    (dir_path / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")


def test_child_override_wins(tmp_path, caplog):
    parent_dir = tmp_path / "parent"
    parent_dir.mkdir()
    child_dir = tmp_path / "child"
    child_dir.mkdir()

    parent_resources = [
        {
            "uri": "test://foo",
            "name": "Parent resource",
            "description": "parent",
            "backend": {
                "function": "get_tasks_by_scope",
                "params": {"scope": "project", "filters": {"status": "pending"}},
            },
        }
    ]

    child_resources = [
        {
            "uri": "test://foo",
            "name": "Child resource",
            "description": "child",
            "backend": {"function": "query_tasks", "params": {"filter": "status:pending"}},
        }
    ]

    _write_manifest(parent_dir, "parent", parent_resources)
    _write_manifest(child_dir, "child", child_resources)

    rm = ResourceMapper(task_service=MinimalTaskService())

    caplog.set_level(logging.INFO)

    # load parent
    parent_manifest = ProfileManifest.from_yaml(parent_dir / "manifest.yaml")
    rm.load_from_profile(parent_dir, parent_manifest)

    # load child - should override without raising
    child_manifest = ProfileManifest.from_yaml(child_dir / "manifest.yaml")
    rm.load_from_profile(child_dir, child_manifest)

    defs = rm.get_all_definitions()
    assert "test://foo" in defs
    assert defs["test://foo"].backend_function == "query_tasks"

    # verify info log emitted for override
    found = False
    for rec in caplog.records:
        if rec.levelno == logging.INFO and "overridden by profile" in rec.getMessage():
            assert "test://foo" in rec.getMessage()
            assert "child" in rec.getMessage()
            found = True
            break
    assert found, "Expected info log about overridden resource"
