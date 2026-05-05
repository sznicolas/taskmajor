"""Unit tests for tools/simulate_profiles.py public API."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make tools/ importable without installing
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from simulate_profiles import (  # noqa: E402
    ProfileContext,
    build_profile_index_data,
    discover_builtin_profiles,
    generate_instructions_content,
    load_profile_context,
    render_profile_report,
)


# ---------------------------------------------------------------------------
# discover_builtin_profiles
# ---------------------------------------------------------------------------

def test_discover_builtin_profiles_returns_known_profiles():
    profiles = discover_builtin_profiles()
    assert isinstance(profiles, list)
    assert len(profiles) >= 1
    assert "base" in profiles
    assert "standard" in profiles


def test_discover_builtin_profiles_sorted():
    profiles = discover_builtin_profiles()
    assert profiles == sorted(profiles)


def test_discover_builtin_profiles_no_hidden_dirs():
    profiles = discover_builtin_profiles()
    for name in profiles:
        assert not name.startswith(".")


# ---------------------------------------------------------------------------
# load_profile_context
# ---------------------------------------------------------------------------

def test_load_profile_context_base():
    ctx = load_profile_context("base")
    assert ctx.profile_name == "base"
    assert any(item["name"] == "base" for item in ctx.chain)
    assert isinstance(ctx.tools_seen, list)
    assert isinstance(ctx.resources, dict)
    assert isinstance(ctx.final_instructions, str)


def test_load_profile_context_standard_has_tools():
    ctx = load_profile_context("standard")
    assert "query_tasks" in ctx.tools_seen
    assert "add_task" in ctx.tools_seen


def test_load_profile_context_standard_has_resources():
    ctx = load_profile_context("standard")
    assert "taskmajor://agenda/today" in ctx.resources


def test_load_profile_context_chain_order():
    ctx = load_profile_context("standard")
    names = [item["name"] for item in ctx.chain]
    assert names.index("base") < names.index("standard")


def test_load_profile_context_productivity_extends_standard():
    ctx = load_profile_context("productivity")
    names = [item["name"] for item in ctx.chain]
    assert "base" in names
    assert "standard" in names
    assert "productivity" in names
    assert names.index("standard") < names.index("productivity")


def test_load_profile_context_project_mgmt_has_udas():
    ctx = load_profile_context("project-mgmt")
    assert "estimate" in ctx.udas
    assert "owner" in ctx.udas
    assert "sprint" in ctx.udas


# ---------------------------------------------------------------------------
# render_profile_report
# ---------------------------------------------------------------------------

def _make_minimal_ctx(**overrides) -> ProfileContext:
    defaults = dict(
        profile_name="test",
        chain=[{"name": "test", "version": "1.0.0", "description": "desc"}],
        manifests=[],
        tools_seen=["add_task", "query_tasks"],
        tool_history={"add_task": ["test"], "query_tasks": ["test"]},
        prompt_defs={},
        udas={},
        uda_source={},
        contexts=[],
        overlaps={},
        resources={},
        final_instructions="Do something.",
        fragments=[],
    )
    defaults.update(overrides)
    return ProfileContext(**defaults)


def test_render_profile_report_contains_profile_name():
    ctx = _make_minimal_ctx()
    report = render_profile_report(ctx)
    assert "# Profile: test" in report


def test_render_profile_report_contains_chain_section():
    ctx = _make_minimal_ctx()
    report = render_profile_report(ctx)
    assert "## Chain:" in report


def test_render_profile_report_contains_tools():
    ctx = _make_minimal_ctx()
    report = render_profile_report(ctx)
    assert "add_task" in report
    assert "query_tasks" in report


def test_render_profile_report_resources_section():
    ctx = _make_minimal_ctx()
    report = render_profile_report(ctx)
    assert "## Resources:" in report


def test_render_profile_report_invalid_format():
    ctx = _make_minimal_ctx()
    with pytest.raises(ValueError, match="Only 'markdown' format"):
        render_profile_report(ctx, format="html")


def test_render_profile_report_no_tools():
    ctx = _make_minimal_ctx(tools_seen=[], tool_history={})
    report = render_profile_report(ctx)
    assert "- None" in report


def test_render_profile_report_real_standard():
    ctx = load_profile_context("standard")
    report = render_profile_report(ctx)
    assert "taskmajor://agenda/today" in report
    assert "## Tools" in report


# ---------------------------------------------------------------------------
# generate_instructions_content
# ---------------------------------------------------------------------------

def test_generate_instructions_content_returns_instructions():
    ctx = _make_minimal_ctx(final_instructions="Use this tool wisely.")
    content = generate_instructions_content(ctx, include_debug=False)
    assert "Use this tool wisely." in content


def test_generate_instructions_content_no_instructions():
    ctx = _make_minimal_ctx(final_instructions="")
    content = generate_instructions_content(ctx, include_debug=False)
    assert "_(no instructions)_" in content


def test_generate_instructions_content_debug_fragments():
    ctx = _make_minimal_ctx(
        final_instructions="Main text.",
        fragments=[("base/instructions/010_objective.md", "Fragment content here.")],
    )
    content = generate_instructions_content(ctx, include_debug=True)
    assert "🔍 Debug fragments" in content
    assert "base/instructions/010_objective.md" in content
    assert "Fragment content here." in content


def test_generate_instructions_content_skip_debug():
    ctx = _make_minimal_ctx(
        final_instructions="Main text.",
        fragments=[("base/instructions/010_objective.md", "Fragment content here.")],
    )
    content = generate_instructions_content(ctx, include_debug=False)
    assert "🔍 Debug fragments" not in content
    assert "Fragment content here." not in content


# ---------------------------------------------------------------------------
# build_profile_index_data
# ---------------------------------------------------------------------------

def test_build_profile_index_data_empty():
    result = build_profile_index_data([])
    assert result == {}


def test_build_profile_index_data_single():
    ctx = _make_minimal_ctx(
        profile_name="base",
        chain=[{"name": "base", "version": "1.0.0", "description": ""}],
    )
    result = build_profile_index_data([ctx])
    assert result == {"base": ["base"]}


def test_build_profile_index_data_chain():
    ctx = _make_minimal_ctx(
        profile_name="standard",
        chain=[
            {"name": "base", "version": "1.0.0", "description": ""},
            {"name": "standard", "version": "2.0.0", "description": ""},
        ],
    )
    result = build_profile_index_data([ctx])
    assert result["standard"] == ["base", "standard"]


def test_build_profile_index_data_multiple_profiles():
    ctxs = [load_profile_context(p) for p in ["base", "standard"]]
    result = build_profile_index_data(ctxs)
    assert "base" in result
    assert "standard" in result
    assert result["standard"] == ["base", "standard"]
