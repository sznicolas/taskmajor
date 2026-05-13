# GitHub Copilot Integration

> **For VS Code users:** Set up TaskMajor as an MCP server in Copilot Chat to manage tasks from your editor.

## Quick Setup (2 minutes)

### Step 1: Start TaskMajor

In a dedicated terminal, start the MCP server:

```bash
cd /path/to/taskmajor
python -m taskmajor.bootstrap.server
```

**Expected output:**
```
INFO:    Starting MCP server on stdio
INFO:    TaskMajor MCP Server ready
```

Leave this terminal running.

### Step 2: Configure VS Code

1. Open **VS Code Settings** (`Cmd+,` on macOS, `Ctrl+,` on Windows/Linux)
2. Search for: `@ext:github.copilot`
3. Look for **"Copilot Model Context"** or **"Model Context"** settings
4. Click **"Edit in settings.json"** (or open `.vscode/settings.json`)
5. Paste this configuration:

```json
{
  "github.copilot.chat.mcp": {
    "taskMajor": {
      "command": "uv",
      "args": ["run", "-m", "taskmajor.bootstrap.server"],
      "type": "stdio",
      "disabled": false
    }
  }
}
```

6. **Save** and restart VS Code

### Step 3: Test It

1. Open **Copilot Chat** in VS Code (`Cmd+Shift+I` / `Ctrl+Shift+I`)
2. Ask Copilot:
   ```
   Can you show me my tasks for today?
   ```
3. Copilot should list your tasks from TaskMajor

---

## What You Can Ask Copilot

Once connected, use natural language:

**Task Queries:**
- *"What's on my plate for today?"*
- *"Show me overdue tasks"*
- *"List all tasks tagged with @urgent"*

**Task Management:**
- *"Add a task: Review API design doc"*
- *"Mark the deployment as complete"*
- *"Delete the obsolete TODO item"*

**Workflow:**
- *"Triage my inbox and set priorities"*
- *"What's my next high-priority task?"*
- *"Set up a weekly review task"*

---

## Troubleshooting

### "Cannot find module 'uv'" / "command not found: uv"

**Problem:** VS Code can't find the `uv` command.

**Solution:**
1. Verify `uv` is installed: `which uv` in your terminal
2. If missing, install: `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. Or use explicit path in settings.json:
   ```json
   "command": "/usr/local/bin/uv"
   ```

### "TaskMajor not found" / "No module named taskmajor"

**Problem:** TaskMajor is not installed or not in the right location.

**Solution:**
1. Clone TaskMajor: `git clone https://github.com/yourusername/taskmajor.git`
2. Install: `cd taskmajor && uv sync`
3. Update settings.json to use full path to TaskMajor:
   ```json
   "args": ["run", "-m", "taskmajor.bootstrap.server"]
   ```

### "Connection refused" / Copilot chat hangs

**Problem:** MCP server isn't running or VS Code can't reach it.

**Solution:**
1. Ensure the MCP server is running in a terminal: `python -m taskmajor.bootstrap.server`
2. Check for errors in the MCP server terminal
3. Restart VS Code completely
4. Check that TaskWarrior is working: `task list` (should not error)

### "Permission denied"

**Problem:** TaskWarrior data files or `.task` directory is not readable.

**Solution:**
```bash
# Fix permissions
chmod 755 ~/.task
chmod 644 ~/.task/*.json
chmod 644 ~/.taskrc

# Or rebuild the task index
cd ~/.task
task sync
```

### Copilot lists tasks, but they're outdated

**Problem:** TaskMajor is reading cached data.

**Solution:**
1. Force TaskWarrior to sync: `task sync`
2. Restart the MCP server (stop and re-run)
3. Ask Copilot again

---

## Advanced Configuration

### Custom TaskWarrior Data Location

If you have multiple TaskWarrior configs or data directories:

```json
{
  "github.copilot.chat.mcp": {
    "taskMajor": {
      "command": "uv",
      "args": ["run", "-m", "taskmajor.bootstrap.server"],
      "type": "stdio",
      "env": {
        "TASKMAJOR_TASKDATA": "/path/to/my/.task",
        "TASKMAJOR_TASKRC": "/path/to/my/.taskrc"
      }
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

Then check VS Code's "Output" panel → "Copilot" for detailed logs.

### Multiple MCP Servers

You can connect multiple MCP servers to Copilot. Add more under `github.copilot.chat.mcp`:

```json
{
  "github.copilot.chat.mcp": {
    "taskMajor": { ... },
    "otherServer": {
      "command": "...",
      "args": [...],
      "type": "stdio"
    }
  }
}
```

---

## Tips & Tricks

**Tip 1: Combine with Code Context**
Ask Copilot to add a task based on code you're viewing:
```
Add a task to refactor the function I'm looking at (add a comment)
```

**Tip 2: Review Queue Integration**
Use the review queue for code reviews and design decisions:
```
Show me tasks in my review queue
```

**Tip 3: Quick Capture**
Quickly capture ideas without leaving your editor:
```
Add this to my inbox: Investigate performance regression
```

---

## Next Steps

- [API Reference](../../api-reference/index.md) — Learn all available tools and resources
- [Configuration](../../getting-started/configuration.md) — Customize TaskMajor behavior
- [Troubleshooting Guide](https://github.com/yourusername/taskmajor/issues) — More common issues

---

## Support

- **Issues?** Check the [Troubleshooting Guide](https://github.com/yourusername/taskmajor/issues)
- **Bugs or Feature Requests?** [Open an issue](https://github.com/yourusername/taskmajor/issues)
- **Want to Contribute?** See [Contributing Guide](../../developer/contributing.md)
