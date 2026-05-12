import os
import tempfile
from pathlib import Path

import pytest

from taskmajor.domains.profiles.models import (
    ContextDefinition,
    ProfileManifest,
    PromptDeclaration,
    PromptDefinition,
    ResourceDefinition,
    ReviewConfig,
    UdaDefinition,
)


def test_prompt_definition_full():
    prompt = PromptDefinition(
        name="test",
        content="prompt content",
        source_profile="profileA",
    )
    assert prompt.name == "test"
    assert prompt.content == "prompt content"
    assert prompt.source_profile == "profileA"


def test_resource_definition_with_params():
    res = ResourceDefinition(
        uri="/api/resource",
        name="Resource",
        description="desc",
        backend_function="func",
        backend_params={"x": 1},
    )
    assert res.backend_params == {"x": 1}


def test_uda_definition():
    uda = UdaDefinition(
        name="ticket_id",
        type="string",
        label="Ticket ID",
        values=["A", "B"],
        default="A",
    )
    assert uda.name == "ticket_id"
    assert uda.type == "string"
    assert uda.label == "Ticket ID"
    assert uda.values == ["A", "B"]
    assert uda.default == "A"


def test_context_definition():
    ctx = ContextDefinition(
        name="work",
        read_filter="project:work",
        write_filter="project:work",
    )
    assert ctx.name == "work"
    assert ctx.read_filter == "project:work"
    assert ctx.write_filter == "project:work"


def test_prompt_declaration():
    decl = PromptDeclaration(
        name="code_review",
        file="prompts/code_review.md",
    )
    assert decl.name == "code_review"
    assert decl.file == "prompts/code_review.md"


def test_review_config():
    review = ReviewConfig(
        projects=["Inbox", "Review"],
        default_project="Inbox",
        include_no_project=True,
    )
    assert review.projects == ["Inbox", "Review"]
    assert review.default_project == "Inbox"
    assert review.include_no_project is True


def test_profile_manifest_from_yaml_valid():
    yaml_content = """
name: testprofile
version: 2.0.0
description: Test profile
author: test author
extends: parent
udas:
  - name: ticket_id
    type: string
    label: Ticket ID
contexts:
  - name: work
    read_filter: "project:work"
review:
  projects:
    - Inbox
  default_project: Inbox
  include_no_project: false
resources:
  - uri: test://resource
    name: Test Resource
    description: A test resource
    backend:
      function: query_tasks
      params: {}
prompts:
  - name: test_prompt
    file: prompts/test.md
tools:
  - query_tasks
  - add_task
  - report_error
"""
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".yaml") as tf:
        tf.write(yaml_content)
        tf.flush()
        path = Path(tf.name)
    try:
        manifest = ProfileManifest.from_yaml(path)
        assert manifest.name == "testprofile"
        assert manifest.version == "2.0.0"
        assert manifest.description == "Test profile"
        assert manifest.author == "test author"
        assert manifest.extends == ["parent"]
        assert len(manifest.udas) == 1
        assert isinstance(manifest.udas[0], UdaDefinition)
        assert manifest.udas[0].name == "ticket_id"
        assert manifest.udas[0].type == "string"
        assert len(manifest.contexts) == 1
        assert isinstance(manifest.contexts[0], ContextDefinition)
        assert manifest.contexts[0].name == "work"
        assert isinstance(manifest.review, ReviewConfig)
        assert manifest.review.default_project == "Inbox"
        assert manifest.resources[0]["uri"] == "test://resource"
        assert len(manifest.prompts) == 1
        assert isinstance(manifest.prompts[0], PromptDeclaration)
        assert manifest.prompts[0].name == "test_prompt"
        assert manifest.tools == ["query_tasks", "add_task", "report_error"]
    finally:
        os.unlink(path)


def test_profile_manifest_tools_default_empty():
    """Test that tools defaults to empty list when not specified."""
    yaml_content = """
name: noprofile
version: 1.0.0
"""
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".yaml") as tf:
        tf.write(yaml_content)
        tf.flush()
        path = Path(tf.name)
    try:
        manifest = ProfileManifest.from_yaml(path)
        assert manifest.tools == []
    finally:
        os.unlink(path)


def test_profile_manifest_extends_normalization():
    """Test that extends accepts string or list and normalizes to list."""
    # String extends
    yaml_str = """
name: child
version: 1.0.0
extends: parent
"""
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".yaml") as tf:
        tf.write(yaml_str)
        tf.flush()
        path = Path(tf.name)
    try:
        manifest = ProfileManifest.from_yaml(path)
        assert manifest.extends == ["parent"]
    finally:
        os.unlink(path)

    # List extends
    yaml_list = """
name: child
version: 1.0.0
extends:
  - grandparent
  - parent
"""
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".yaml") as tf:
        tf.write(yaml_list)
        tf.flush()
        path = Path(tf.name)
    try:
        manifest = ProfileManifest.from_yaml(path)
        assert manifest.extends == ["grandparent", "parent"]
    finally:
        os.unlink(path)


def test_profile_manifest_from_yaml_missing_name():
    yaml_content = "version: 1.0.0"
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".yaml") as tf:
        tf.write(yaml_content)
        tf.flush()
        path = Path(tf.name)
    try:
        with pytest.raises(ValueError, match="name.*version"):
            ProfileManifest.from_yaml(path)
    finally:
        os.unlink(path)


def test_profile_manifest_from_yaml_file_not_found():
    path = Path("/tmp/nonexistent_profile_manifest.yaml")
    with pytest.raises(FileNotFoundError):
        ProfileManifest.from_yaml(path)
