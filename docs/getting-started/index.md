# Getting Started

## Prerequisites

TaskMajor requires the TaskWarrior `task` command to be installed and available on the PATH. If the `task` binary is not present, TaskMajor will fail to start.

See the [TaskWarrior installation guide](https://taskwarrior.org/download/build/) for platforms and packaging options.

## Installation

### With uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/taskmajor.git
cd taskmajor

# Install with uv
uv sync
```

### With pip

```bash
# Clone the repository
git clone https://github.com/yourusername/taskmajor.git
cd taskmajor

# Install in development mode
pip install -e .
```

## Configuration

TaskMajor uses environment variables for configuration. Create a `.env` file in the repo root:

```bash
# .env (do not commit secrets)
TASKMAJOR_SERVER_HOST=localhost
TASKMAJOR_SERVER_PORT=8888
TASKMAJOR_LOG_LEVEL=INFO
TASKMAJOR_LOG_FORMAT=json
```

See [Configuration](configuration.md) for complete environment variable documentation.

## Running the Server

### Standard MCP Server

```bash
python -m taskmajor.bootstrap.server
```

The server will start on `localhost:8888` by default.

### Development with FastMCP Inspector

```bash
uv run fastmcp dev inspector taskmajor/bootstrap/core.py:main
```

This opens an interactive inspector for exploring resources and tools during development.

## Running Tests

```bash
uv run pytest -v
```

All tests should pass. If you encounter failures, check:

1. TaskWarrior is installed: `task --version`
2. Your `.env` file has correct paths
3. TaskWarrior data directory exists

## Next Steps

- [Quick Start](getting-started.md) — Try your first task operations
- [Configuration](configuration.md) — Customize environment settings
- [API Reference](../api-reference/index.md) — Explore all resources and tools
