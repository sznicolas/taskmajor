# Contribution Path: Adding a New Agent Integration

> **Interested in adding TaskMajor support for your favorite AI agent?** This guide walks you through creating a new integration guide and contributing it back.

## Why Contribute?

By adding a new agent integration guide, you:
- Help other users get TaskMajor working with their tool
- Make TaskMajor more accessible to a broader audience
- Establish your agent as MCP-compatible
- Become part of the TaskMajor community

---

## Before You Start

### What We're Looking For

We accept integration guides for:
- **Popular AI agents/coding assistants** — Copilot, Claude, Cursor, etc.
- **Custom tools** that support MCP (Model Context Protocol)
- **Platform-specific setups** — if your agent differs from generic MCP

We're looking for clear, copy-paste-ready configuration guides with:
- Prerequisites listed
- Step-by-step setup
- Common troubleshooting
- At least one working example

### What We're Not Looking For

- Guides for tools that don't support MCP
- Outdated or unmaintained tools
- Advertising or promotional content
- Incomplete or untested guides

---

## Submission Process

### Step 1: Check Existing Guides

Look in `docs/user-guides/integrations/` to see if your agent is already documented:

```bash
ls -la docs/user-guides/integrations/
```

If it exists, you can:
- Open a PR to improve it
- Add a subsection (e.g., "Cursor IDE Enterprise Edition")

If it doesn't exist, continue to Step 2.

### Step 2: Create Your Guide

Use this **template** as a starting point:

```markdown
# [Agent Name] Integration

> **For [Agent Type] users:** Set up TaskMajor as an MCP server to manage tasks from [Your Tool].

## Quick Setup (2 minutes)

### Step 1: Start TaskMajor

(Copy from another guide, adapt if needed)

### Step 2: Configure [Agent]

(Specific config instructions for your agent)

### Step 3: Test It

(Copy-paste test command and expected output)

## What You Can Ask [Agent]

(Examples of natural language requests)

## Configuration

(Advanced setup, env vars, etc.)

## Troubleshooting

(Common issues and solutions)

## Tips & Tricks

(Unique features or workflows)

## Next Steps

(Links to API Reference, other guides)
```

### Step 3: Test Your Guide

Before submitting, **test every step**:

1. Follow your guide on a fresh machine or VM
2. Verify each code snippet works
3. Try the examples you provide
4. Check all links
5. Ensure no typos or formatting issues

### Step 4: Compare with Existing Guides

Check [GitHub Copilot](../user-guides/integrations/copilot.md) or [Claude Code](../user-guides/integrations/claude-code.md) for:
- Tone and style
- Section structure
- Troubleshooting format
- Link conventions

Match the style so the documentation feels cohesive.

### Step 5: Submit a Pull Request

1. **Fork the repository:**
   ```bash
   git clone https://github.com/yourusername/taskmajor.git
   cd taskmajor
   git checkout -b add/integration-[agent-name]
   ```

2. **Create your guide:**
   ```bash
   touch docs/user-guides/integrations/[agent-name].md
   # Write the guide (use the template above)
   git add docs/user-guides/integrations/[agent-name].md
   git commit -m "Add [Agent Name] integration guide"
   ```

3. **Update mkdocs.yml** to include your guide in the Quick Start section:

   ```yaml
   - Quick Start:
       - Simple Agent Setup: user-guides/integrations/simple-agent-setup.md
       - GitHub Copilot: user-guides/integrations/copilot.md
       - Claude Code: user-guides/integrations/claude-code.md
       - Cursor IDE: user-guides/integrations/cursor.md
       - [Agent Name]: user-guides/integrations/[agent-name].md  # NEW
       - Generic MCP Client: user-guides/integrations/generic-mcp.md
   ```

4. **Push and create PR:**
   ```bash
   git push origin add/integration-[agent-name]
   ```

   Go to GitHub and [create a Pull Request](https://github.com/yourusername/taskmajor/pulls).

5. **Respond to feedback:**

   Maintainers may request changes. Be ready to:
   - Fix typos or formatting
   - Add missing sections
   - Clarify unclear instructions
   - Update broken links

---

## Template: Full Integration Guide

Copy this template to get started:

```markdown
# [Your Agent] Integration

> **For [Your Agent] users:** Set up TaskMajor as an MCP server to manage tasks from [Your Agent].

## Quick Setup ([X] minutes)

### Step 1: Start TaskMajor

In a dedicated terminal, start the MCP server:

\`\`\`bash
cd /path/to/taskmajor
uv run -m taskmajor.server
\`\`\`

**Expected output:**
\`\`\`
INFO:    Starting MCP server on stdio
INFO:    TaskMajor MCP Server ready
\`\`\`

Leave this terminal running.

### Step 2: Configure [Your Agent]

[Write specific configuration steps here. Include file paths, config format, etc.]

### Step 3: Test It

[Provide copy-paste test command and expected result]

## What You Can Ask [Your Agent]

(Provide 3-5 example queries)

## Configuration

(Environment variables, advanced setup, multiple instances)

## Troubleshooting

(Common errors and solutions)

## Tips & Tricks

(Unique workflows or integrations)

## Next Steps

- [Simple Agent Setup](../user-guides/integrations/simple-agent-setup.md)
- [API Reference](../api-reference/index.md)

## Support

- **Questions?** See [Troubleshooting](https://github.com/yourusername/taskmajor/issues)
- **Bug report?** [Open an issue](https://github.com/yourusername/taskmajor/issues)
```

---

## Style Guidelines

### Tone

- **Professional and welcoming**
- Assume reader is new to TaskMajor
- Use simple, clear language
- No jargon without explanation

### Format

- **Use headers for sections** (H2 and H3, not H1)
- **Copy-paste code blocks** — test each one
- **Numbered steps** for instructions
- **Bullet points** for lists
- **Bold** for important terms first mention
- **Code formatting** for commands, file paths, env vars

### Examples

```markdown
# ❌ Bad: Unclear, no structure
Just configure your agent with the MCP server. Update settings and test.

# ✅ Good: Clear, structured
### Step 1: Start TaskMajor

In a terminal, run:

\`\`\`bash
cd /path/to/taskmajor
uv run -m taskmajor.server
\`\`\`

Then configure your agent (see Step 2).
```

---

## Links & References

When linking to other parts of TaskMajor, use relative paths:

```markdown
# ❌ Bad (absolute URL)
[Configuration](https://taskmajor.readthedocs.io/getting-started/configuration/)

# ✅ Good (relative path)
[Configuration](../getting-started/configuration.md)
[API Reference](../api-reference/index.md)
[Troubleshooting](https://github.com/yourusername/taskmajor/issues)
```

---

## Common Mistakes to Avoid

| Mistake | Impact | Fix |
|---------|--------|-----|
| Untested code snippets | Readers waste time debugging | Test every command |
| Missing prerequisites | Setup fails halfway | List all requirements upfront |
| Broken links | Users can't find help | Use relative paths, test links |
| Too much jargon | Non-technical users confused | Define terms, provide context |
| No troubleshooting | Users give up | Include common issues & solutions |
| Incomplete setup | Doesn't work for everyone | Add all required configuration steps |

---

## Examples

### Good Introduction
```markdown
> **For VS Code users:** Add TaskMajor as an MCP server in Copilot Chat to ask for your tasks without leaving your editor.
```

### Good Prerequisites
```markdown
## Prerequisites

1. **TaskWarrior installed**: Required by TaskMajor
   \`\`\`bash
   which task
   \`\`\`

2. **TaskMajor installed**: Clone and set up
   \`\`\`bash
   git clone https://github.com/yourusername/taskmajor.git
   cd taskmajor
   uv sync
   \`\`\`
```

### Good Troubleshooting
```markdown
### "Cannot find module 'uv'"

**Problem:** Agent says `uv` is not found.

**Solutions:**

1. Check if installed: \`which uv\`
2. If not, install: \`curl -LsSf https://astral.sh/uv/install.sh | sh\`
3. Use full path: \`command: "/usr/local/bin/uv"\`
```

---

## Getting Help

### Before You Submit

- Check [existing guides](../user-guides/integrations/simple-agent-setup.md) for style and structure
- Read this guide top to bottom
- Test your guide on a fresh setup
- Verify all links work

### While Contributing

- Comment on related issues (if any) to coordinate
- Be open to feedback and suggestions
- Respond promptly to maintainer questions

### After Submission

- Update your agent's documentation to link to the guide
- Help other users using the same integration

---

## Recognition

Contributors who add agent integration guides will be:
- Listed in the guide (with credit/link)
- Recognized in the [CHANGELOG](../changelog.md)
- Listed in the README (coming soon)

---

## Questions?

- **How do I get started?** Read the template above and follow the submission process
- **What if my agent isn't officially supported?** Submit a PR anyway! We'll review it
- **Can I update an existing guide?** Yes! Open a PR with improvements
- **Who reviews contributions?** The TaskMajor maintainers. See [Contributing](contributing.md)

---

## Next Steps

1. **Read the template** (above)
2. **Create your guide** using `docs/user-guides/integrations/[agent-name].md`
3. **Test thoroughly** on a clean setup
4. **Submit a PR** with your guide and mkdocs.yml update
5. **Respond to feedback** from maintainers

---

## Additional Resources

- [Simple Agent Setup](../user-guides/integrations/simple-agent-setup.md) — Overview of all supported agents
- [API Reference](../api-reference/index.md) — TaskMajor capabilities to document
- [Contributing Guide](contributing.md) — General contribution guidelines
- [GitHub Copilot Guide](../user-guides/integrations/copilot.md) — Example of a complete guide
