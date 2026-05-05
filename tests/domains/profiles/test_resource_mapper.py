from unittest.mock import Mock

import pytest
import yaml

from taskmajor.domains.profiles.models import ProfileManifest
from taskmajor.domains.profiles.resource_mapper import ResourceMapper


class DummyTaskService:
    def get_stats(self, **kwargs):
        return {"ok": True, "kwargs": kwargs}

    def query_tasks(self, **kwargs):
        raise RuntimeError("boom")


def make_manifest(resources=None):
    return ProfileManifest(
        name="profile",
        version="1.0.0",
        resources=resources or [],
    )


def test_load_from_profile_manifest_only(tmp_path):
    manifest = make_manifest(resources=[{
        "uri": "/r1",
        "name": "R1",
        "description": "desc",
        "backend": {"function": "query_tasks"},
    }])
    rm = ResourceMapper(DummyTaskService())
    rm.load_from_profile(tmp_path, manifest)
    assert "/r1" in rm._resources
    assert rm._resources["/r1"].name == "R1"
    assert rm.list_resources() == ["/r1"]
    assert rm.get_resource("/r1").name == "R1"


def test_load_from_profile_yaml_overrides_manifest(tmp_path):
    manifest = make_manifest(resources=[{
        "uri": "/r1",
        "name": "R1",
        "description": "desc",
        "backend": {"function": "query_tasks"},
    }])
    yaml_resources = [{
        "uri": "/r1",
        "name": "R1Y",
        "description": "desc2",
        "backend": {"function": "get_stats"},
    }]
    (tmp_path / "resources.yaml").write_text(yaml.dump(yaml_resources), encoding="utf-8")
    rm = ResourceMapper(DummyTaskService())
    rm.load_from_profile(tmp_path, manifest)
    assert "/r1" in rm._resources
    assert rm._resources["/r1"].name == "R1Y"
    assert rm._resources["/r1"].backend_function == "get_stats"


def test_create_handler_returns_json_payload(tmp_path):
    manifest = make_manifest(resources=[{
        "uri": "/r1",
        "name": "R1",
        "description": "desc",
        "backend": {"function": "get_stats", "params": {"project": "Inbox"}},
    }])
    rm = ResourceMapper(DummyTaskService())
    rm.load_from_profile(tmp_path, manifest)

    payload = rm.create_handler("/r1")()

    assert '"ok": true' in payload
    assert '"project": "Inbox"' in payload


def test_create_handler_serializes_backend_error(tmp_path):
    manifest = make_manifest(resources=[{
        "uri": "/r1",
        "name": "R1",
        "description": "desc",
        "backend": {"function": "query_tasks"},
    }])
    rm = ResourceMapper(DummyTaskService())
    rm.load_from_profile(tmp_path, manifest)

    payload = rm.create_handler("/r1")()

    assert '"error": "boom"' in payload


def test_load_from_profile_invalid_backend(tmp_path):
    manifest = make_manifest(resources=[{
        "uri": "/r1",
        "name": "R1",
        "description": "desc",
        "backend": {"function": "not_allowed"},
    }])
    rm = ResourceMapper(DummyTaskService())
    with pytest.raises(ValueError):
        rm.load_from_profile(tmp_path, manifest)


def test_load_from_profile_duplicate_uri(tmp_path):
    manifest = make_manifest(resources=[
        {"uri": "/r1", "name": "R1", "description": "desc", "backend": {"function": "query_tasks"}},
        {"uri": "/r1", "name": "R2", "description": "desc2", "backend": {"function": "get_stats"}}
    ])
    rm = ResourceMapper(DummyTaskService())
    with pytest.raises(ValueError):
        rm.load_from_profile(tmp_path, manifest)


def test_load_from_profile_yaml_not_list(tmp_path):
    (tmp_path / "resources.yaml").write_text("{}", encoding="utf-8")
    manifest = make_manifest()
    rm = ResourceMapper(DummyTaskService())
    with pytest.raises(ValueError):
        rm.load_from_profile(tmp_path, manifest)


# New tests for backend parameter validation

def test_backend_parameter_validation_valid(tmp_path):
    def get_stats(filters=None):
        return {"ok": True}

    ts = Mock()
    ts.get_stats = get_stats

    manifest = make_manifest(resources=[{
        "uri": "/r1",
        "name": "R1",
        "description": "desc",
        "backend": {"function": "get_stats", "params": {"filters": {"status": "pending"}}},
    }])

    rm = ResourceMapper(ts)
    # Should not raise
    rm.load_from_profile(tmp_path, manifest)
    assert "/r1" in rm.list_resources()


def test_backend_parameter_validation_invalid(tmp_path):
    def get_stats(filters=None):
        return {"ok": True}

    ts = Mock()
    ts.get_stats = get_stats

    manifest = make_manifest(resources=[{
        "uri": "/r1",
        "name": "R1",
        "description": "desc",
        "backend": {"function": "get_stats", "params": {"type": "something"}},
    }])

    rm = ResourceMapper(ts)
    with pytest.raises(ValueError) as exc:
        rm.load_from_profile(tmp_path, manifest)

    msg = str(exc.value)
    assert "does not accept parameter" in msg
    assert "type" in msg


def test_resource_merge_params(tmp_path):
    parent = make_manifest(resources=[{
        "uri": "test://foo",
        "name": "parent-foo",
        "description": "parent",
        "backend": {"function": "get_stats", "params": {"filter": "status:pending", "sort": ["due"], "limit": 50}},
    }])
    child = make_manifest(resources=[{
        "uri": "test://foo",
        "name": "child-foo",
        "description": "child",
        "merge": True,
        "backend": {"function": "get_stats", "params": {"filter": "status:pending project:Inbox"}},
    }])
    rm = ResourceMapper(DummyTaskService())
    rm.load_from_profile(tmp_path, parent)
    rm.load_from_profile(tmp_path, child)
    res = rm.get_resource("test://foo")
    assert res is not None
    assert res.backend_params == {"filter": "status:pending project:Inbox", "sort": ["due"], "limit": 50}


def test_resource_merge_list_replacement(tmp_path):
    parent = make_manifest(resources=[{
        "uri": "test://foo2",
        "name": "parent-foo2",
        "description": "parent2",
        "backend": {"function": "get_stats", "params": {"sort": ["due", "priority"]}},
    }])
    child = make_manifest(resources=[{
        "uri": "test://foo2",
        "merge": True,
        "backend": {"function": "get_stats", "params": {"sort": ["-priority"]}},
    }])
    rm = ResourceMapper(DummyTaskService())
    rm.load_from_profile(tmp_path, parent)
    rm.load_from_profile(tmp_path, child)
    res = rm.get_resource("test://foo2")
    assert res is not None
    assert res.backend_params.get("sort") == ["-priority"]


def test_resource_override_without_merge(tmp_path):
    parent = make_manifest(resources=[{
        "uri": "test://bar",
        "name": "parent-bar",
        "description": "parent",
        "backend": {"function": "get_stats", "params": {"filter": "A", "sort": ["due"]}},
    }])
    child = make_manifest(resources=[{
        "uri": "test://bar",
        "name": "child-bar",
        "description": "child",
        "backend": {"function": "get_stats", "params": {"filter": "B"}},
    }])
    rm = ResourceMapper(DummyTaskService())
    rm.load_from_profile(tmp_path, parent)
    rm.load_from_profile(tmp_path, child)
    res = rm.get_resource("test://bar")
    assert res is not None
    assert res.backend_params == {"filter": "B"}
