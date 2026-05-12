#!/usr/bin/env python3
"""Pure utilities for inspecting TaskMajor profiles and rendering reports.

This module provides pure, testable functions and does NOT perform any file I/O.
Orchestrators (e.g. tools/generate_profile_docs.py) should import and call
these functions and handle writing outputs to disk.

Public API:
- discover_builtin_profiles() -> list[str]
- load_profile_context(profile_name: str) -> ProfileContext
- render_profile_report(ctx: ProfileContext, format: str = "markdown") -> str
- generate_instructions_content(ctx: ProfileContext, include_debug: bool = True) -> str
- build_profile_index_data(ctxs: list[ProfileContext]) -> dict

A small CLI is provided for convenience; it prints rendered Markdown to stdout.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from taskmajor.domains.profiles import ProfileManager
from taskmajor.domains.taskwarrior.config import TaskMajorConfig


class MockTaskService:
    def query_tasks(self, **_: object) -> list[object]:
        return []

    def get_tasks_by_scope(self, **_: object) -> dict[str, object]:
        return {}

    def get_stats(self, **_: object) -> dict[str, object]:
        return {}

    def next_task(self, **_: object) -> object | None:
        return None

    def get_metadata(self, **_: object) -> dict[str, object]:
        return {}

    def get_projects(self, **_: object) -> list[object]:
        return []

    def get_tags(self, **_: object) -> list[object]:
        return []

    def get_udas(self, **_: object) -> list[object]:
        return []

    def add_task(self, **_: object) -> dict[str, object]:
        return {}

    def update_task(self, **_: object) -> bool:
        return True

    def delete_task(self, **_: object) -> bool:
        return True

    def get_task(self, **_: object) -> dict[str, object]:
        return {}


@dataclass
class ProfileContext:
    profile_name: str
    chain: list[dict[str, str]]
    manifests: list[Any]
    tools_seen: list[str]
    tool_history: dict[str, list[str]]
    prompt_defs: dict[str, Any]
    udas: dict[str, Any]
    uda_source: dict[str, str]
    contexts: list[dict[str, str]]
    overlaps: dict[str, list[str]]
    resources: dict[str, Any]
    final_instructions: str
    fragments: list[tuple[str, str]]


def discover_builtin_profiles() -> list[str]:
    """Discover built-in profile directories by looking for manifest.yaml."""
    profiles_dir = Path(__file__).parent.parent / "taskmajor" / "profiles"
    if not profiles_dir.exists():
        return []
    result: list[str] = []
    for p in sorted(profiles_dir.iterdir()):
        if p.is_dir() and not p.name.startswith(".") and (p / "manifest.yaml").exists():
            result.append(p.name)
    return result


def load_profile_context(profile_name: str) -> ProfileContext:
    """Load a profile via ProfileManager and collect reportable pieces.

    This function performs only in-memory operations and returns a ProfileContext.
    """
    pm = ProfileManager(TaskMajorConfig(profile=profile_name))
    pm.set_task_service(MockTaskService())
    loaded = pm.load_all()
    manifests = pm.get_loaded_profiles()
    resource_mapper = pm.get_resource_mapper()
    prompt_loader = pm.get_prompt_loader()
    instructions_loader = pm.get_instructions_loader()

    # Tools
    tools_seen: list[str] = []
    tool_history: dict[str, list[str]] = {}
    for manifest in manifests:
        for t in getattr(manifest, "tools", []) or []:
            if t not in tools_seen:
                tools_seen.append(t)
            tool_history.setdefault(t, []).append(manifest.name)

    # UDAs
    udas: dict[str, Any] = {}
    uda_source: dict[str, str] = {}
    for manifest in manifests:
        for uda in getattr(manifest, "udas", []) or []:
            name = getattr(uda, "name", None)
            if name and name not in udas:
                udas[name] = uda
                uda_source[name] = manifest.name

    # Prompts
    prompt_names = prompt_loader.list_prompts()
    prompt_defs = {name: prompt_loader.get_prompt_definition(name) for name in prompt_names}

    # Contexts
    contexts: list[dict[str, str]] = []
    for m in manifests:
        for ctx in getattr(m, "contexts", []) or []:
            contexts.append({"name": getattr(ctx, "name", ""), "profile": m.name})

    # Resources & overlaps
    owners: dict[str, list[str]] = {}
    resource_source: dict[str, str] = {}
    for m in manifests:
        for resource in getattr(m, "resources", []) or []:
            uri = resource.get("uri") if isinstance(resource, dict) else None
            if isinstance(uri, str):
                owners.setdefault(uri, []).append(m.name)
                if uri not in resource_source:
                    resource_source[uri] = m.name
    overlaps = {uri: names for uri, names in owners.items() if len(names) > 1}

    # Resource definitions mapping
    resource_defs: dict[str, Any] = {}
    try:
        for uri, definition in resource_mapper.get_all_definitions().items():
            resource_defs[uri] = definition
    except Exception:
        resource_defs = {}

    # Chain
    desc_by_profile = {m.name: str(getattr(m, "description", "") or "") for m in manifests}
    chain: list[dict[str, str]] = []
    for obj in loaded:
        name = str(getattr(obj, "name", "") or "")
        version = str(getattr(obj, "version", "") or "")
        desc = desc_by_profile.get(name, "")
        chain.append({"name": name, "version": version, "description": desc})

    # Instructions + fragments
    final_instructions = instructions_loader.get_instructions() or ""
    fragments: list[tuple[str, str]] = []
    try:
        frag_items = sorted(
            getattr(instructions_loader, "_fragments", {}).items(), key=lambda it: it[0]
        )
        for fname, frag in frag_items:
            profile_name_frag = getattr(frag, "profile_name", "")
            filepath = f"{profile_name_frag}/instructions/{fname}" if profile_name_frag else fname
            fragments.append((filepath, getattr(frag, "content", "") or ""))
    except Exception:
        fragments = []

    return ProfileContext(
        profile_name=profile_name,
        chain=chain,
        manifests=manifests,
        tools_seen=tools_seen,
        tool_history=tool_history,
        prompt_defs=prompt_defs,
        udas=udas,
        uda_source=uda_source,
        contexts=contexts,
        overlaps=overlaps,
        resources=resource_defs,
        final_instructions=final_instructions,
        fragments=fragments,
    )


def _md_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines: list[str] = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for r in rows:
        lines.append("| " + " | ".join(str(c) for c in r) + " |")
    return lines


def render_profile_report(ctx: ProfileContext, format: str = "markdown") -> str:
    """Render a profile report. Only 'markdown' is supported for now.

    Returns a Markdown string describing the profile composition.
    """
    if format != "markdown":
        raise ValueError("Only 'markdown' format is supported by render_profile_report")

    md: list[str] = []
    md.append(f"# Profile: {ctx.profile_name}")
    md.append("")
    md.append("## Chain:")
    md.append("")
    for item in ctx.chain:
        if item.get("version"):
            md.append(f"### {item['name']} ({item['version']})")
        else:
            md.append(f"### {item['name']}")
        if item.get("description"):
            md.append(item["description"])
        md.append("")

    md.append("**Instructions sources:** (see Instructions section)")
    md.append("")

    # Tools
    md.append("## Tools")
    tool_rows = [[t, " -> ".join(ctx.tool_history.get(t, []))] for t in ctx.tools_seen]
    if tool_rows:
        md.extend(_md_table(["Tool", "Declared in (chain)"], tool_rows))
    else:
        md.append("- None")
    md.append("")

    # Prompts
    md.append("## Prompts")
    prompt_rows = [
        [name, getattr(defn, "source_profile", "")] for name, defn in ctx.prompt_defs.items()
    ]
    if prompt_rows:
        md.extend(_md_table(["name", "source_profile"], prompt_rows))
    else:
        md.append("- None")
    md.append("")

    # UDAs
    md.append("## UDAs")
    uda_rows = []
    for name, uda in ctx.udas.items():
        extras = {
            k: v for k, v in getattr(uda, "__dict__", {}).items() if k not in ("name", "type")
        }
        source = ctx.uda_source.get(name, "")
        uda_rows.append(
            [name, getattr(uda, "type", ""), source, json.dumps(extras, sort_keys=True)]
        )
    if uda_rows:
        md.extend(_md_table(["name", "type", "defined_in", "extras"], uda_rows))
    else:
        md.append("- None")
    md.append("")

    # Contexts
    md.append("## Contexts")
    ctx_rows = [[c["name"], c["profile"]] for c in ctx.contexts]
    if ctx_rows:
        md.extend(_md_table(["name", "defined_in"], ctx_rows))
    else:
        md.append("- None")
    md.append("")

    # URI overlaps
    if ctx.overlaps:
        md.append("## URI overlaps")
        for uri, names in ctx.overlaps.items():
            md.append(f"- `{uri}` : {', '.join(names)}")
        md.append("")

    # Resources
    md.append("## Resources:")
    res_rows: list[list[str]] = []
    for uri, definition in (ctx.resources or {}).items():
        params = json.dumps(getattr(definition, "backend_params", {}) or {}, sort_keys=True)
        src = getattr(definition, "name", "") if definition is not None else ""
        res_rows.append(
            [
                uri,
                getattr(definition, "backend_function", ""),
                params,
                src,
                (ctx.overlaps.get(uri, [""])[0] if uri in ctx.overlaps else ""),
            ]
        )
    if res_rows:
        md.extend(_md_table(["URI", "backend.function", "params", "name", "source"], res_rows))
    else:
        md.append("- None")
    md.append("")

    return "\n".join(md).rstrip() + "\n"


def generate_instructions_content(ctx: ProfileContext, include_debug: bool = True) -> str:
    """Return the instructions content (without an auto-generated file header).

    The orchestrator should prepend a standard AUTO-GENERATED header and write the
    final file. This function focuses on instruction text + inline debug fragments.
    """
    body_lines: list[str] = []
    body_lines.append((ctx.final_instructions or "_(no instructions)_").rstrip())
    body_lines.append("")

    if include_debug and ctx.fragments:
        body_lines.append("---")
        body_lines.append("## 🔍 Debug fragments (not sent via MCP)")
        body_lines.append("")
        for path, content in ctx.fragments:
            body_lines.append(f"### 🔍 {path}")
            for ln in (content or "").splitlines():
                body_lines.append(f"🔍 {ln}")
            body_lines.append("")

    return "\n".join(body_lines).rstrip() + "\n"


def build_profile_index_data(ctxs: list[ProfileContext]) -> dict[str, list[str]]:
    """Return a mapping profile_name -> chain (list of profile names in loaded order).

    This is convenient for building Mermaid graphs and adjacency maps.
    """
    result: dict[str, list[str]] = {}
    for ctx in ctxs:
        result[ctx.profile_name] = [item["name"] for item in ctx.chain if item.get("name")]
    return result


# Lightweight CLI to render markdown summary (no file writes)
if __name__ == "__main__":
    import argparse
    import sys

    ap = argparse.ArgumentParser(description="Render TaskMajor profile report (Markdown) to stdout")
    ap.add_argument(
        "-p",
        "--profiles",
        dest="profiles",
        default=None,
        help="Comma-separated profile names (default: all built-in profiles)",
    )
    ap.add_argument(
        "-i",
        "--instructions",
        dest="instructions",
        action="store_true",
        help="Also print instructions",
    )
    args = ap.parse_args()

    if args.profiles:
        profiles = [p.strip() for p in args.profiles.split(",") if p.strip()]
    else:
        profiles = discover_builtin_profiles()

    if not profiles:
        print("No profiles found", file=sys.stderr)
        raise SystemExit(2)

    for profile in profiles:
        ctx = load_profile_context(profile)
        print(render_profile_report(ctx, format="markdown"))
        if args.instructions:
            print("\n---\n")
            print(generate_instructions_content(ctx, include_debug=True))
