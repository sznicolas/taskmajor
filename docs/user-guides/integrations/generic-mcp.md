# Generic MCP Client Setup

> For MCP clients not covered by specific agent guides (e.g., Claude Desktop, custom tools, Anthropic API integrations).

## Standard MCP Configuration

TaskMajor follows the **Model Context Protocol (MCP)** standard, which most AI tools support. The basic configuration pattern is:

```json
{
  "taskMajor": {
    "command": "uv",
    "args": ["run", "-m", "taskmajor.server"],
    "type": "stdio"
  }
}
```

## Common MCP Configuration Locations

| Client | Config File | Notes |
|--------|------------|-------|
| **Claude Desktop** | `~/.claude/mcp_servers.json` | See Claude Desktop setup below |
| **Anthropic API** | Environment variable or SDK config | Requires API key; see docs |
| **Custom Tools** | Your tool's MCP config file | Depends on tool implementation |
| **Codebase Context** | `.mcp.json` or `mcp_config.json` | Project-specific config |

---

## Claude Desktop

Claude Desktop (formerly Claude for Slack/Web) uses MCP servers defined in `~/.claude/mcp_servers.json`.

### Setup

1. Create the config directory:
   ```bash
   mkdir -p ~/.claude
   ```

2. Edit `~/.claude/mcp_servers.json`:
   ```json
   {
     "taskMajor": {
       "command": "uv",
       "args": ["run", "-m", "taskmajor.server"],
       "type": "stdio"
     }
   }
   ```

3. Restart Claude Desktop

4. Test by asking:
   ```
   What tasks do I have this week?
   ```

---

## Custom Integration

If you're building a custom integration or using an MCP client not listed above:

### 1. Prerequisites

- **uv installed**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **TaskMajor installed**: `cd /path/to/taskmajor && uv sync`
- **MCP client** that supports stdio communication

### 2. Verify TaskMajor Works

Test manually:

```bash
cd /path/to/taskmajor
python -m taskmajor.bootstrap.server
```

If it starts without error, you're ready to configure your client.

### 3. Configure Your Client

Add TaskMajor to your MCP client's config:

```json
{
  "taskMajor": {
    "command": "uv",
    "args": ["run", "-m", "taskmajor.server"],
    "type": "stdio"
  }
}
```

### 4. With Environment Variables

If you need to customize TaskWarrior data location or logging:

```json
{
  "taskMajor": {
    "command": "uv",
    "args": ["run", "-m", "taskmajor.server"],
    "type": "stdio",
    "env": {
      "TASKMAJOR_TASKDATA": "~/.task",
      "TASKMAJOR_TASKRC": "~/.taskrc",
      "TASKMAJOR_LOG_LEVEL": "INFO"
    }
  }
}
```

---

## Anthropic API Integration (Advanced)

If integrating TaskMajor with Anthropic's API directly:

### Using Claude SDK (Python)

```python
from anthropic import Anthropic
import subprocess
import json

# Start TaskMajor server (ensure it's running)
# subprocess.Popen(["uv", "run", "-m", "taskmajor.server"])

client = Anthropic()

# MCP server configuration
mcp_config = {
    "taskMajor": {
        "command": "uv",
        "args": ["run", "-m", "taskmajor.server"],
        "type": "stdio"
    }
}

# Create message with MCP tools
response = client.messages.create(
    model="claude-opus-4-1",
    max_tokens=1024,
    tools=[
        {
            "type": "computer_use",
            "name": "task_management",
            "description": "TaskMajor task management"
        }
    ],
    messages=[
        {
            "role": "user",
            "content": "Show me my tasks for today"
        }
    ]
)

print(response.content)
```

**Note:** Requires Anthropic API key and SDK. See [Anthropic Python SDK docs](https://github.com/anthropics/anthropic-sdk-python).

---

## Verify Connection

Use the FastMCP inspector to test without a full client:

```bash
cd /path/to/taskmajor
uv run fastmcp dev inspector taskmajor/bootstrap/core.py:main
```

This opens a web UI at `http://localhost:8000` where you can:

- Test each tool (add_task, query_tasks, etc.)
- Read each resource (taskmajor://agenda/today, etc.)
- See the metadata contract
- Debug connection issues

---

## Debugging

### Enable verbose logging

```bash
TASKMAJOR_LOG_LEVEL=DEBUG python -m taskmajor.bootstrap.server
```

### Check MCP server output

Add to your config:

```json
{
  "taskMajor": {
    "command": "uv",
    "args": ["run", "-m", "taskmajor.server"],
    "type": "stdio",
    "logfile": "/tmp/taskmajor-mcp.log"
  }
}
```

Then check logs: `tail -f /tmp/taskmajor-mcp.log`

---

## Troubleshooting

### "Connection refused"

1. Ensure TaskMajor server is running
2. Check firewall rules (if using network instead of stdio)
3. Verify `uv` is installed and in PATH

### "Module not found"

1. Verify TaskMajor installation: `cd /path/to/taskmajor && uv sync`
2. Use full path to TaskMajor in command

### "No output from server"

1. Test manually: `python -m taskmajor.bootstrap.server`
2. Check for error messages in terminal
3. Verify TaskWarrior is installed: `which task`

---

## API Reference

Once connected, TaskMajor exposes:

### Resources (Read-Only)
- `taskmajor://agenda/today` — Tasks due today
- `taskmajor://agenda/week` — Tasks this week
- `taskmajor://status/overdue` — Overdue tasks
- `taskmajor://queue/unsorted` — Review queue
- `taskmajor://analytics/summary` — Task aggregates
- `taskmajor://config/schema` — API self-description

### Tools (Callable)
- `query_tasks(filters, sort, limit, offset)` — Search tasks
- `add_task(task_input)` — Create task (use `project: Inbox` for quick capture)
- `update_task(task_id, task_input)` — Modify or triage task (requires ≥1 field change)
- `done_task(task_id)` — Complete task
- `delete_task(task_id)` — Delete task

See [API Reference](../../api-reference/index.md) for details.

---

## What's Next?

- [Simple Agent Setup](simple-agent-setup.md) — Agent-specific guides
- [API Reference](../../api-reference/index.md) — Complete tool and resource documentation
- [Configuration](../../getting-started/configuration.md) — Environment variables and advanced setup
- [Troubleshooting](https://github.com/yourusername/taskmajor/issues) — Common issues and solutions

---

## Support

- **Having trouble?** Check [Troubleshooting](https://github.com/yourusername/taskmajor/issues)
- **Want to contribute a guide for your client?** [Contribute](../../development/contribution-path.md)
- **Found a bug?** [Report it](https://github.com/yourusername/taskmajor/issues)
