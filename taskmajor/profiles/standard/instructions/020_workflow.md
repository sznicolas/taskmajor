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
