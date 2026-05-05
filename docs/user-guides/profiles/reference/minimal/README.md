<!-- AUTO-GENERATED - Do not edit manually -->

> **AUTO-GENERATED - Do not edit manually**

Generated: 2026-04-30T22:44:18.067908
Regenerate: `python tools/generate_profile_docs.py`

---

[← Back to profile overview](../../profile-system.md)

# Profile: minimal

## Chain:

### base (1.0.0)
Minimal task CRUD foundation. Provides essential tools, a pending-tasks resource, and shared date/text rules. Extend via `extends: base` for richer workflows.


### minimal (1.0.0)
Lightweight demo for testing and onboarding. Captures tasks, reuses existing metadata, and keeps the workflow simple.


**Instructions sources:** (see Instructions section)

## Tools
| Tool | Declared in (chain) | Final owner |
|---|---|---|
| add_task | base | base |
| get_task | base | base |
| query_tasks | base | base |
| update_task | base | base |
| delete_task | base | base |
| done_task | base | base |
| next_task | minimal | minimal |
| get_projects | minimal | minimal |
| get_tags | minimal | minimal |
| get_udas | minimal | minimal |

## Prompts
- None

## UDAs
- None

## Contexts
- None

## Resources:
| URI | backend.function | params | name | source |
|---|---|---|---|---|
| taskmajor://tasks/pending | query_tasks | {"filter": "status:pending", "sort": ["urgency"]} | Pending Tasks |  |
| taskmajor://metadata/projects | get_projects | {} | Projects |  |
| taskmajor://metadata/tags | get_tags | {} | Tags |  |
| taskmajor://metadata/udas | get_udas | {} | UDAs |  |
| taskmajor://roadmap/project | get_tasks_by_scope | {"filters": {"status": "pending"}, "scope": "project"} | Tasks by Project |  |
| taskmajor://queue/unsorted | query_tasks | {"filter": "status:pending project:", "sort": ["urgency"]} | Unsorted Queue |  |

---

## Instructions

# Minimal Profile Objective

Stay lightweight: capture tasks fast, keep triage shallow, and avoid extra workflow machinery unless the user asks for it.


---

# Workflow

1. Capture with `add_task`; keep descriptions short and clear.
2. Before triage, reuse existing values with `get_projects`, `get_tags`, and `get_udas`.
3. Use `update_task` to assign project, priority, due date, or tags; change at least one field.
4. Use `next_task` only when the user explicitly asks what to do next.

---

# Text Quality

- Pass strings directly as UTF-8.
- Do not escape quotes, accents, or apostrophes.
- Emojis are supported and welcome.
- Preserve the user's language and formatting as written.
- Build task text directly; do not route it through shell escaping.

---
## 🔍 Debug fragments (not sent via MCP)

### 🔍 minimal/instructions/010_objective.md

### 🔍 minimal/instructions/020_workflow.md

### 🔍 base/instructions/040_text_quality.md

[View debug instructions](instructions/debug.md)
