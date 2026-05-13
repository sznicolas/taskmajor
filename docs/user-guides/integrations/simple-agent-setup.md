# Connect TaskMajor to Your AI Agent

> **TL;DR**: TaskMajor is an MCP server for TaskWarrior. Start it once (or configure your agent to launch it), then connect Copilot, Claude Code, Cursor, Hermes, or any MCP-compatible agent.

See `doc_agents/AGENT_CONFIGURATION.md` for details on transport selection (`--transport`) and how `stdio` differs from network transports.

## Prerequisites

- **TaskWarrior v3.0+**: `brew install task` (macOS) or [taskwarrior.org/download](https://taskwarrior.org/download/)
- **TaskMajor installed**: `git clone … && uv sync`
- **Python 3.10+`

## Start TaskMajor

TaskMajor can be started manually for network-based agents, or launched by the agent process for stdio-based integrations.

Start with defaults (config.yaml or TaskMajor defaults):

```bash
cd /path/to/taskmajor
uv run -m taskmajor.bootstrap.server --help  # view available CLI flags like --transport
```

Start server explicitly (network transport):

```bash
uv run -m taskmajor.bootstrap.server --transport streamable-http --server-port 8888
```

Start server for stdio-based integrations (usually the agent will launch this for you):

```bash
uv run -m taskmajor.bootstrap.server --transport stdio
```

Important: when using `--transport stdio` the server is not a network server — `--server-port` and `--server-host` are ignored. See `doc_agents/AGENT_CONFIGURATION.md` for details.

---

## Hermes

Hermes connects via HTTP — TaskMajor must be running as a network server (see [Start TaskMajor](#start-taskmajor)). Use a network transport such as `streamable-http`.

### Setup

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  taskmajor:
    url: http://127.0.0.1:8888/mcp
    headers:
      Authorization: Bearer <your-token>
```

Start TaskMajor with a network transport if not launched by the agent:

```bash
uv run -m taskmajor.bootstrap.server --transport streamable-http --server-port 8888
```

Then ask Hermes: `What are my tasks for today?`

### Troubleshooting

- **Connection refused**: ensure TaskMajor was started with a network transport and is listening on the configured port
- **401 Unauthorized**: check the Bearer token value in your config
- **Wrong port**: verify `--server-port` or `server_port` in `taskmajor/config/config.yaml` matches the URL

---

## GitHub Copilot (VS Code)

Copilot's VS Code integration typically expects an MCP server exposed over stdio and often starts the server as a subprocess. The configuration below instructs Copilot to run TaskMajor on stdin/stdout.

### Setup

1. Open VS Code Settings (`Cmd+,` / `Ctrl+,`), search `@ext:github.copilot`
2. Click **Edit in settings.json** and add:

```json
{
  "github.copilot.chat.mcp": {
    "taskMajor": {
      "command": "uv",
      "args": ["run", "-m", "taskmajor.bootstrap.server", "--transport", "stdio"],
      "type": "stdio"
    }
  }
}
```

3. Save and restart VS Code
4. Open Copilot Chat (`Cmd+Shift+I`) and ask: `What's on my plate today?`

### Custom data location

When the agent launches the server subprocess, you can pass environment variables to configure TaskMajor's TaskWarrior data location:

```json
{
  "github.copilot.chat.mcp": {
    "taskMajor": {
      "command": "uv",
      "args": ["run", "-m", "taskmajor.bootstrap.server", "--transport", "stdio"],
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
- **Connection refused / empty responses**: if Copilot launches the server, check the extension logs; otherwise start the server manually with `--transport stdio` to reproduce and inspect logs
- **No tasks returned**: verify TaskWarrior works with `task list`

---

## Claude Code (CLI)

### Setup

1. Create or edit `~/.claude/mcp_servers.json` and specify stdio transport so the CLI can start TaskMajor as a subprocess:

```json
{
  "taskMajor": {
    "command": "uv",
    "args": ["run", "-m", "taskmajor.bootstrap.server", "--transport", "stdio"],
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
    "args": ["run", "-m", "taskmajor.bootstrap.server", "--transport", "stdio"],
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
2. Locate and edit `mcp_servers.json` and prefer stdio for editor-integrated agents:

```json
{
  "taskMajor": {
    "command": "uv",
    "args": ["run", "-m", "taskmajor.bootstrap.server", "--transport", "stdio"],
    "type": "stdio"
  }
}
```

3. Save and restart Cursor
4. Open Cursor Agent (`Cmd+K`) and ask: `Show me overdue tasks`

### Troubleshooting

- **`uv` not found**: use full path `"command": "/usr/local/bin/uv"`
- **Connection refused**: verify with `python -m taskmajor.bootstrap.server` or run with `--transport stdio` to reproduce editor-launched behavior
- **No tasks returned**: `task list` then `task sync`

---


## Generic MCP Client

For any MCP-compatible client (Claude Desktop, custom tools, Anthropic SDK integrations), prefer stdio for local, editor-launched agents, and a network transport for remote clients.

```json
{
  "taskMajor": {
    "command": "uv",
    "args": ["run", "-m", "taskmajor.bootstrap.server", "--transport", "stdio"],
    "type": "stdio",
    "env": {
      "TASKMAJOR_LOG_LEVEL": "INFO"
    }
  }
}
```

Verify with the FastMCP inspector (developer tool):
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
