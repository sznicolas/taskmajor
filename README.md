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

Behind this sits [**TaskWarrior**](https://taskwarrior.org)—a remarkably flexible, battle-tested task engine. It runs locally, stores plain text, and bends to almost any organizational style. TaskMajor builds on that foundation and adds its own layer of adaptability: the **profile system**. Each profile defines a unique contract of exposed tools, views, and behaviors—turning TaskMajor into anything from a simple to-do list to a full GTD system or a multi-agent coordination hub. Explore the [built-in profiles](docs/user-guides/profiles/reference/README.md) or learn how to compose and extend them in the [profile documentation](docs/user-guides/profiles/profile-system.md).

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
2. **(Optional) Configure**
   > **Important for TaskWarrior users:** If you already have a TaskWarrior database, you **must** edit `taskmajor/config/config.yaml` if you want to share your existing data directory.
   >
   > ```yaml
   > # taskmajor/config/config.yaml
   > taskrc: /path/to/your/.taskrc # default: ~/.taskrc_mcp
   > taskdata: /path/to/your/.task # default: ~/.task_mcp/
   > ```

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
docker build -t taskmajor . && mkdir taskdata && docker run -d -v $PWD/taskdata:/home/taskmajor/.task_mcp -p 8888:8888 taskmajor
```
*Remember to mount your `config.yaml` and TaskWarrior data directory if you want to persist data.*

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


## 🌐 Community

- **Issues & Features:** [GitHub Issues](https://github.com/nschmeltz/taskmajor/issues)
- **Discussions:** [GitHub Discussions](https://github.com/nschmeltz/taskmajor/discussions)

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
