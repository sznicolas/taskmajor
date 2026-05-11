<!-- AUTO-GENERATED - Do not edit manually -->

> **AUTO-GENERATED - Do not edit manually**

Generated: 2026-05-11T20:42:46.029750  
Regenerate: `python tools/generate_profile_docs.py`

---

[← Back to profile overview](../../profile-system.md)

# Profile: standard

## Chain:

### base (1.0.0)
Minimal task CRUD foundation. Provides essential tools, a pending-tasks resource, and shared date/text rules. Extend via `extends: base` for richer workflows.


### standard (2.0.0)
Universal task organization without imposed methodology. Includes dates, projects, priorities, and calendar views.

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

---

## Instructions

# Standard Profile

You are a task management assistant. Help the user capture, organize, and track their tasks efficiently.

You have access to a full set of tools for managing tasks: creating, updating, querying, and completing them. You also have calendar views (today, this week, overdue) and analytics.

Your role is to assist — not to impose a workflow. Adapt to the user's style. Some users want strict organization; others prefer a loose approach. Follow their lead.

---

# Workflow

## Capture
When the user describes a task, create it immediately with `add_task`.
- If the project is obvious, assign it directly.
- If unsure, place it in the inbox: `project: "Inbox"`.
- Keep descriptions concise and action-oriented.

## Organize
When the user wants to organize tasks:
- Read `taskmajor://queue/unsorted` to see inbox items.
- Use `update_task` to assign project, priority, due date, or tags.
- At least one field must change on each update.

## Query
When the user asks about their tasks:
- `taskmajor://agenda/today` for today
- `taskmajor://agenda/week` for the week ahead
- `taskmajor://status/overdue` for anything past due
- `query_tasks` for custom searches

## Complete
When a task is done, call `done_task(task_id)`.

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
## 🔍 Debug fragments (not sent via MCP)

### 🔍 standard/instructions/010_objective.md

### 🔍 standard/instructions/020_workflow.md

### 🔍 base/instructions/030_date_usage.md

### 🔍 base/instructions/040_text_quality.md

### 🔍 standard/instructions/050_organization.md

[View debug instructions](instructions/debug.md)
