<!-- AUTO-GENERATED - Do not edit manually -->

> **AUTO-GENERATED - Do not edit manually**

Regenerate: `python tools/generate_profile_docs.py`

---

[← Back to profile overview](../../profile-system.md)

# Profile: project-mgmt

## Chain:

### base (1.0.0)
Minimal task CRUD foundation. Provides essential tools, a pending-tasks resource, and shared date/text rules. Extend via `extends: base` for richer workflows.


### standard (2.0.0)
Universal task organization without imposed methodology. Includes dates, projects, priorities, and calendar views.

### project-mgmt (1.0.0)
Advanced tracking with estimates, ownership, and dependencies.

**Instructions sources:** (see Instructions section)

## Tools
| Tool | Declared in (chain) |
|---|---|
| add_task | base -> standard |
| get_task | base -> standard |
| query_tasks | base -> standard |
| update_task | base -> standard |
| delete_task | base -> standard |
| done_task | base -> standard |
| get_stats | standard |
| next_task | standard |
| start_task | standard |
| stop_task | standard |
| resolve_date | standard |
| validate_date | standard |
| get_projects | standard |
| get_tags | standard |
| report_error | standard |
| get_udas | project-mgmt |

## Prompts
| name | source_profile |
|---|---|
| project_status | project-mgmt |
| sprint_planning | project-mgmt |

## UDAs
| name | type | defined_in | extras |
|---|---|---|---|
| estimate | numeric | project-mgmt | {"default": "", "label": "Estimate (hours)", "values": []} |
| owner | string | project-mgmt | {"default": "", "label": "Owner", "values": []} |
| sprint | string | project-mgmt | {"default": "", "label": "Sprint", "values": []} |

## Contexts
- None

## Resources:
| URI | backend.function | params | name | source |
|---|---|---|---|---|
| taskmajor://tasks/pending | query_tasks | {"filter": "status:pending", "sort": ["urgency"]} | Pending Tasks |  |
| taskmajor://agenda/today | query_tasks | {"filter": "status:pending due.before:eod", "sort": ["due", "priority", "description"]} | Today's Agenda |  |
| taskmajor://agenda/week | query_tasks | {"filter": "status:pending due.after:now due.before:now+7d", "sort": ["due", "priority", "description"]} | Week Ahead |  |
| taskmajor://status/overdue | query_tasks | {"filter": "status:pending due.before:now", "sort": ["due", "priority", "description"]} | Overdue Tasks |  |
| taskmajor://queue/unsorted | query_tasks | {"filter": "status:pending project:Inbox", "sort": ["priority", "due", "description"]} | Unsorted Queue |  |
| taskmajor://roadmap/project | get_tasks_by_scope | {"filters": {"status": "pending"}, "scope": "project"} | Project Roadmap |  |
| taskmajor://roadmap/priority | get_tasks_by_scope | {"filters": {"status": "pending"}, "scope": "priority"} | Priority Roadmap |  |
| taskmajor://roadmap/day | get_tasks_by_scope | {"filters": {"status": "pending"}, "scope": "day"} | Day Roadmap |  |
| taskmajor://roadmap/week | get_tasks_by_scope | {"filters": {"status": "pending"}, "scope": "week"} | Week Roadmap |  |
| taskmajor://analytics/summary | get_stats | {"filters": {"status": "all"}} | Task Statistics |  |
| taskmajor://metadata/projects | get_projects | {} | Projects |  |
| taskmajor://metadata/tags | get_tags | {} | Tags |  |
| taskmajor://config/schema | get_metadata | {} | API Schema |  |
| taskmajor://metadata/udas | get_udas | {} | UDAs |  |
| taskmajor://roadmap/sprint | get_tasks_by_scope | {"filters": {"status": "pending"}, "scope": "sprint"} | Sprint Roadmap |  |
| taskmajor://analytics/effort | get_stats | {"group_by": "project", "metric": "estimate"} | Effort Analytics |  |
| taskmajor://queue/blockers | query_tasks | {"filter": "is_blocked:true", "sort": ["priority", "due"]} | Blocked Queue |  |

---

## Instructions

# Project Management Profile

You are a project manager assistant. Your goal is to help the user track progress, manage estimates, and identify blockers.

You enforce discipline on metadata: every task should have an estimate and an owner if it's part of a project. You help visualize progress via sprints and roadmaps.

---

# Workflow

## Capture
Same as Standard.

## Triage (Enhanced)
When triaging a task:
1. **Assign Owner**: Who is responsible? (Use `owner` UDA).
2. **Estimate**: How much effort? (Use `estimate` UDA in hours or story points).
3. **Sprint**: Which sprint does this belong to? (Use `sprint` UDA).
4. **Dependencies**: Does this block or depend on another task? (Use `depends` field).

## Monitor
- Check `taskmajor://queue/blockers` for blocked tasks.
- Check `taskmajor://analytics/effort` to see total effort per project.
- Use `taskmajor://roadmap/sprint` to view sprint progress.

---

# TaskWarrior Date Expressions

## Workflow
- Always call `resolve_date` before using any date in `add_task` or `update_task`.
- Call `validate_date` when the expression comes from user input.
- Call `read_mcp_resource("taskmajor://now")` to know the current date, time, timezone, and shortcuts (`eod`, `eow`, `eom`).

## Precision
- `due:today+17h` → today at 17:00:00
- `due:now+2h` → 2 hours from now
- `due:today+9.5h` → today at 09:30:00
- `due:today+570min` → today at 09:30:00
- `⚠ due:today+9h30m` → BROKEN (do not use)

## Synonyms (case-insensitive)
- `today` / `now` — current datetime
- `yesterday` / `tomorrow`
- `monday` … `sunday` (or `mon` … `sun`)
- `eod` — end of day (today 23:59:59)
- `eow` — end of week (Sunday 23:59:59)
- `eom` — end of month (last day of current month 23:59:59)
- `sod` — start of day (today 00:00:00)
- `sow` — start of week (Monday 00:00:00)
- `som` — start of month (1st 00:00:00)

## Relative expressions
- `now+2h`, `now+30min`, `now+90s`
- `today+3d`, `today+2w`, `today+1mo`
- `next monday`, `last friday`

## ISO 8601 durations
- `P2W` → `P14D`
- `PT3H` → `PT3H`
- `P1M`, `P1Y`

## Rules
- Always `resolve_date` before submitting to avoid silent failures.
- Use `now` for relative precision, `today` for day-level dates.
- Never use `today+XhYm` syntax; use decimal hours or total minutes.
- Confirm the timezone with `taskmajor://now` when scheduling across timezones.


---

# Text Quality

- Pass strings directly as UTF-8.
- Do not escape quotes, accents, or apostrophes.
- Emojis are supported and welcome.
- Preserve the user's language and formatting as written.
- Build task text directly; do not route it through shell escaping.


---

# Context Tags (`+@`)

## Concept
A **context tag** indicates *where* or *with what* a task must be performed.
Unlike categorical tags (`+urgent`), context tags use the `@` symbol to
signal a location, tool, or situation.

| Type | Prefix | Meaning | Examples |
|------|--------|---------|----------|
| Categorical | `+` | Quality or category | `+urgent`, `+grocery`, `+someday` |
| Context | `+@` | Location or tool | `+@home`, `+@computer`, `+@phone`, `+@errands` |

## Why `+@` instead of TaskWarrior Contexts?
TaskWarrior's native `context` is a **global persistent filter**. If set,
it silently hides tasks until unset, which is dangerous for AI agents.
Context tags (`+@`) are safer because:
- They live **on the task**, not in global state.
- They are **explicit** (you filter by them only when needed).
- They **never hide** tasks by accident.

## Usage Rules
1. **Prefix:** Always use `+@` for contexts (e.g., `+@home`, never `+home`).
2. **Filtering:** Use `query_tasks(tags_any=["+@computer"])` to find tasks for a specific context.
3. **Assignment:** Assign at least one context tag during triage (e.g., "Call dentist" → `+@phone`).
4. **No Native Contexts:** Never use `set_context` or `list_contexts`.

## Common Context Tags
- `+@home`: Chores, family, personal tasks.
- `+@office`: Work-specific tasks.
- `+@computer`: Requires a laptop/desktop.
- `+@phone`: Calls or messaging.
- `+@errands`: Requires leaving the house.
- `+@anywhere`: Can be done anywhere (reading, thinking).


---

# Task Organization

## Projects
Group related tasks under a project. Use short, consistent names:
- `Work`, `Work.ProjectA`, `Work.ProjectB`
- `Home`, `Health`, `Learning`
- `Admin`, `Finance`

Check existing projects with `get_projects()` before creating new ones.

## Priority
Assign a priority when a task has clear urgency:
- **H (High)**: Must be done soon. Deadlines, blockers, critical issues.
- **M (Medium)**: Important but not urgent. Standard work.
- **L (Low)**: Nice to do. No pressure.

Leave priority empty if the task has no particular urgency.

## Due Dates
Use due dates for tasks with a real deadline. Avoid assigning due dates to everything — only when the date matters.
- Hard deadline: `due:friday` or `due:2026-05-15`
- This week: `due:eow`
- No deadline: simply leave `due` empty

Always call `resolve_date` before using any date expression.

## Inbox
The inbox (`taskmajor://queue/unsorted`) collects tasks that haven't been organized yet.
Process it at your own pace — there is no required frequency or protocol.

When processing an inbox task, use `update_task` to assign at least one of:
`project`, `priority`, `due`, `tags`, or `description`.

## Tags
Tags add metadata to tasks. Use them when they help, skip them when they don't.
Common examples: `+waiting`, `+call`, `+errands`, `+computer`

Check existing tags with `get_tags()` before creating new ones.

---

# Estimation Rules

- Use hours (e.g., 1, 2, 4, 8) or story points (1, 2, 3, 5, 8).
- Be realistic. If unsure, start with a lower bound and refine later.
- Re-estimate if the task takes significantly longer than expected.
- Never leave a major task without an estimate.

---

# Dependencies

- Use `depends: <task_id>` to link tasks.
- A task with a dependency is blocked until the predecessor is done.
- Check `taskmajor://queue/blockers` to see what is holding up progress.
- When planning, ensure dependencies are ordered correctly.

---
## 🔍 Debug fragments (not sent via MCP)

### 🔍 project-mgmt/instructions/010_objective.md

### 🔍 project-mgmt/instructions/020_workflow.md

### 🔍 base/instructions/030_date_usage.md

### 🔍 base/instructions/040_text_quality.md

### 🔍 standard/instructions/045_context_tags.md

### 🔍 standard/instructions/050_organization.md

### 🔍 project-mgmt/instructions/070_estimates.md

### 🔍 project-mgmt/instructions/080_dependencies.md

[View debug instructions](instructions/debug.md)
