# Quick Start

Get up and running with TaskMajor in 5 minutes.

## 1. Start the Server

```bash
cd taskmajor
python -m taskmajor.bootstrap.server
```

You should see:

```
INFO  taskmajor.bootstrap.server: TaskMajor Server started at http://localhost:8888
```

## 2. Query Today's Tasks

Using any MCP client, fetch the resource:

```
GET taskmajor://agenda/today
```

Returns JSON with pending tasks due today.

## 3. Add a Task

Use `add_task` to create a task (use `project: Inbox` for quick capture without triage):

```
add_task(description="Buy groceries", project="Inbox")
```

## 4. List All Tasks

Query with filters:

```
query_tasks(filters={"status": "pending"}, limit=10)
```

## 5. Triage a Task

Move a task from review queue to ready:

```
update_task(
    task_id="abc123",
    task_input=TaskInputDTO(
        project="personal",
        priority="M",
        due="tomorrow"
    )
)
```

## Common Operations

### Get Week's Tasks
```
GET taskmajor://agenda/week
```

### Get Overdue Tasks
```
GET taskmajor://status/overdue
```

### Complete a Task
```
done_task(task_id="abc123")
```

### Review Queue
```
GET taskmajor://queue/unsorted
```

## Troubleshooting

### "TaskWarrior 'task' command not found"
Install TaskWarrior: https://taskwarrior.org/download/build/

### "Connection refused"
Ensure the server is running: `python -m taskmajor.bootstrap.server`

### Permissions errors
Check `.env` paths have read/write permissions

## Learn More

- [Configuration](configuration.md) — Advanced settings
- [API Reference](../api-reference/index.md) — Complete documentation
