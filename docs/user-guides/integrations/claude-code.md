# Claude Code Integration

> **For Claude users:** Connect TaskMajor to Claude Code (CLI or web) to manage tasks from your development workflow.

## Quick Setup (3 minutes)

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

### Step 2: Configure Claude MCP Servers

Claude looks for MCP server definitions in `~/.claude/mcp_servers.json`.

1. Create the directory if it doesn't exist:
   ```bash
   mkdir -p ~/.claude
   ```

2. Create or edit `~/.claude/mcp_servers.json`:
   ```json
   {
     "taskMajor": {
       "command": "uv",
       "args": ["run", "-m", "taskmajor.server"],
       "type": "stdio"
     }
   }
   ```

3. **Save** the file

### Step 3: Test It

#### Claude CLI

```bash
claude
```

Then ask:
```
What tasks do I have this week?
```

Claude should retrieve your tasks from TaskMajor.

#### Claude Web / VS Code Extension

If using Claude through web or IDE extensions, the configuration may differ. Check your Claude client's documentation for MCP server setup.

---

## What You Can Ask Claude

Once connected, use natural language:

**Task Queries:**
- *"List my tasks for today"*
- *"Show me overdue items"*
- *"What's tagged with @code-review?"*

**Task Creation:**
- *"Add a task: Set up CI/CD pipeline"*
- *"Create a reminder: Schedule 1:1 with Alice"*

**Task Management:**
- *"Mark the design review as done"*
- *"Move the deployment task to Thursday"*
- *"Delete the archived todos"*

**Workflow:**
- *"What's my highest-priority task right now?"*
- *"Help me review and prioritize my inbox"*
- *"Create my weekly planning list"*

---

## Configuration

### Custom TaskWarrior Data Location

If you store TaskWarrior data in a non-standard location:

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

Add to the `env` section:

```json
"env": {
  "TASKMAJOR_LOG_LEVEL": "DEBUG"
}
```

Logs will appear in Claude's output.

### Timeout Configuration

If Claude times out when querying tasks, increase the timeout:

```json
{
  "taskMajor": {
    "command": "uv",
    "args": ["run", "-m", "taskmajor.server"],
    "type": "stdio",
    "timeout": 10
  }
}
```

---

## Troubleshooting

### "Cannot find module 'uv'"

**Problem:** Claude can't locate the `uv` command.

**Solution:**
1. Check if `uv` is installed: `which uv`
2. If not, install: `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. Use the full path in mcp_servers.json:
   ```json
   "command": "/usr/local/bin/uv"
   ```

### "TaskMajor not found" / Module not found error

**Problem:** TaskMajor is not installed or not accessible from the specified path.

**Solution:**
1. Verify TaskMajor is installed: `ls -la /path/to/taskmajor/taskmajor/`
2. Test the command manually:
   ```bash
   cd /path/to/taskmajor
   uv run -m taskmajor.server
   ```
3. If this works, update `mcp_servers.json` with the absolute path to TaskMajor

### "Connection timeout" / Server doesn't respond

**Problem:** The MCP server is not running or not responding.

**Solution:**
1. Ensure the server is running in another terminal: `uv run -m taskmajor.server`
2. Check for errors in the server terminal
3. Verify TaskWarrior is working: `task list` (should not produce errors)
4. Restart Claude
5. Increase timeout in mcp_servers.json

### No tasks returned / Empty task list

**Problem:** Claude connects but returns no tasks.

**Solution:**
1. Verify TaskWarrior has tasks: `task list`
2. Check TaskWarrior status: `task --version && task --help`
3. Sync TaskWarrior: `task sync`
4. Restart the MCP server
5. Try again

### "Permission denied"

**Problem:** TaskWarrior files are not readable by Claude.

**Solution:**
```bash
# Fix permissions on TaskWarrior data
chmod 755 ~/.task
chmod 644 ~/.task/*.json
chmod 644 ~/.taskrc
```

---

## Advanced Usage

### Multiple TaskWarrior Contexts

Configure multiple MCP servers if you have separate task databases:

```json
{
  "taskMajor-work": {
    "command": "uv",
    "args": ["run", "-m", "taskmajor.server"],
    "type": "stdio",
    "env": {
      "TASKMAJOR_TASKDATA": "~/.task_work"
    }
  },
  "taskMajor-personal": {
    "command": "uv",
    "args": ["run", "-m", "taskmajor.server"],
    "type": "stdio",
    "env": {
      "TASKMAJOR_TASKDATA": "~/.task_personal"
    }
  }
}
```

Then ask Claude:
```
Using the taskMajor-work server, show me my work tasks
```

### Combining with Other MCP Servers

You can use TaskMajor alongside other MCP servers:

```json
{
  "taskMajor": { ... },
  "webSearch": { ... },
  "codeInterpreter": { ... }
}
```

Claude will use the appropriate server for each query.

---

## Tips

**Tip 1: Ask for Task Context**
```
Show me my tasks and help me plan my day
```
Claude will use TaskMajor to retrieve tasks and provide personalized suggestions.

**Tip 2: Use for Code-Related Tasks**
```
I'm reviewing this PR. Add a task to follow up on the comments.
```
Claude can create task descriptions based on code context.

**Tip 3: Bulk Operations**
```
Archive all tasks tagged @completed
```
Claude can execute complex workflows using TaskMajor's query and update tools.

---

## Next Steps

- [API Reference](../../api-reference/index.md) — Learn all available tools and resources
- [Configuration](../../getting-started/configuration.md) — Customize TaskMajor behavior
- [Troubleshooting Guide](https://github.com/yourusername/taskmajor/issues) — More common issues

---

## Support

- **Need help?** Check the [Troubleshooting Guide](https://github.com/yourusername/taskmajor/issues)
- **Found a bug?** [Open an issue](https://github.com/yourusername/taskmajor/issues)
- **Want to contribute?** See [Contributing Guide](../../development/contribution-path.md)
