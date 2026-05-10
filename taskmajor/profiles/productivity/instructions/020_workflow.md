# Workflow

## Capture
`add_task` immediately. Use `project: "Inbox"` if you're not sure.

## Organize
Assign project, priority, due date. 

## Review (new)
- **Daily review** : Launch the prompt `daily_review` every morning.

## Energy (UDA)
- `energy` (enum: low, medium, high): use to mark a task's energy requirement or the user's current energy.
- During Capture: include `energy` when known (e.g., `add_task "Call client" project:Work energy:low`).
- During Organize: assign `energy` to help scheduling and selection.
- During Review: filter tasks by `energy` to pick items matching current energy (e.g., `query_tasks(filter:"status:pending energy:low")`).
