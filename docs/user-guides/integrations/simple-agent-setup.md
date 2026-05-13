# Quick Connect: Using TaskMajor with Your Favorite AI Agent

> **TL;DR**: TaskMajor is an MCP server for TaskWarrior. Connect it to Copilot, Claude Code, Cursor, or any MCP-compatible AI agent to manage tasks with natural language.

TaskMajor exposes all task operations via the Model Context Protocol (MCP), a standard interface that allows any AI agent to interact with your tasks using natural language.

## What You Can Do

Once connected, ask your agent:

- *"Add a task to fix the login bug"*
- *"What's on my plate for today?"*
- *"Mark the design review as done"*
- *"Show me overdue tasks"*
- *"Triage my inbox and set priorities"*

The agent will use TaskMajor to execute these commands on your TaskWarrior database.

---

## Prerequisites

1. **TaskWarrior installed**: TaskMajor requires the `task` command
   ```bash
   # macOS
   brew install task
   
   # Linux (Ubuntu/Debian)
   sudo apt-get install task
   
   # Or build from source: https://taskwarrior.org/download/build/
   ```

2. **TaskMajor installed**: Clone and set up
   ```bash
   git clone https://github.com/yourusername/taskmajor.git
   cd taskmajor
   uv sync  # or: pip install -e .
   ```

3. **Python 3.10+**: Required by TaskMajor

---

## Choose Your Agent

Select your AI agent to see copy-paste configuration instructions:

- **[GitHub Copilot (VS Code)](#github-copilot-vs-code)** — Built into VS Code, excellent integration
- **[Claude Code (CLI)](#claude-code-cli)** — Command-line Anthropic agent
- **[Cursor IDE](#cursor-ide)** — AI-first code editor
- **[Generic MCP Client](#generic-mcp-client)** — Any MCP-compatible tool

---

## GitHub Copilot (VS Code)

### Setup

1. **Start TaskMajor in a terminal**:
   ```bash
   cd /path/to/taskmajor
   uv run -m taskmajor.bootstrap.server
   ```
   
   Expected output:
   ```
   Starting MCP server on stdio
   TaskMajor MCP Server ready
   ```

2. **Configure VS Code settings.json**:

   Open VS Code settings (`Cmd+,` / `Ctrl+,`), search for `@ext:github.copilot`, and add:
   
   ```json
   {
     "github.copilot.modelContext.mcp": {
       "taskMajor": {
         "command": "uv",
         "args": ["run", "-m", "taskmajor.bootstrap.server"],
         "type": "stdio",
         "disabled": false
       }
     }
   }
   ```

3. **Test the connection**:
   
   Open Copilot Chat (Cmd+Shift+I / Ctrl+Shift+I) and ask:
   ```
   Can you check my TaskMajor tasks for today?
   ```

   Copilot should respond with today's tasks from TaskWarrior.

### Troubleshooting

- **"TaskMajor not found"**: Ensure `uv` is in your PATH. Run `which uv` to verify.
- **"Connection refused"**: Check that the MCP server is running in another terminal.
- **No tasks returned**: Verify TaskWarrior has tasks. Run `task list` in your terminal.

---

## Claude Code (CLI)

### Setup

1. **Start TaskMajor**:
   ```bash
   cd /path/to/taskmajor
   uv run -m taskmajor.bootstrap.server
   ```

2. **Configure Claude MCP servers** (~/.claude/mcp_servers.json):
   
   ```json
   {
     "taskMajor": {
       "command": "uv",
       "args": ["run", "-m", "taskmajor.bootstrap.server"],
       "type": "stdio"
     }
   }
   ```

3. **Test the connection**:
   
   ```bash
   claude
   ```
   
   Then ask:
   ```
   What tasks do I have this week?
   ```

### Troubleshooting

- **File not found (~/.claude/)**: Create the directory: `mkdir -p ~/.claude`
- **Permission denied**: Ensure MCP server executable: `chmod +x /path/to/taskmajor/taskmajor/server.py`
- **Connection timeout**: Increase timeout in mcp_servers.json if needed

---

## Cursor IDE

### Setup

1. **Start TaskMajor**:
   ```bash
   cd /path/to/taskmajor
   uv run -m taskmajor.bootstrap.server
   ```

2. **Configure Cursor settings.json** (Cmd+, / Ctrl+,):
   
   Search for `mcp` and add:
   ```json
   {
     "mcp.servers": {
       "taskMajor": {
         "command": "uv",
         "args": ["run", "-m", "taskmajor.bootstrap.server"],
         "type": "stdio"
       }
     }
   }
   ```

3. **Test with Cursor Agent**:
   
   Open Cursor's agent panel (Cmd+K / Ctrl+K) and ask:
   ```
   Show me overdue tasks
   ```

### Troubleshooting

- Check Cursor's MCP configuration file location (varies by OS)
- Restart Cursor after config changes
- Verify TaskMajor is responding: `python -m taskmajor.bootstrap.server --version`

---

## Generic MCP Client

If you use a different MCP client (e.g., Claude Desktop, Anthropic API, custom tool), TaskMajor follows the standard MCP protocol.

### Standard MCP Configuration

```json
{
  "taskMajor": {
    "command": "uv",
    "args": ["run", "-m", "taskmajor.bootstrap.server"],
    "type": "stdio",
    "env": {
      "TASKMAJOR_LOG_LEVEL": "info"
    }
  }
}
```

### Verify Connection (Manual Test)

Start TaskMajor and manually test with FastMCP inspector:

```bash
uv run fastmcp dev inspector taskmajor/bootstrap/core.py:main
```

This opens an interactive web UI where you can:
- Test tools (add_task, query_tasks, etc.)
- Read resources (taskmajor://agenda/today, taskmajor://config/schema)
- Verify the MCP server is working

---

## Common Patterns

### Pattern 1: Daily Standup
```
"What are my top 3 tasks for today?"
```

The agent will call `query_tasks(filters={status: pending}, sort=[-urgency])` and return your most urgent tasks.

### Pattern 2: Quick Capture
```
"Add a task: Review PR from Alice"
```

The agent will call `add_task(description="Review PR from Alice", project="Inbox")`.

### Pattern 3: Triage Inbox
```
"Show me tasks in the review queue and help me prioritize them"
```

The agent will call `query_tasks(filters={project: "Inbox"})` and guide you through triage.

### Pattern 4: Context Switching
```
"Switch to my @work context"
```

The agent will call `set_context(name="work")` to activate the work filter.

---

## Environment Variables

TaskMajor respects standard configuration via environment variables. The most common:

```bash
# TaskWarrior data location (default: ~/.task_mcp)
export TASKMAJOR_TASKDATA=~/.task_mcp

# TaskWarrior config location (default: ~/.taskrc_mcp)
export TASKMAJOR_TASKRC=~/.taskrc_mcp

# Log level (default: INFO)
export TASKMAJOR_LOG_LEVEL=DEBUG
```

See [Configuration](../../getting-started/configuration.md) for the full list.

---

## What's Next?

### Learn the API
- [Resources](../../api-reference/resources.md) — Read-only task views (`taskmajor://agenda/today`, etc.)
- [Tools](../../api-reference/tools.md) — Actions your agent can perform
- [API Reference](../../api-reference/index.md) — Complete documentation

### Advanced Setup
- [Configuration](../../getting-started/configuration.md) — Customize behavior with env vars
- [Observability](../../developer/observability.md) — Enable tracing and metrics

### Troubleshooting
- [Common Issues](#troubleshooting) — Permissions, paths, connection errors

---

## Need Help?

- **Something not working?** Check [Troubleshooting](#troubleshooting)
- **Want to contribute an agent guide?** See [Contributing](../../developer/contributing.md)
- **Bug or feature request?** Open an [issue on GitHub](https://github.com/yourusername/taskmajor/issues)
