# TaskMajor — Manage Tasks with Any AI Agent

[![CI Tests](https://github.com/nschmeltz/taskmajor/workflows/CI/badge.svg)](https://github.com/nschmeltz/taskmajor/actions/workflows/ci.yml)
[![Coverage Status](https://img.shields.io/badge/coverage-61%25-brightgreen)](docs/TESTING.md#coverage)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-v0.1-blueviolet)](#mcp-model-context-protocol)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](#license)

> **TaskMajor MCP. Coordinate your tasks. Execute with precision.**

---

> **TaskMajor MCP. Coordinate your tasks. Execute with precision.**

TaskMajor connects your AI assistants to your task management—organized your way, hosted on your terms.

Ask your assistant:
```
"Add a task to review the API spec"
"What's on my plate for today?"
"Run my daily review"
"Show me the roadmap for Project X"
```

Behind this sits [**TaskWarrior**](https://taskwarrior.org)—a remarkably flexible, battle-tested task engine. It runs locally, stores plain text, and bends to almost any organizational style. TaskMajor builds on that foundation and adds its own layer of adaptability: the **profile system**. Each profile defines a unique contract of exposed tools, views, and behaviors—turning TaskMajor into anything from a simple to-do list to a full GTD system or a multi-agent coordination hub. Explore the [built-in profiles](docs/user-guides/profiles/profile-system.md) or learn how to compose and extend them in the [profile documentation](docs/user-guides/profiles/profile-system.md).

Ready to transform your task management? Jump straight into the [Quick Start](#quick-start) to get running in minutes.

## 🚀 Quick Start

### Prerequisites

- **TaskWarrior v3.0+** is required.
  - **macOS**: `brew install task`
  - **Linux/Windows**: Download from [taskwarrior.org](https://taskwarrior.org/download/)
  - **Alternative**: If you cannot install TaskWarrior locally, use the **Docker** option below which includes a bundled version.
- **Python 3.10+**
- **uv** (recommended) or **pip**

### Installation & Running

1. **Clone and Install**
   ```bash
   git clone https://github.com/nschmeltz/taskmajor.git
   cd taskmajor
   uv sync
   ```
   *(Or use `pip install -e .`)*

2. **Configure for Existing Users**
   > **Important for TaskWarrior users:** If you already have a TaskWarrior database, you **must** edit `taskmajor/config/config.yaml` to point to your existing `.taskrc` and data directory.
   >
   > ```yaml
   > # taskmajor/config/config.yaml
   > taskrc: /path/to/your/.taskrc
   > taskdata: /path/to/your/.task
   > ```
   > *If you skip this, TaskMajor will initialize a new, empty database.*

3. **Launch the Server**
   ```bash
   uv run -m taskmajor.bootstrap.server # --help to view overridable options in CLI
   ```
   You should see: `INFO: TaskMajor MCP Server ready`.

4. **Connect Your Agent**
   That's it. Now, simply configure your AI agent (Copilot, Claude, Cursor) to connect to this local MCP server. See the **[Quick Connect Guide](docs/user-guides/integrations/simple-agent-setup.md)** for copy-paste snippets for your specific editor.

### Docker Option
If you prefer containerization or need a bundled TaskWarrior instance:
```bash
docker build -t taskmajor . && docker run -d -v -p 8888:8888 taskmajor
```
*Remember to mount your `config.yaml` and TaskWarrior data directory if you want to persist data.*

---

## ⚙️ Adapt It to Your Methodology

TaskMajor ships with ready-made profiles—and gives you the building blocks to create your own.

### Built-In Profiles

| Profile | Best For | What It Adds |
|---------|----------|--------------|
| **base** | Minimalists | Essential CRUD, pending-tasks view, date/text rules |
| **standard** | Everyone | Projects, priorities, due dates, calendar views, context management |
| **productivity** | GTD practitioners | Daily & weekly reviews, dashboards, context tags (`+work`, `+home`, `+errands`) |
| **project-mgmt** | Project managers | Scope-based roadmaps (by project, priority, day, week), milestone tracking |

### Want GTD? Use the Productivity Profile

It's designed for Getting Things Done out of the box:

- **Capture** → `add_task` with `project: Inbox` for instant capture
- **Organize** → Assign project, priority, due date, context tags
- **Review** → Built-in `daily_review` and `weekly_review` prompts with structured output
- **Execute** → `next_task` surfaces your highest-urgency item

~~~
📅 Daily Review
🔴 OVERDUE: 2 tasks — reschedule or delete
📋 TODAY: 5 tasks — confirm capacity
📥 INBOX: 3 items — triage now
💡 NEXT: "Finalize Q4 budget proposal" (H, due:today)
~~~

### Want Something Else? Build Your Own Profile

Profiles are composable. Extend any existing profile and override only what you need:

~~~
# my-custom-profile/profile.yaml
name: my-flow
version: 1.0.0
extends: standard          # inherit everything from standard

# Add your own instructions
instructions:
  - my_flow/rules.md       # custom agent behavior
  - my_flow/reports.md     # custom review format

# Add your own resources
resources:
  - uri: taskmajor://my/sprint
    function: query_tasks
    params:
      filter: "status:pending +sprint"
      sort: ["priority", "due"]
    name: Sprint Board
~~~

Drop your profile into the config directory and TaskMajor picks it up. No fork, no patch—just a YAML file and a few instruction fragments.

### Multi-Agent Project Management

Running several AI agents on the same codebase? TaskMajor supports that natively:

- **Shared TaskWarrior database** — All agents read and write the same tasks
- **Per-agent profiles** — Give each agent a tailored scope (e.g., one handles triage, another handles execution)
- **Project-scoped roadmaps** — `taskmajor://roadmap/project` groups tasks by project hierarchy
- **Context-aware filtering** — Tag tasks with `+agent:copilot` or `+agent:claude` to track ownership

~~~
# Agent A: Triage bot (productivity profile)
"Process inbox and assign projects"

# Agent B: Execution bot (standard profile, scoped to +sprint)
"Start the next high-priority sprint task"

# Agent C: Review bot (productivity profile, read-only)
"Generate the weekly status report"
~~~

---

## ✨ Key Features

✅ **Complete Task Lifecycle** — Create, update, complete, and archive tasks
✅ **Triage Workflow** — Capture to Inbox and triage with `update_task`
✅ **Rich Metadata** — Auto-discovery of projects, tags, priorities, and contexts
✅ **Multiple Views** — Pre-built resources for today, this week, overdue, and statistics
✅ **Profile System** — Ship-ready workflows or roll your own; composable and extensible
✅ **Multi-Agent Ready** — Coordinate several agents on the same task database
✅ **OpenTelemetry Ready** — Optional tracing, metrics, and structured logging
✅ **Type-Safe** — Full Pydantic models for all DTOs
✅ **MCP Standard** — Compatible with any MCP client

---

## 🚀 Quick Start: Choose Your Path

### 👤 I Use Copilot, Claude, or Cursor

**Skip the DevOps stuff.** Get up and running in 5 minutes:

👉 **[Quick Connect Guide](docs/user-guides/integrations/simple-agent-setup.md)**

- Copy-paste config snippets for VS Code, CLI, or Cursor
- Test with one command
- Start managing tasks immediately

### 🚀 I'm Deploying a Server

**Deploy TaskMajor for your team or infrastructure:**

👉 **[Getting Started (DevOps)](docs/getting-started/index.md)**

- Docker setup and docker-compose
- Configuration with environment variables
- Build from source or containerize
- Observability with OpenTelemetry

### 🔧 I'm Building a Custom Agent

**Understand the API and architecture:**

👉 **[API Reference](docs/api-reference/index.md)** | **[Architecture](docs/developer/architecture.md)**

- Resource contracts and tool signatures
- Metadata contract (projects, tags, contexts)
- Workflow examples and advanced use cases

---

## ⚙️ Configuration Layers

TaskMajor separates concerns into three layers—each one optional, each one overridable:

### 1. Environment Variables (deployment)

~~~
TASKMAJOR_SERVER_HOST=localhost
TASKMAJOR_SERVER_PORT=8888
TASKMAJOR_LOG_LEVEL=INFO
TASKMAJOR_TASKRC=/data/task/.taskrc
TASKMAJOR_TASKDATA=/data/task
~~~

### 2. YAML Config (runtime settings)

~~~yaml
# taskmajor/config/config.yaml
server_host: localhost
server_port: 7777
server_name: TaskMajor Server
config_mode: false

taskrc: /data/task/.taskrc
taskdata: /data/task

log_level: INFO
log_format: text          # or: json
agent_errors_path: /data/task/agent_errors.jsonl
~~~

### 3. Profile System (workflow behavior)

Choose a built-in profile or create your own. Profiles control:
- Which **tools** the agent can use
- Which **resources** (views) are available
- Which **prompts** shape agent behavior
- How **dates, text, and organization** are handled

👉 **[Profile System Documentation](docs/user-guides/profiles/profile-system.md)**

Mount a custom profile into Docker without overwriting built-in ones:

👉 **[Docker: Custom Profiles](docs/deployment/docker-custom-profile.md)**

---

## 📦 Installation

### Option 1: Quick Install (with uv)

~~~bash
git clone https://github.com/nschmeltz/taskmajor.git
cd taskmajor
uv sync
~~~

### Option 2: With pip

~~~bash
git clone https://github.com/nschmeltz/taskmajor.git
cd taskmajor
pip install -e .
~~~

### Option 3: Docker

~~~bash
docker compose -f docker/docker-compose.yaml up -d
~~~

### Requirements

- **TaskWarrior** installed and on PATH — [Install](https://taskwarrior.org/download/build/)
- **Python 3.10+** — [Download](https://www.python.org/downloads/)
- **uv** (optional but recommended) — [Install](https://astral.sh/uv/install.sh)

---

## 💡 Usage Examples

### GitHub Copilot (VS Code)

~~~json
// Add to VS Code settings.json
{
  "github.copilot.chat.mcp": {
    "taskMajor": {
      "command": "uv",
      "args": ["run", "-m", "taskmajor.bootstrap.server"],
      "type": "stdio"
    }
  }
}
~~~

Then in Copilot Chat:
~~~
Show me my tasks for today
~~~

### Claude Code (CLI)

~~~json
// ~/.claude/mcp_servers.json
{
  "taskMajor": {
    "command": "uv",
    "args": ["run", "-m", "taskmajor.bootstrap.server"],
    "type": "stdio"
  }
}
~~~

### Run the MCP Server

~~~bash
cd taskmajor
uv run -m taskmajor.bootstrap.server
~~~

**Expected output:**
~~~
INFO:    Starting MCP server on stdio
INFO:    TaskMajor MCP Server ready
~~~

---

## 🔌 API Overview

### Resources (Read-Only)

Query data from TaskWarrior:

| Resource | Purpose |
|----------|---------|
| `taskmajor://agenda/today` | Tasks due today |
| `taskmajor://agenda/week` | Tasks this week |
| `taskmajor://status/overdue` | Overdue tasks |
| `taskmajor://queue/unsorted` | Inbox tasks (pending, project:Inbox) |
| `taskmajor://roadmap/project` | Tasks grouped by project |
| `taskmajor://roadmap/priority` | Tasks grouped by priority |
| `taskmajor://roadmap/day` | Tasks grouped by day |
| `taskmajor://roadmap/week` | Tasks grouped by week |
| `taskmajor://analytics/summary` | Aggregate counts and metrics |
| `taskmajor://config/schema` | API capabilities and self-description |

### Tools (Write/Execute)

Execute task operations:

| Tool | Purpose |
|------|---------|
| `query_tasks(filters, sort, limit, offset)` | Search tasks |
| `add_task(task_input)` | Create a new task (use `project: Inbox` for quick capture) |
| `update_task(task_id, task_input)` | Modify an existing task or triage (≥1 field required) |
| `done_task(task_id)` | Mark task complete |
| `delete_task(task_id)` | Delete task |
| `start_task(task_id)` | Start working on a task |
| `stop_task(task_id)` | Pause work on a task |
| `next_task()` | Surface the highest-urgency pending task |
| `resolve_date(expression)` | Convert a date expression to ISO 8601 |
| `validate_date(expression)` | Validate a user-supplied date expression |

See [API Reference](docs/api-reference/index.md) for complete documentation.

---

## 📚 Documentation

| Section | For |
|---------|-----|
| **[Quick Connect](docs/user-guides/integrations/simple-agent-setup.md)** | Simple Agent Users (Copilot, Claude, Cursor) |
| **[Getting Started](docs/getting-started/index.md)** | DevOps / Deployment |
| **[API Reference](docs/api-reference/index.md)** | Developers / Integrators |
| **[Architecture](docs/developer/architecture.md)** | System design and concepts |
| **[Configuration](docs/getting-started/configuration.md)** | Environment variables and setup |
| **[Profiles](docs/user-guides/profiles/profile-system.md)** | Workflow methodologies & custom profiles |
| **[Docker: Custom Profiles](docs/deployment/docker-custom-profile.md)** | Mount profiles without overwriting built-ins |
| **[Troubleshooting](https://github.com/nschmeltz/taskmajor/issues)** | Common issues and solutions |
| **[Contributing](docs/development/contribution-path.md)** | Add a new agent integration |

**Full documentation:** [https://taskmajor.readthedocs.io/](https://taskmajor.readthedocs.io/)

---

## 🛠 Development

### Run Tests

~~~bash
uv run pytest -v
~~~

### Generate Documentation

~~~bash
# Build MkDocs site locally
mkdocs serve
# Opens http://localhost:8000
~~~

### Project Structure

~~~
taskmajor/
├── core.py              # MCP server factory
├── server.py            # MCP server entry point
├── task_service.py      # Business logic
├── taskrc_service.py    # TaskWarrior config wrapper
├── storage.py           # Task cache
├── config.py            # Configuration
├── mcp/
│   ├── resources/       # Read-only views
│   ├── tools/           # Callable operations
│   └── prompts/         # Agent system prompts
└── tests/               # Test suite
~~~

---

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Add tests for new functionality
4. Ensure all tests pass: `uv run pytest`
5. Submit a pull request

**Want to add support for your AI agent?** See [Contributing Guide](docs/development/contribution-path.md)

---

## 🧪 Testing

TaskMajor has comprehensive test coverage (**61% line coverage, 148 tests, 100% passing**) across multiple test layers:

### Quick Test Commands

~~~bash
# Run all tests (recommended first step)
pytest

# Run using the validation script (with formatting/lint checks)
./scripts/run_tests.sh

# Run specific test category
pytest tests/domains/tasks/           # Unit tests
pytest tests/mcp/                     # MCP contract tests
pytest tests/domains/taskwarrior/     # Config and initialization

# Run with coverage report
pytest --cov=taskmajor --cov-report=html
open htmlcov/index.html               # View report in browser

# Run only fast tests (skip slow edge cases)
pytest -m "not slow"

# Run property-based tests with output
pytest tests/domains/tasks/test_property_based.py -v
~~~

### CI/CD & Quality Gates

Tests run automatically on every push and PR via GitHub Actions:
- ✅ All 148+ tests must pass (Python 3.10, 3.11, 3.12)
- ✅ Minimum 60% code coverage required
- ✅ No linting errors (ruff, mypy)
- ✅ Branch protection requires review + passing checks

---

## 🌐 Community

- **Issues & Features:** [GitHub Issues](https://github.com/nschmeltz/taskmajor/issues)
- **Discussions:** [GitHub Discussions](https://github.com/nschmeltz/taskmajor/discussions)
- **Documentation:** [Full Docs](https://taskmajor.readthedocs.io/)

---

## 📄 License

MIT License — See [LICENSE](https://github.com/nschmeltz/taskmajor/blob/main/LICENSE) for details.

---

## 🏗 Acknowledgments

Built with:

- **[FastMCP](https://github.com/joshstevens19/fastmcp)** — Modern MCP framework
- **[pytaskwarrior](https://github.com/sznicolas/pytaskwarrior)** — Python TaskWarrior wrapper
- **[Pydantic](https://docs.pydantic.dev/)** — Data validation
- **[OpenTelemetry](https://opentelemetry.io/)** — Observability

---

## 📊 Status

✅ Actively maintained | 📚 Well documented | 🧪 Tested | 🚀 Ready for production

---

<div align="center">

**Questions?** Check the [Troubleshooting Guide](https://github.com/nschmeltz/taskmajor/issues)
**Found a bug?** [Report it](https://github.com/nschmeltz/taskmajor/issues)
**Want to help?** [Contribute!](docs/development/contribution-path.md)

</div>
