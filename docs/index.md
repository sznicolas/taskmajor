# TaskMajor

> **TaskMajor MCP. Coordinate your tasks. Execute with precision.**

## What is TaskMajor?

TaskMajor is a modern **Model Context Protocol (MCP)** server for TaskWarrior, enabling AI agents to seamlessly manage tasks via a clean, well-documented API.

It provides:

- **Complete Task Lifecycle** — Create, update, and complete tasks
- **Triage Workflow** — Capture tasks to Inbox and triage with `update_task`
- **Context Management** — Support for TaskWarrior contexts with filtering and metadata exposure
- **Rich Metadata** — Auto-discovery of projects, tags, priorities, and API capabilities
- **Multiple Views** — Pre-built resources for today's tasks, this week, overdue items, and statistics
- **OpenTelemetry Observability** — Built-in tracing, metrics, and structured logging (optional)
- **Type-Safe** — Full Pydantic models for all DTOs and responses

## Quick Start

### Installation

```bash
git clone https://github.com/yourusername/taskmajor.git
cd taskmajor

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

### Run the Server

```bash
# Start the MCP server
python -m taskmajor.bootstrap.server

# Or run the inspector (FastMCP dev mode)
uv run fastmcp dev inspector taskmajor/bootstrap/core.py:main
```

### Use as a Library

```python
from taskmajor.bootstrap import create_mcp

# Create the MCP server, task service, and error log
mcp, task_service, error_log = create_mcp()

# Use the task_service directly
tasks = task_service.list_pending_tasks()
print(f"Pending tasks: {len(tasks)}")
```

## Core Concepts

### Resources (`taskmajor://`)

Read-only views of task data:

- **`taskmajor://agenda/today`** — Tasks due today
- **`taskmajor://agenda/week`** — Tasks due in the next 7 days
- **`taskmajor://status/overdue`** — Tasks past due
- **`taskmajor://queue/unsorted`** — Tasks in the review queue
- **`taskmajor://analytics/summary`** — Task aggregates
- **`taskmajor://config/schema`** — API self-description

[Full API Reference →](api-reference/index.md)

### Tools

Callable operations:

- **Business Queries** — `query_tasks()`, `get_stats()`, `next_task()`
- **Task Management** — `add_task()`, `update_task()`, `done_task()`, `delete_task()`
- **Workflow** — `update_task()`, `start_task()`, `stop_task()`
- **Contexts** — `list_contexts()`, `set_context()`, `unset_context()`

[Full API Reference →](api-reference/index.md)

## Documentation

- [Getting Started](getting-started/index.md) — Installation and setup
- [Configuration](getting-started/configuration.md) — Environment variables and settings
- [API Reference](api-reference/index.md) — Complete resource and tool documentation
- [Architecture](developer/architecture.md) — System design and modules
- [GTD Workflow](user-guides/workflows/gtd-workflow.md) — GTD methodology with TaskMajor
- [Observability](developer/observability.md) — OpenTelemetry setup

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass (`uv run pytest`)
5. Submit a pull request

## License

Check the LICENSE file for terms.

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/taskmajor/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/taskmajor/discussions)
