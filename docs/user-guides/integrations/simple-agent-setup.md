# Connect TaskMajor to Your AI Agent

> **TL;DR**: TaskMajor is an MCP server for TaskWarrior. Start it once, then connect Copilot, Claude Code, Cursor, Hermes, or any MCP-compatible agent.

## Prerequisites

- **TaskWarrior v3.0+**: `brew install task` (macOS) or [taskwarrior.org/download](https://taskwarrior.org/download/)
- **TaskMajor installed**: `git clone … && uv sync`
- **Python 3.10+**

## Start TaskMajor

All agents below require TaskMajor to be running first:

```bash
cd /path/to/taskmajor
uv run -m taskmajor.bootstrap.server
```

Expected output:
```
INFO:    TaskMajor MCP Server ready
```

For **stdio agents** (Copilot, Claude Code, Cursor, Generic MCP), the agent launches the server automatically — you don't need to start it manually. For **HTTP agents** (Hermes), leave the server running in a dedicated terminal.

---

## GitHub Copilot (VS Code)

### Setup

1. Open VS Code Settings (`Cmd+,` / `Ctrl+,`), search `@ext:github.copilot`
2. Click **Edit in settings.json** and add:

```json
{
  "github.copilot.chat.mcp": {
    "taskMajor": {
      "command": "uv",
      "args": ["run", "-m", "taskmajor.bootstrap.server"],
      "type": "stdio"
    }
  }
}
```

3. Save and restart VS Code
4. Open Copilot Chat (`Cmd+Shift+I`) and ask: `What's on my plate today?`

### Custom data location

```json
{
  "github.copilot.chat.mcp": {
    "taskMajor": {
      "command": "uv",
      "args": ["run", "-m", "taskmajor.bootstrap.server"],
      "type": "stdio",
      "env": {
        "TASKMAJOR_TASKDATA": "/path/to/.task",
        "TASKMAJOR_TASKRC": "/path/to/.taskrc"
      }
    }
  }
}
```

### Troubleshooting

- **`uv` not found**: run `which uv`, use full path in `"command"` if needed
- **Connection refused**: restart VS Code after config changes
- **No tasks returned**: verify TaskWarrior works with `task list`

---

## Claude Code (CLI)

### Setup

1. Create or edit `~/.claude/mcp_servers.json`:

```json
{
  "taskMajor": {
    "command": "uv",
    "args": ["run", "-m", "taskmajor.bootstrap.server"],
    "type": "stdio"
  }
}
```

2. Run `claude` and ask: `What tasks do I have this week?`

### Custom data location or timeout

```json
{
  "taskMajor": {
    "command": "uv",
    "args": ["run", "-m", "taskmajor.bootstrap.server"],
    "type": "stdio",
    "timeout": 10,
    "env": {
      "TASKMAJOR_TASKDATA": "/path/to/.task",
      "TASKMAJOR_TASKRC": "/path/to/.taskrc"
    }
  }
}
```

### Troubleshooting

- **Directory missing**: `mkdir -p ~/.claude`
- **Permission denied**: `chmod 755 ~/.task && chmod 644 ~/.task/*.json ~/.taskrc`
- **Module not found**: test manually with `cd /path/to/taskmajor && uv run -m taskmajor.bootstrap.server`

---

## Cursor IDE

### Setup

1. Open Cursor Settings (`Cmd+,` / `Ctrl+,`), search `mcp`
2. Locate and edit `mcp_servers.json`:

```json
{
  "taskMajor": {
    "command": "uv",
    "args": ["run", "-m", "taskmajor.bootstrap.server"],
    "type": "stdio"
  }
}
```

3. Save and restart Cursor
4. Open Cursor Agent (`Cmd+K`) and ask: `Show me overdue tasks`

### Troubleshooting

- **`uv` not found**: use full path `"command": "/usr/local/bin/uv"`
- **Connection refused**: verify with `python -m taskmajor.bootstrap.server`
- **No tasks returned**: `task list` then `task sync`

---

## Hermes

Hermes connects via HTTP — TaskMajor must be running as a server (see [Start TaskMajor](#start-taskmajor) above).

### Setup

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  taskmajor:
    url: http://127.0.0.1:8888/mcp
    headers:
      Authorization: Bearer <your-token>
```

Then ask Hermes: `What are my tasks for today?`

### Troubleshooting

- **Connection refused**: ensure `uv run -m taskmajor.bootstrap.server` is running in a terminal
- **401 Unauthorized**: check the Bearer token value in your config
- **Wrong port**: verify `server_port` in `taskmajor/config/config.yaml` matches the URL

---

## Generic MCP Client

For any MCP-compatible client (Claude Desktop, custom tools, Anthropic SDK integrations):

```json
{
  "taskMajor": {
    "command": "uv",
    "args": ["run", "-m", "taskmajor.bootstrap.server"],
    "type": "stdio",
    "env": {
      "TASKMAJOR_LOG_LEVEL": "INFO"
    }
  }
}
```

Verify with the FastMCP inspector:
```bash
uv run fastmcp dev inspector taskmajor/bootstrap/core.py:main
```

---

## Common Patterns

```
"Add a task to fix the login bug"
"What's on my plate for today?"
"Mark the design review as done"
"Show me overdue tasks"
"Triage my inbox and set priorities"
"Switch to my @work context"
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TASKMAJOR_TASKDATA` | `~/.task_mcp` | TaskWarrior data directory |
| `TASKMAJOR_TASKRC` | `~/.taskrc_mcp` | TaskWarrior config file |
| `TASKMAJOR_LOG_LEVEL` | `INFO` | Log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `TASKMAJOR_SERVER_PORT` | `8888` | HTTP port (relevant for Hermes / HTTP clients) |

See [Configuration](../../getting-started/configuration.md) for the full list.

---

## What's Next?

- [API Reference](../../api-reference/index.md) — All tools and resources
- [Configuration](../../getting-started/configuration.md) — Advanced setup
- [Profiles](../profiles/profile-system.md) — Customize TaskMajor behavior
- [Contributing](../../developer/contributing.md) — Add a guide for your agent
