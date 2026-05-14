<!-- AUTO-GENERATED - Do not edit manually -->

> **AUTO-GENERATED - Do not edit manually**

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
| Tool | Declared in (chain) |
|---|---|
| add_task | base |
| get_task | base |
| query_tasks | base |
| update_task | base |
| delete_task | base |
| done_task | base |
| next_task | minimal |
| get_projects | minimal |
| get_tags | minimal |

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
| taskmajor://roadmap/project | get_tasks_by_scope | {"filters": {"status": "pending"}, "scope": "project"} | Tasks by Project |  |
| taskmajor://queue/unsorted | query_tasks | {"filter": "status:pending project:", "sort": ["urgency"]} | Unsorted Queue |  |

---

## Instructions

# Minimal Profile Objective

Stay lightweight: capture tasks fast, keep triage shallow, and avoid extra workflow machinery unless the user asks for it.


---

# Workflow

1. Capture with `add_task`; keep descriptions short and clear.
2. Before triage, reuse existing values with `get_projects` and `get_tags`.
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
