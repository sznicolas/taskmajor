# MCP Tools Reference

This page describes the **tools actually exposed to the standard runtime**.

---

## Business Tools

### `query_tasks(filters=None, sort=None, limit=50, offset=0) -> dict`

Canonical read with pagination.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filters` | dict \| None | None | `project`, `projects`, `priority`, `status`, `tags_any`, `tags_all`, `due_before`, `due_after`, `has_depends`, `is_blocked`, `text` |
| `sort` | list[str] \| None | None | `due`, `-due`, `priority`, `-priority`, `project`, `urgency` |
| `limit` | int \| None | `50` | Max number of results |
| `offset` | int | `0` | Offset |

For `tags_any` and `tags_all`, the MCP accepts the public form from `metadata` (`+phone`, `+@home`) and normalizes it to the underlying Taskwarrior tag.

Response:

```json
{
  "tasks": [
    {
      "uuid": "...",
      "description": "Prepare the presentation",
      "project": "Work",
      "priority": "H",
      "tags": [],
      "due": "2026-03-23T17:00:00+01:00",
      "status": "pending",
      "depends": []
    }
  ],
  "total": 42
}
```

### `get_task(task_id: str) -> dict`

Get a single task with full details (depends, annotations, UDAs, timestamps).

Args:
- `task_id`: ID or UUID of the task to retrieve.

Example response:

```json
{
  "uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  "description": "Review capture",
  "project": "Inbox",
  "priority": null,
  "tags": [],
  "due": "2026-04-11T11:00:00+00:00",
  "status": "pending",
  "depends": [],
  "annotations": [
    {"id": 1, "entry": "2026-04-10T09:15:00+00:00", "description": "Captured from email"}
  ],
  "udas": {"estimate": "30min"},
  "entry": "2026-04-10T09:00:00+00:00",
  "modified": "2026-04-10T09:20:00+00:00"
}
```


### `get_stats(filters=None) -> dict`

Aggregates over the filtered selection.

Typical response:

```json
{
  "total": 60,
  "by_status": {"pending": 12, "completed": 45, "deleted": 3},
  "by_project": {"Inbox": 3, "Work": 8, "Personal": 4},
  "by_priority": {"H": 2, "M": 5, "L": 5},
  "overdue": 2
}
```

### `next_task(filters=None) -> dict`

Returns the next recommended actionable task (excludes tasks blocked by unresolved dependencies).

The response follows the canonical contract `{tasks, total}` and additionally contains `selection_reason`.

### `update_task(task_id: str, task_input: TaskInputDTO) -> dict`

Modify an existing task. Can be used for both triage classification (project, priority, due, tags) and advanced field modifications (description, recurrence, dependencies, etc.).

**Requirement**: At least one field in `task_input` must be modified. Raises `ValueError` if no changes would be applied.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | str | ✅ | ID or UUID |
| `task_input` | TaskInputDTO | ✅ | Updated task fields (minimum: 1 field required) |

**Returns**: Serialized task object (dict) with updated values.

**Example**:
```python
# Triage a task
update_task(
    task_id="abc123",
    task_input=TaskInputDTO(
        project="work",
        priority="H",
        due="friday",
        tags=["urgent"]
    )
)
```

---

## CRUD / Execution

### `add_task(task_input: TaskInputDTO) -> dict`

Create a complete task.

### `done_task(task_id: str) -> str`

Mark a task as completed.

### `delete_task(task_id: str) -> str`

Soft delete a task.

### `start_task(task_id: str) -> str`

Start a task.

### `stop_task(task_id: str) -> str`

Stop a started task.

---

## Diagnostic

### `report_error(tool_name, parameters, error) -> str`

Log an agent error to the MCP journal.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tool_name` | str | ✅ | Relevant tool |
| `parameters` | dict | ✅ | Parameters sent |
| `error` | str | ✅ | Error message |

---

## Metadata

### `get_projects() -> dict`

All projects currently in use by pending tasks.

### `get_tags() -> dict`

All tags currently in use by pending tasks.

### `get_udas() -> dict`

All UDAs defined in the TaskWarrior configuration.

---

## Date Tools

### `resolve_date(expression: str) -> dict`

Resolve a TaskWarrior date expression to an ISO datetime string. Use before passing dates to `add_task` or `update_task`.

Supported expressions: `today`, `tomorrow`, `friday`, `eom`, `eow`, `today+2d`, `P2W`, etc.

### `validate_date(expression: str) -> dict`

Check whether a string is a valid TaskWarrior date expression. Returns `{"expression": ..., "valid": true|false}`.

---

## Context Management

### `list_contexts() -> dict`

List all defined TaskWarrior contexts and the currently active one.

### `set_context(name: str) -> dict`

Activate a named TaskWarrior context (filters future queries to that context's read filter).

### `unset_context() -> dict`

Clear the active TaskWarrior context.

---

## Configuration

### `get_config() -> dict`

Return the current TaskMajor server configuration.

### `set_timezone(timezone: str) -> dict`

Update the server timezone.

### `add_uda(uda_config: UdaConfig) -> dict`

Add a new User-Defined Attribute to the TaskWarrior configuration.

### `delete_uda(name: str) -> dict`

Remove a UDA from the TaskWarrior configuration.

### `define_context(context: ContextDTO) -> dict`

Create or update a TaskWarrior context.

### `delete_context(name: str) -> dict`

Remove a TaskWarrior context.
