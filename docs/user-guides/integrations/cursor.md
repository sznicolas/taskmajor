# Cursor IDE Integration

> **For Cursor users:** Set up TaskMajor as an MCP server in Cursor to manage tasks from your AI-first IDE.

## Quick Setup (2 minutes)

### Step 1: Start TaskMajor

In a dedicated terminal, start the MCP server:

```bash
cd /path/to/taskmajor
uv run -m taskmajor.server
```

**Expected output:**
```
INFO:    Starting MCP server on stdio
INFO:    TaskMajor MCP Server ready
```

Leave this terminal running.

### Step 2: Configure Cursor

1. Open **Cursor Settings** (`Cmd+,` on macOS, `Ctrl+,` on Windows/Linux)
2. Search for: `mcp`
3. Look for **"MCP Servers"** or **"Model Context Servers"**
4. Find the `mcp_servers.json` file location (usually shown in settings)
5. Edit `mcp_servers.json` and add:

```json
{
  "taskMajor": {
    "command": "uv",
    "args": ["run", "-m", "taskmajor.server"],
    "type": "stdio"
  }
}
```

6. **Save** and restart Cursor

### Step 3: Test It

1. Open **Cursor Agent** (usually `Cmd+K` or `Ctrl+K`)
2. Ask:
   ```
   Show me my tasks for today
   ```
3. Cursor should retrieve your tasks from TaskMajor

---

## Cursor-Specific Features

### Integration with Code Context

Cursor can use TaskMajor alongside your code:

```
Create a task based on this TODO comment
```

Cursor will understand the code context and add relevant task descriptions.

### Inline Task Insertion

While editing code, ask Cursor:
```
Add a task reminder for when I've finished this function
```

### Agent-Driven Development

Use Cursor Agent with TaskMajor for workflow integration:

```
What's my next task? Let's tackle it together.
```

---

## Configuration

### Custom TaskWarrior Data Location

```json
{
  "taskMajor": {
    "command": "uv",
    "args": ["run", "-m", "taskmajor.server"],
    "type": "stdio",
    "env": {
      "TASKMAJOR_TASKDATA": "/path/to/my/.task",
      "TASKMAJOR_TASKRC": "/path/to/my/.taskrc"
    }
  }
}
```

### Enable Debug Logging

```json
{
  "env": {
    "TASKMAJOR_LOG_LEVEL": "DEBUG"
  }
}
```

Logs appear in Cursor's output panel.

---

## Troubleshooting

### "Cannot find module 'uv'"

**Problem:** Cursor can't locate `uv`.

**Solution:**
1. Verify: `which uv`
2. Install if missing: `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. Use full path: `"command": "/usr/local/bin/uv"`

### "TaskMajor not found"

**Problem:** TaskMajor installation not accessible.

**Solution:**
1. Ensure TaskMajor is installed: `cd /path/to/taskmajor && uv sync`
2. Test manually: `uv run -m taskmajor.server`
3. Use full path in mcp_servers.json

### "Connection refused"

**Problem:** MCP server not running or Cursor can't reach it.

**Solution:**
1. Verify the MCP server is running: `python -m taskmajor.bootstrap.server`
2. Check for errors in the terminal
3. Restart Cursor completely
4. Verify TaskWarrior works: `task list`

### No tasks returned

**Problem:** Cursor connects but no tasks appear.

**Solution:**
1. Check TaskWarrior: `task list`
2. Sync: `task sync`
3. Restart MCP server
4. Try again

---

## Tips & Tricks

**Tip 1: Multi-file Workflows**
Ask Cursor to review multiple files and create a checklist task:
```
Review these files and create a task with notes on refactoring
```

**Tip 2: Code Comments → Tasks**
Let Cursor find TODOs and create corresponding tasks:
```
Find all TODO comments in this file and create tasks for each
```

**Tip 3: Sprint Planning**
Use TaskMajor with Cursor's code understanding:
```
Based on the code I'm working on, what should my priorities be?
```

---

## Next Steps

- [Simple Agent Setup](simple-agent-setup.md) — General MCP setup guide
- [API Reference](../../api-reference/index.md) — Learn available tools and resources
- [Configuration](../../getting-started/configuration.md) — Customize TaskMajor behavior

---

## Support

- **Questions?** Check [Troubleshooting](https://github.com/yourusername/taskmajor/issues)
- **Found an issue?** [Report it](https://github.com/yourusername/taskmajor/issues)
- **Want to help?** See [Contributing](../../development/contribution-path.md)
