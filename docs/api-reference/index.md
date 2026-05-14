# API Reference

TaskMajor exposes task management capabilities through **Resources** (readable data views), **Tools** (callable operations), and **Prompts** (agent instructions).

## Resources (taskmajor://)

Resources provide read-only views of task data. Each resource returns JSON.

### Core Resources

| URI | Description | Purpose |
|-----|-------------|---------|
| `taskmajor://agenda/today` | Tasks due today | Quick view of today's workload |
| `taskmajor://agenda/week` | Tasks due in next 7 days | Weekly planning |
| `taskmajor://status/overdue` | Tasks past their due date | Triage overdue items |
| `taskmajor://queue/unsorted` | Inbox tasks (pending, project:Inbox) | Review workflow |
| `taskmajor://analytics/summary` | Aggregate task counts | Progress tracking |
| `taskmajor://config/schema` | API surface description | Self-description (projects, tags, contexts) |

### Additional Resources

| URI | Description | Purpose |
|-----|-------------|---------|
| `taskmajor://context/current` | Current TaskWarrior context info | Context management |
| `taskmajor://debug/errors` | Error history (agent errors) | Debugging |
| `taskmajor://history/undo` | Undo stack (completed/deleted tasks) | Undo operations (post-sync) |
| `taskmajor://now` | Current date/time and timezone | Date references |
| `taskmajor://roadmap/project` | Tasks grouped by project | High-level roadmap by project |
| `taskmajor://roadmap/priority` | Tasks grouped by priority | Prioritized roadmap |
| `taskmajor://roadmap/day` | Tasks grouped by day (due date) | Daily roadmap |
| `taskmajor://roadmap/week` | Tasks grouped by ISO week | Weekly roadmap |

#### `taskmajor://context/current`
Returns the currently active TaskWarrior context and its filter.

```json
{
  "context": "work",
  "read_filter": "project:work",
  "write_filter": "project:work"
}
```

#### `taskmajor://queue/unsorted`
Returns tasks in the review/capture queue (default: "Inbox" project). Use this to track newly added tasks pending triage.

```json
{
  "tasks": [
    {"uuid": "...", "description": "New task", "project": "Inbox", "status": "pending"},
    ...
  ],
  "total": 5
}
```

#### `taskmajor://now`
Returns the current date, time, and system timezone. Useful for resolving relative date expressions.

```json
{
  "now": "2025-04-01T14:30:00Z",
  "date": "2025-04-01",
  "time": "14:30:00Z",
  "timezone": "Europe/Paris"
}
```

### Templated Resources

| URI Pattern | Description | Example |
|-------------|-------------|---------|
| `taskmajor://date/{expression}` | Date calculation (resolved to ISO) | `taskmajor://date/tomorrow`, `taskmajor://date/eow`, `taskmajor://date/today+3d` |
| `taskmajor://project/{project_name}/tasks` | Tasks in a project | `taskmajor://project/work/tasks` |

#### `taskmajor://date/{expression}`
Resolves a TaskWarrior date expression to an ISO datetime. Accepts any valid TaskWarrior date syntax.

**Supported expressions:**
- Simple dates: `today`, `tomorrow`, `friday`
- End of period: `eom` (end of month), `eow` (end of week), `eoq` (end of quarter), `eoy` (end of year)
- Relative: `today+2d`, `now+3h`, `tomorrow+5h30m`
- ISO durations: `P2W` (2 weeks), `P1M` (1 month), `PT4H` (4 hours)

```json
GET taskmajor://date/tomorrow
# Returns:
{
  "expression": "tomorrow",
  "resolved": "2025-04-02T00:00:00Z",
  "date": "2025-04-02",
  "time": "00:00:00Z"
}

GET taskmajor://date/eow
# Returns:
{
  "expression": "eow",
  "resolved": "2025-04-04T23:59:59Z",
  "date": "2025-04-04",
  "time": "23:59:59Z"
}
```

## Tools

Tools are callable operations that modify or query task data.

### Business Queries

#### `query_tasks(filters, sort, limit, offset)`
Flexible task search with filtering, sorting, and pagination.

See the JSON Schema for the input at `schemas/query_tasks_schema.json` for a machine-readable contract. Key semantics:

- Filters are optional and combined with logical AND across keys. For a single key, string values match exactly; array values mean "match any" (OR within that key).
- `projects` (array) matches any listed project (OR); `project` matches a single project.
- `tags_any` matches tasks that have any of the provided tags (OR). `tags_all` requires the task to have all listed tags (AND).
- `status` accepts either a single status string or an array of statuses (e.g., `"pending"`, `"completed"`).
- Date filters (`due_before`, `due_after`) accept ISO datetimes or TaskWarrior expressions (e.g., `"today"`, `"eow"`).
- `text` performs a simple full-text match against task description and tags.
Sorting:
- `sort` is a list of field names in precedence order. Prefix a field with `-` to sort descending (e.g., `-due`).
- Common sort fields: `due`, `priority`, `urgency`, `start`, `end`, `project`.

Pagination:
- `limit` bounds the number of returned tasks. `null` or omission uses the server default.
- `offset` skips N matching items and is useful for paging.

Examples:

```python
# High-priority pending work tasks due this week, limited to 10
query_tasks(
    filters={"project": "work", "status": "pending", "priority": "H", "due_before": "eow"},
    sort=["due", "-priority"],
    limit=10
)

# Any task in work or personal projects with either "urgent" or "blocked" tag
query_tasks(
    filters={"projects": ["work", "personal"], "tags_any": ["urgent", "blocked"]},
    sort=["-urgency"],
    limit=50
)

# Text search for "meeting" across descriptions and tags
query_tasks(
    filters={"text": "meeting"},
    sort=["due"],
)
```

#### `get_stats(filters)`
Aggregate task statistics.

```python
# Returns: counts by status, project, priority, and overdue
get_stats(filters={"status": "all"})
```


#### `next_task(filters)`
Get the next recommended actionable task.

```python
# Returns: single task from pending, prioritized by urgency
next_task(filters={"priority": "H"})
```

#### `update_task(task_id, task_input) -> TaskOutputDTO`
Update an existing task with new field values. Can be used for both simple triage (project, priority, due, tags) and advanced modifications (description, recurrence, dependencies, etc.).

**Requirement**: At least one field must be modified. Raises `ValueError` if no changes would be applied.

```python
# Triage: assign project, priority, due date, and tags
update_task(
    task_id="12345",
    task_input=TaskInputDTO(
        project="work",
        priority="M",
        due="friday",
        tags=["urgent"]
    )
)
```

### Task Management (CRUD)

#### `add_task(task_input)`
Create a new task.

```python
# task_input: TaskInputDTO with description, project, priority, due, tags, etc.
add_task({
    "description": "Complete report",
    "project": "work",
    "priority": "H",
    "due": "tomorrow"
})
```

#### `done_task(task_id)`
Mark a task as complete.

```python
done_task(task_id="12345")
```

#### `delete_task(task_id)`
Soft-delete a task (mark as deleted, reversible).

```bash
delete_task(task_id="12345")
```

### Workflow Operations

#### `start_task(task_id)`
Mark a task as started (begin time tracking).

```python
start_task(task_id="12345")
```

#### `stop_task(task_id)`
Stop active task (end time tracking).

```python
stop_task(task_id="12345")
```

### Context Management

#### `list_contexts()`
List all available TaskWarrior contexts.

```python
# Returns: list of context names and their filters
list_contexts()
```

#### `set_context(name)`
Activate a TaskWarrior context (filters future queries).

```python
set_context(name="work")
```

#### `unset_context()`
Clear active context.

```python
unset_context()
```

### Date Tools

#### `resolve_date(expression)`
Resolve a TaskWarrior date expression to an ISO datetime string.

Use this to preview what a date expression means before passing it to add_task or update_task.

```python
# Examples:
# - Simple dates: 'today', 'tomorrow', 'friday'
# - End of period: 'eom' (end of month), 'eow' (end of week)
# - Relative: 'today+2d', 'now+3h', 'today+17h'
# - ISO durations: 'P2W' (2 weeks), 'P1M' (1 month)

resolve_date("friday")
# Returns: {
#   "expression": "friday",
#   "resolved": "2025-04-04T23:59:59Z",
#   "date": "2025-04-04",
#   "time": "23:59:59Z"
# }

resolve_date("today+2d")
# Returns: {..., "resolved": "2025-04-02T00:00:00Z"}
```

#### `validate_date(expression)`
Check whether a string is a valid TaskWarrior date expression.

Always validate user-supplied dates before passing them to add_task or update_task to avoid silent failures.

```python
validate_date("friday")
# Returns: {"expression": "friday", "valid": True}

validate_date("invalid-date")
# Returns: {"expression": "invalid-date", "valid": False}
```

### Diagnostic Tools

#### `report_error(tool_name, parameters, error)`
Report an error encountered while using a tool.

Call this whenever a tool returns an unexpected error or behaves incorrectly, so the issue can be investigated.

```python
# Example: report an error from add_task
report_error(
    tool_name="add_task",
    parameters={"description": "Buy milk", "due": "today"},
    error="Connection refused: TaskWarrior server unavailable"
)
# Returns: "Error logged at 2025-04-01T14:30:05Z"
```

The error log is stored and can be accessed via `taskmajor://debug/errors` resource.

## Prompts

Prompts are system instructions for agents using TaskMajor.

### Standard Prompts

- **`task_management`** — Core task lifecycle management prompt
- **`review_workflow`** — Review queue and triage workflow prompt
- **`date_handling`** — Date expression parsing and calendar prompt
- **`context_aware`** — Context filtering and tag management prompt

## Data Models

### TaskInputDTO
Input model for task creation/update:

```python
{
    "description": str,           # Task title (required for creation)
    "project": str,               # Project name
    "priority": str,              # H, M, L, or empty
    "due": str,                   # Due date (ISO format or TaskWarrior expression)
    "tags": list[str],            # Task tags
    "depends": list[str],         # Task IDs this depends on
    "scheduled": str,             # Earliest start date
    "wait": str,                  # Date to unhide task
    "until": str,                 # Recurrence expiration
    "recur": str,                 # Recurrence (daily, weekly, monthly, etc.)
    "annotations": list[str],     # Notes/comments
    "udas": dict,                 # User-defined attributes
}
```

### Task (QueryResult)
Output model for task queries:

```python
{
    "id": str,                    # Task UUID
    "description": str,           # Task title
    "project": str,               # Project name
    "priority": str,              # H, M, L
    "due": str,                   # Due date (ISO)
    "start": str,                 # Start time (if active)
    "end": str,                   # Completion time (if done)
    "status": str,                # pending, completed, deleted
    "tags": list[str],            # Task tags
    "urgency": float,             # Computed urgency score
    "annotations": list[str],     # Notes
    "udas": dict,                 # User-defined attributes
}
```

### TaskQueryFilters
Filter specification for query_tasks() and other query operations.

All fields are optional. Multiple filters are combined with AND logic.

```python
{
    "project": str | None,           # Single project name
    "projects": list[str] | None,    # Multiple project names (OR)
    "priority": str | None,          # Single priority: H, M, L
    "status": str | list[str] | None, # pending, waiting, completed, deleted
    "tags_any": list[str] | None,    # Task has ANY of these tags (OR)
    "tags_all": list[str] | None,    # Task has ALL of these tags (AND)
    "due_before": str | None,        # Due date <= (ISO or TaskWarrior expr)
    "due_after": str | None,         # Due date >= (ISO or TaskWarrior expr)
    "text": str | None,              # Search in description and tags
}
```

**Examples:**

```python
# High priority work tasks due this week
{
    "project": "work",
    "priority": "H",
    "due_before": "eow"
}

# Multiple projects, any tag
{
    "projects": ["work", "personal"],
    "tags_any": ["urgent", "blocked"]
}

# Overdue tasks
{
    "status": "pending",
    "due_before": "today"
}
```

### Metadata
Self-description of API capabilities:

```python
{
    "projects": list[str],        # Available projects
    "tags": list[str],            # Available tags
    "contexts": list[str],        # Available contexts
    "priorities": ["H", "M", "L", ""],
    "api_version": str,           # Version of this contract
    "available_filters": list[str],  # Supported filter keys
    "available_sorts": list[str],    # Supported sort fields
}
```

## Examples

### Get Today's Tasks

```python
# Resource: straightforward read
GET taskmajor://agenda/today

# Tool: more control
query_tasks(
    filters={"status": "pending", "due": "today"},
    sort=["priority"],
    limit=10
)
```

### Create & Triage a Task

```python
# Quick capture to Inbox
add_task(description="Project kickoff meeting", project="Inbox")

# Later, triage with update_task
update_task(
    task_id="abc123",
    task_input=TaskInputDTO(
        project="projects",
        priority="H",
        due="friday",
        tags=["meeting", "stakeholders"]
    )
)
```

### Weekly Review

```python
# Get week's tasks
week_tasks = query_tasks(
    filters={"status": "pending", "due_after": "today", "due_before": "eow"},
    sort=["due", "priority"]
)

# Process Inbox
review_tasks = query_tasks(
    filters={"project": "Inbox", "status": "pending"}
)

# Triage each one with update_task
for task in review_tasks:
    update_task(
        task_id=task["id"],
        task_input=TaskInputDTO(
            project="appropriate_project",
            priority="M"
        )
    )
```

## See Also

- [Configuration](../getting-started/configuration.md) — Environment setup
- [Resources](resources.md) — Detailed resource specs
- [Tools](tools.md) — Detailed tool specs
