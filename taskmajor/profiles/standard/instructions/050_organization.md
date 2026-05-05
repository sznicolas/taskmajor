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
Tags add context to tasks. Use them when they help, skip them when they don't.
Common examples: `+waiting`, `+call`, `+errands`, `+computer`

Check existing tags with `get_tags()` before creating new ones.
