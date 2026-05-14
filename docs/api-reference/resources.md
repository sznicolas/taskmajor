# MCP Resources Reference

## Overview

Resources are MCP endpoints that agents can access via `read_mcp_resource(uri)`. TaskMajor provides built-in resources and supports custom resource declarations in profiles.

## Resource Declaration

Most resources are declared in profile manifests (`taskmajor/profiles/<name>/manifest.yaml`):

```yaml
resources:
  - uri: "taskmajor://my-resource"
    name: "My Resource"
    description: "Custom resource"
    backend:
      function: query_tasks
      params:
        filter: "status:pending project:MyProject"
        sort: ["due", "priority"]
        limit: 20
```

See [Profiles](../user-guides/profiles/profile-system.md) for detailed resource declaration syntax.

## Available Resources

Resources are accessible via `read_mcp_resource(uri)` in the agent.

### `taskmajor://queue/unsorted`
Pending tasks in the Inbox project (configurable per profile).

```json
{
  "tasks": [
    {
      "uuid": "...",
      "description": "Call the plumber",
      "project": "Inbox",
      "priority": null,
      "tags": ["phone"],
      "due": null,
      "status": "pending",
      "depends": []
    }
  ],
  "total": 1
}
```

---

### `taskmajor://agenda/today`
Pending tasks due today.

```json
{
  "tasks": [
    {"uuid": "...", "description": "Write report", "project": "Work", "priority": "H", "tags": [], "due": "2026-02-28T17:00:00", "status": "pending", "depends": []}
  ],
  "total": 1
}
```

---

### `taskmajor://agenda/week`
Pending tasks due in the next 7 days.

```json
{
  "tasks": [...],
  "total": 8
}
```

---

### `taskmajor://status/overdue`
Pending tasks already past due.

```json
{
  "tasks": [
    {"uuid": "...", "description": "Send quote", "project": "Work", "priority": "H", "tags": [], "due": "2026-02-26T17:00:00", "status": "pending"}
  ],
  "total": 2
}
```

---

### `taskmajor://config/schema`
All projects, tags, priorities, available TaskWarrior contexts, and API capabilities (pending tasks only).

**Important distinction:**
- `available_contexts` : TaskWarrior contexts defined in `.taskrc` (real contexts with read/write filters)
- `active_context` : Currently active TaskWarrior context (or `null`)
- `context_tags` : Tags following the `+@` naming convention (e.g., `+@office`, `+@calls`) — these are not real contexts, just task labels

```json
{
  "projects": ["Inbox", "Work", "Perso", "Clarify", "Scratchpad"],
  "tags": ["+phone", "+errands", "+waiting"],
  "context_tags": ["+@home", "+@office"],
  "available_contexts": ["home", "office"],
  "active_context": "office",
  "priorities": ["H", "M", "L"],
  "views": ["review", "today", "week", "overdue"],
  "supported_filters": [
    "project",
    "priority",
    "status",
    "tags_any",
    "tags_all",
    "due_before",
    "due_after",
    "has_depends",
    "is_blocked",
    "text"
  ],
  "supported_sorts": ["due", "-due", "priority", "-priority", "project", "urgency"],
  "tag_conventions": {
    "contexts": {"prefix": "+@"},
    "lists": {"prefix": "+"}
  },
  "resource_uris": {
    "review": "taskmajor://queue/unsorted",
    "today": "taskmajor://agenda/today",
    "week": "taskmajor://agenda/week",
    "overdue": "taskmajor://status/overdue",
    "stats": "taskmajor://analytics/summary",
    "metadata": "taskmajor://config/schema"
  },
  "api_version": "2.1"
}
```

---

### `taskmajor://analytics/summary`
Task counts by status, project, and priority.

```json
{
  "total": 60,
  "by_status": {"pending": 12, "completed": 45, "deleted": 3},
  "by_project": {"work": 8, "personal": 4},
  "by_priority": {"H": 2, "M": 5, "L": 5},
  "overdue": 2
}
```

---

## Static Resources (Always Available)

These 4 resources are always registered and cannot be declared in profiles:

### `taskmajor://now`
Current date and time in the system timezone.

```json
{
  "date": "2026-02-28",
  "time": "14:30:45",
  "timestamp": "2026-02-28T14:30:45+01:00",
  "timezone": "Europe/Paris"
}
```

---

### `taskmajor://context/current`
Currently active TaskWarrior context.

```json
{
  "name": "office",
  "read_filter": "project:work",
  "write_filter": "project:work",
  "is_active": true
}
```

---

### `taskmajor://debug/errors`
History of errors reported by the agent (JSONL format, most recent first).

```json
{
  "errors": [
    {
      "timestamp": "2026-02-28T10:00:00Z",
      "tool_name": "add_task",
      "parameters": {"description": "..."},
      "error": "Invalid date format"
    }
  ]
}
```

---

### `taskmajor://history/undo`
Undo stack (if configured on TaskService).

```json
{
  "entries": [
    {
      "action": "completed_task",
      "task_id": "abc123",
      "timestamp": "2026-02-28T14:00:00Z"
    }
  ]
}
```

---

## Backend Functions

Profile resources use these TaskService backend functions (ALLOWED_BACKENDS):

- **`query_tasks`** — Filter and paginate tasks
  ```yaml
  backend:
    function: query_tasks
    params:
      filter: "status:pending"
      sort: ["due", "-priority"]
      limit: 50
  ```

- **`get_tasks_by_scope`** — Group tasks by scope
  ```yaml
  backend:
    function: get_tasks_by_scope
    params:
      scope: project          # or: priority, day, week
      filters: {status: pending}
  ```

- **`get_stats`** — Task statistics
  ```yaml
  backend:
    function: get_stats
    params:
      filters: {status: all}
  ```

- **`next_task`** — Highest-priority unblocked task
  ```yaml
  backend:
    function: next_task
    params:
      filters: {status: pending}
  ```

- **`get_metadata`** — Projects, tags, priorities, contexts, API info
  ```yaml
  backend:
    function: get_metadata
  ```

- **`add_task`** — Create new task
  ```yaml
  backend:
    function: add_task
    params:
      description: "Fixed task description"
      project: "Inbox"
  ```

- **`update_task`** — Modify existing task
  ```yaml
  backend:
    function: update_task
    params:
      task_id: "abc123"
      priority: "H"
  ```

- **`get_projects`** — All projects currently in use (no params)
  ```yaml
  backend:
    function: get_projects
  ```

- **`get_tags`** — All tags currently in use (no params)
  ```yaml
  backend:
    function: get_tags
  ```

- **`get_udas`** — All UDAs defined in TaskWarrior configuration (no params)
  ```yaml
  backend:
    function: get_udas
  ```
