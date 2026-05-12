#!/usr/bin/env python3
"""Orchestrator to generate profile docs using simulate_profiles pure API.

 Writes:
  - docs/user-guides/profiles/reference/{profile}.md
  - docs/user-guides/profiles/reference/README.md

Updates mkdocs.yml nav and attempts to ensure mermaid plugin present.
Run this before docs build so generated profile pages stay in sync.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent.resolve()
REPO_ROOT = HERE.parent
DEFAULT_OUT = Path("docs/user-guides/profiles/reference/")


def load_simulator_module():
    sim_path = HERE / "simulate_profiles.py"
    if not sim_path.exists():
        raise FileNotFoundError(f"simulate_profiles.py not found at {sim_path}")
    spec = importlib.util.spec_from_file_location("simulate_profiles", str(sim_path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore
    return module


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    print(f"Wrote: {path}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate profile reference docs.")
    parser.add_argument(
        "--no-update-mkdocs",
        action="store_true",
        help="Skip rewriting mkdocs.yml during generation.",
    )
    return parser.parse_args(argv)


def cleanup_obsolete_profile_dirs(
    outdir: Path,
    current_profiles: list[str],
    safe_names: set[str] | None = None,
    dry_run: bool = False,
) -> list[str]:
    import shutil

    if safe_names is None:
        safe_names = {"assets", "examples"}
    if not outdir.exists() or not outdir.is_dir():
        raise RuntimeError(f"Output directory {outdir} does not exist or is not a directory")
    existing_dirs = [d for d in outdir.iterdir() if d.is_dir()]
    to_delete: list[Path] = []
    current_set = set(current_profiles)
    for d in existing_dirs:
        if d.name in current_set or d.name in safe_names:
            continue
        # safety: ensure the dir is inside outdir
        try:
            d.resolve().relative_to(outdir.resolve())
        except Exception as exc:
            raise RuntimeError(f"Unsafe path detected: {d}") from exc
        to_delete.append(d)
    if not to_delete:
        return []
    for d in to_delete:
        if dry_run:
            print(f"[CLEANUP] Would remove profile: {d.name}")
            continue
        try:
            shutil.rmtree(d)
            print(f"[CLEANUP] Removed profile: {d.name}")
        except Exception as exc:
            raise RuntimeError(f"Failed to remove {d}: {exc}") from exc
    return [d.name for d in to_delete]


def atomic_write(path: Path, content: str) -> None:
    tmp = path.parent / (path.name + ".tmp")
    ensure_dir(path.parent)
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)
    print(f"Wrote: {path}")


def build_edges_from_chains(chains: dict[str, list[str]]) -> set[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for _profile, chain in chains.items():
        for i in range(len(chain) - 1):
            parent = chain[i]
            child = chain[i + 1]
            if parent and child:
                edges.add((parent, child))
    return edges


def build_children_map(edges: set[tuple[str, str]]) -> dict[str, list[str]]:
    children: dict[str, list[str]] = {}
    nodes: set[str] = set()
    for a, b in edges:
        nodes.add(a)
        nodes.add(b)
        children.setdefault(a, []).append(b)
    for k in list(children.keys()):
        children[k] = sorted(set(children[k]))
    return children


def write_index_md(outdir: Path, profiles: list[str], chains: dict[str, list[str]]) -> None:
    edges = build_edges_from_chains(chains)
    children = build_children_map(edges)

    nodes = set(profiles)
    for a, b in edges:
        nodes.add(a)
        nodes.add(b)

    parents: dict[str, list[str]] = defaultdict(list)
    for a, b in edges:
        parents[b].append(a)

    roots = sorted([n for n in nodes if not parents.get(n)])

    def node_id(name: str) -> str:
        return "".join(c if c.isalnum() else "_" for c in name)

    mermaid_lines: list[str] = ["```mermaid", "flowchart TD"]
    for a, b in sorted(edges):
        mermaid_lines.append(f"  {node_id(a)}[{a}] --> {node_id(b)}[{b}]")
    mermaid_lines.append("```")

    def render_node(name: str, seen: set[str], level: int = 0) -> list[str]:
        if name in seen:
            return ["  " * level + f"- [{name}]({name}/README.md)"]
        seen.add(name)
        lines = ["  " * level + f"- [{name}]({name}/README.md)"]
        for child in sorted(children.get(name, [])):
            lines.extend(render_node(child, seen, level + 1))
        return lines

    list_lines: list[str] = []
    seen: set[str] = set()
    for r in roots:
        list_lines.extend(render_node(r, seen))

    for n in sorted(nodes):
        if n not in seen:
            list_lines.extend(render_node(n, seen))

    header = (
        "<!-- AUTO-GENERATED - Do not edit manually -->\n\n"
        "> **AUTO-GENERATED - Do not edit manually**\n\n"
        f"Generated: {datetime.now().isoformat()}\n\n---\n\n"
    )

    body_lines: list[str] = [
        header,
        "# Profiles index",
        "",
        "This page shows profile inheritance and links to individual profile pages.",
        "",
        "## Graph",
        "",
    ]
    body_lines.extend(mermaid_lines)
    body_lines.append("")
    body_lines.append("## Profiles")
    body_lines.append("")
    body_lines.extend(list_lines)

    write_text(outdir / "README.md", "\n".join(body_lines).rstrip() + "\n")


def update_mkdocs_configuration(
    mkdocs_path: Path, profiles: list[str], ensure_mermaid: bool = True
) -> None:
    """
    Safely update mkdocs.yml to ensure the mermaid2 plugin is present and
    to insert or update a `User Guides -> Profiles` navigation section.

    Strategy:
    - Use ruamel.yaml when available to preserve comments and formatting.
    - Fall back to PyYAML (yaml) when ruamel is not installed (comments may be lost).
    - Create a timestamped backup before writing and validate by reloading the file.
    """
    import shutil
    from datetime import datetime

    # Load with ruamel if available, else with PyYAML
    yaml_backend: str
    try:
        from ruamel.yaml import YAML

        yaml = YAML()
        data = yaml.load(mkdocs_path)
        yaml_backend = "ruamel"
    except Exception:
        try:
            import yaml as pyyaml

            content = mkdocs_path.read_text(encoding="utf-8")
            data = pyyaml.safe_load(content) or {}
            yaml_backend = "pyyaml"
        except Exception as exc:  # pragma: no cover - environment dependent
            raise RuntimeError("ruamel.yaml or PyYAML is required to update mkdocs.yml") from exc

    if data is None:
        data = {}

    # Ensure plugins contains mermaid2
    if ensure_mermaid:
        plugins = data.get("plugins")
        if plugins is None:
            data["plugins"] = []
            plugins = data["plugins"]

        has_mermaid = False
        for p in list(plugins):
            # entry can be a scalar (str) or a mapping (dict)
            if isinstance(p, str) and p == "mermaid2":
                has_mermaid = True
                break
            if isinstance(p, dict) and "mermaid2" in p:
                has_mermaid = True
                break
        if not has_mermaid:
            plugins.append("mermaid2")

    # Ensure nav exists and is a list
    nav = data.get("nav")
    if nav is None or not isinstance(nav, list):
        data["nav"] = []
        nav = data["nav"]

    # Build the Profiles block to insert
    ref_items: list[dict] = []
    for name in profiles:
        title = name.replace("-", " ").title()
        ref_items.append(
            {
                title: [
                    {"README": f"user-guides/profiles/reference/{name}/README.md"},
                    {"Debug": f"user-guides/profiles/reference/{name}/instructions/debug.md"},
                ]
            }
        )

    profiles_block = {
        "Profiles": [
            {"Index": "user-guides/profiles/reference/index.md"},
            {"Reference": ref_items},
        ]
    }

    # Locate existing 'User Guides' entry in nav
    user_idx = None
    for idx, entry in enumerate(nav):
        if isinstance(entry, dict) and "User Guides" in entry:
            user_idx = idx
            break

    if user_idx is None:
        # Insert before Changelog if found, else append
        changelog_idx = None
        for idx, entry in enumerate(nav):
            if isinstance(entry, dict) and "Changelog" in entry:
                changelog_idx = idx
                break
        if changelog_idx is None:
            nav.append({"User Guides": [profiles_block]})
        else:
            nav.insert(changelog_idx, {"User Guides": [profiles_block]})
    else:
        user_val = nav[user_idx]["User Guides"]
        if not isinstance(user_val, list):
            user_val = [user_val]
            nav[user_idx]["User Guides"] = user_val
        # Replace existing Profiles block or append
        replaced = False
        for i, sub in enumerate(user_val):
            if isinstance(sub, dict) and "Profiles" in sub:
                user_val[i] = profiles_block
                replaced = True
                break
        if not replaced:
            user_val.append(profiles_block)

    # Backup original mkdocs.yml
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    backup = mkdocs_path.parent / f"{mkdocs_path.name}.bak.{ts}"
    shutil.copy2(mkdocs_path, backup)

    # Write and validate
    try:
        if yaml_backend == "ruamel":
            # try to preserve indentation style
            yaml.indent(mapping=2, sequence=4, offset=2)
            with mkdocs_path.open("w", encoding="utf-8") as f:
                yaml.dump(data, f)
            # validate by reloading
            yaml.load(mkdocs_path)
        else:
            import yaml as pyyaml

            with mkdocs_path.open("w", encoding="utf-8") as f:
                pyyaml.safe_dump(data, f, sort_keys=False)
            # validate by reloading
            pyyaml.safe_load(mkdocs_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - error path
        # restore backup on error
        shutil.copy2(backup, mkdocs_path)
        raise RuntimeError(
            f"Failed to update mkdocs.yml; restored backup at {backup}. Error: {exc}"
        ) from exc

    print(f"Updated mkdocs.yml using {yaml_backend}; backup at {backup}")


def build_profile_doc_artifacts(
    sim, ctx, *, generated_at: str | None = None, regen_cmd: str | None = None
) -> dict[str, str]:
    """Build README.md and instructions/debug.md for a profile using simulate_profiles APIs.

    sim: the simulate_profiles module object
    ctx: ProfileContext from sim.load_profile_context
    Returns mapping relative path -> content
    """
    if generated_at is None:
        generated_at = datetime.now().isoformat()
    if regen_cmd is None:
        regen_cmd = "python tools/generate_profile_docs.py"

    report_md = sim.render_profile_report(ctx)
    instr_md = sim.generate_instructions_content(ctx, include_debug=True)

    lines = instr_md.splitlines()
    non_debug_lines = [ln for ln in lines if not ln.strip().startswith("🔍")]
    debug_lines = [ln for ln in lines if ln.strip().startswith("🔍")]

    # preserve the visual marker. No cleaning of debug lines is performed.
    non_debug_md = "\n".join(non_debug_lines).strip()
    debug_md = "\n".join(debug_lines).strip()

    profile_header = "<!-- AUTO-GENERATED - Do not edit manually -->\n\n"
    profile_header += "> **AUTO-GENERATED - Do not edit manually**\n\n"
    profile_header += f"Generated: {generated_at}  \n"
    profile_header += f"Regenerate: `{regen_cmd}`\n\n"
    profile_header += "---\n\n"

    nav_link = "[← Back to profile overview](../../profile-system.md)\n\n"

    profile_readme = profile_header + nav_link + report_md + "\n---\n\n## Instructions\n\n"
    if non_debug_md:
        profile_readme += non_debug_md + "\n\n"
    profile_readme += "[View debug instructions](instructions/debug.md)\n"

    debug_header = "<!-- DEBUG - fragments prefixed with 🔍 - not sent via MCP -->\n\n"
    if debug_md:
        # Choose a fence longer than any backtick run found in the content to avoid
        # prematurely closing the fenced code block if the content contains backticks.
        import re

        runs = re.findall(r"`+", debug_md)
        max_run = max((len(r) for r in runs), default=0)
        # Use at least 3 backticks for the fence to be widely compatible with Markdown
        fence_len = max(3, max_run + 1)
        fence = "`" * fence_len
        debug_content = debug_header + f"{fence}text\n" + debug_md + f"\n{fence}\n"
    else:
        debug_content = debug_header + "\n"

    return {"README.md": profile_readme, "instructions/debug.md": debug_content}


def main(argv: list[str] | None = None) -> int:
    """Generate all profile docs before mkdocs build."""
    args = parse_args(argv)
    sim = load_simulator_module()

    try:
        profiles = sim.discover_builtin_profiles()
    except Exception:
        p = REPO_ROOT / "taskmajor" / "profiles"
        profiles = sorted(
            [d.name for d in p.iterdir() if d.is_dir() and not d.name.startswith(".")]
        )

    if not profiles:
        print("No profiles found. Exiting.")
        return 1

    outdir = REPO_ROOT / DEFAULT_OUT
    # Clean output directory in a single line and recreate
    import shutil

    shutil.rmtree(outdir, ignore_errors=True)
    ensure_dir(outdir)

    chains: dict[str, list[str]] = {}
    regen_base = "python tools/generate_profile_docs.py"

    ctxs = []
    for profile in profiles:
        print(f"Generating profile: {profile}")
        ctx = sim.load_profile_context(profile)
        ctxs.append(ctx)
        chains[profile] = [c.get("name") for c in ctx.chain]

        generated_at = datetime.now().isoformat()
        regen_cmd = regen_base

        artifacts = build_profile_doc_artifacts(
            sim, ctx, generated_at=generated_at, regen_cmd=regen_cmd
        )

        # Write artifacts returned as relative paths -> content
        for rel_path, content in artifacts.items():
            dest = outdir / profile / rel_path
            atomic_write(dest, content)

    write_index_md(outdir, profiles, sim.build_profile_index_data(ctxs))

    if not args.no_update_mkdocs:
        mkdocs_path = REPO_ROOT / "mkdocs.yml"
        if mkdocs_path.exists():
            try:
                update_mkdocs_configuration(mkdocs_path, profiles)
            except Exception as e:
                print(f"Warning updating mkdocs.yml: {e}")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
