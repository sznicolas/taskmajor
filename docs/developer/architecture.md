# Architecture

TaskMajor is organized into a clean, modular Python package structure.

## Package Structure

```
taskmajor/
├── config/                      # Runtime YAML configuration
├── domains/
│   ├── agent/                   # Agent-facing helpers
│   ├── observability/           # Telemetry and error logging
│   ├── profiles/                # Profile loading system (v2)
│   │   ├── models.py            # ProfileManifest, UdaDefinition, etc.
│   │   ├── profile_manager.py   # Chain loading, extends composition
│   │   ├── resource_mapper.py   # Dynamic resource registration
│   │   ├── prompt_loader.py     # Prompt discovery and loading
│   │   └── instructions_loader.py  # Sequential instruction accumulation
│   ├── sync/                    # Synchronization engine
│   │   └── sync_engine.py       # SyncEngine + SyncHealth
│   ├── tasks/                   # Task business logic and storage
│   └── taskwarrior/             # TaskWarrior config and initialization
├── profiles/                    # Built-in profiles
│   ├── base/                    # Minimal CRUD foundation
│   ├── minimal/                 # Lightweight variant
│   ├── standard/                # Default workflows (extends base)
│   ├── productivity/            # GTD-inspired workflow (extends standard)
│   └── project-mgmt/            # Project tracking with UDAs (extends standard)
├── bootstrap/                   # MCP server composition and entry points
│   └── core.py                  # Profile loading → TaskService → MCP wiring
└── mcp/                         # MCP component registry
    ├── resources/               # Static resource definitions
    │   ├── context_resources.py # TaskWarrior context (static)
    │   ├── date_resources.py    # Date/time (static)
    │   ├── debug_resources.py   # Error history (static)
    │   └── history_resources.py # Undo stack (static)
    ├── tools/                   # Tool definitions
    │   ├── task_tools.py        # Task CRUD and queries
    │   ├── context_tools.py     # Context management
    │   ├── config_tools.py      # Configuration tools
    │   ├── diagnostic_tools.py  # Diagnostics
    │   └── sync_tools.py        # Sync tools (registered when a sync backend is configured)
    ├── prompts/                 # Agent system prompts (referenced by profiles)
    └── templates/               # Resource templates
        └── date_templates.py    # Date templating logic
```

## Core Modules

### `domains/taskwarrior/config.py`
**Configuration management** using YAML-loaded Pydantic models.

- Loads from `taskmajor/config/config.yaml`
- Validates configuration with `extra="forbid"` on all models
- `SyncConfig` — sync mode, interval, on\_exit flag; `LocalSyncConfig` and `RemoteSyncConfig` sub-models with validation (Literal mode, interval > 0, remote requires origin)

```python
from taskmajor.domains.taskwarrior import config
print(config.server_port)
print(config.sync.mode)  # "periodic" | "manual"
```

### `domains/sync/sync_engine.py`
**Automatic TaskWarrior synchronization**, independent of `TaskWarriorProxy`.

- Routes sync calls through `TaskWarriorProxy` (thread-safe).
- `periodic` mode: recurring `threading.Timer` every `interval_seconds`.
- `manual` mode: no timer; sync triggered via `force_sync` MCP tool.
- `is_sync_configured()` guard: silently skips sync when TaskWarrior has no server configured.
- `SyncHealth` tracks `last_sync`, `consecutive_failures`, `last_error`.

```python
engine = SyncEngine(tw_proxy, cfg.sync.model_dump())
engine.start()
engine.force_sync()
engine.health  # {"mode": ..., "last_sync": ..., ...}
engine.stop()  # performs final sync if on_exit=True
```

### `domains/profiles/profile_manager.py`
**Profile system orchestrator (v2)**.

- Builds extends chain (parent → child profiles)
- Detects conflicts and cycles
- Three-tier profile resolution (absolute, user, built-in)
- Two-phase loading:
  - Phase 1: Build chain and load prompts/instructions (no TaskService)
  - Phase 2: Load resources (requires TaskService for backend dispatch)

```python
from taskmajor.domains.profiles import ProfileManager
pm = ProfileManager(config, cli_profile="my-profile")
pm.set_task_service(task_service)
manifests = pm.load_all()  # [parent, child]
```

### `bootstrap/core.py`
**MCP server factory and profile orchestrator**.

- `resolve_sync_config(sync_cfg, args)` — merges YAML `SyncConfig` with CLI overrides; `--no-sync` always wins.
- `create_mcp()` — full initialization sequence (see below).
- `start_mcp()` — parses sync CLI flags, calls `resolve_sync_config`, then `create_mcp`.

```python
from taskmajor.bootstrap import create_mcp
mcp, task_service, error_log = create_mcp()
```

**Initialization Order (`create_mcp`):**
1. Configure telemetry
2. Create `FastMCP` instance
3. Initialize TaskWarrior (`init_taskwarrior`)
4. Create `TaskWarriorProxy` (spawns worker thread, `TaskWarrior` created inside worker)
5. **Create `SyncEngine`** if a sync backend is configured — starts timer, registers `atexit.register(engine.stop)`
6. Load profile chain (`ProfileManager`)
7. Create `TaskService`
8. Register tools (including sync tools if engine is active) and resources
9. Apply profile components (UDAs, contexts, prompts, resources)

### `domains/tasks/task_service.py`
**Business logic layer**.

- Interfaces with TaskWarrior via `pytaskwarrior`
- Handles task queries, filtering, sorting
- Implements review queue and metadata

### `domains/taskwarrior/task_config.py`
**TaskWarrior configuration wrapper**.

- Reads `.taskrc` configuration
- Manages contexts
- Provides config metadata

### `domains/tasks/storage.py`
**In-memory task cache**.

- Local task storage for quick access
- Refresh mechanism from TaskWarrior
- Supports add/update/delete operations

### `domains/observability/instrumentation.py`
**OpenTelemetry tracing**.

- Traces MCP resources and tools
- Records timing and success/failure
- Decorators for automatic instrumentation

### `domains/agent/`
**Agent-facing helpers**.

- Resource tools for agent use
- Integrates with Pydantic-AI for structured agent interactions

## MCP Component Registry (`mcp/__init__.py`)

Registers all resources, tools, prompts, and templates:

```python
def register_all(mcp, task_service, error_log, tool_whitelist=None, sync_engine=None):
    register_tools(mcp, task_service, error_log,
                   tool_whitelist=tool_whitelist,
                   sync_engine=sync_engine)  # sync_engine=None → no sync tools
    register_resources(mcp, task_service, error_log)
    register_templates(mcp, task_service)
```

Sync tools (`force_sync`, `sync_status`) are registered only when `sync_engine` is not `None` (i.e., when a sync backend is configured).

## Resources

**Read-only data views** exposing task information via the `taskmajor://` URI scheme.

Resources come from two sources:

### Static resources (always registered — `mcp/resources/`)

| Module | URI | Description |
|--------|-----|-------------|
| `context_resources.py` | `taskmajor://context/current` | Active TaskWarrior context |
| `date_resources.py` | `taskmajor://now` | Current date/time and timezone |
| `debug_resources.py` | `taskmajor://debug/errors` | Agent error history |
| `history_resources.py` | `taskmajor://history/undo` | Undo stack |

### Profile-declared resources (registered dynamically from `profiles/*/manifest.yaml`)

Profiles declare additional resources under `resources:` in their `manifest.yaml`. The `standard` profile, for example, registers:

| URI | Description |
|-----|-------------|
| `taskmajor://agenda/today` | Tasks due today |
| `taskmajor://agenda/week` | Tasks due next 7 days |
| `taskmajor://status/overdue` | Overdue tasks |
| `taskmajor://queue/unsorted` | Inbox review queue |
| `taskmajor://analytics/summary` | Task aggregates |
| `taskmajor://config/schema` | API metadata |
| `taskmajor://roadmap/project` | Tasks grouped by project |
| `taskmajor://roadmap/priority` | Tasks grouped by priority |

Each resource specifies a `backend.function` (e.g. `query_tasks`, `get_stats`) and optional parameters. See [Profile Composition](profile-composition.md) for the full resource declaration format.

## Tools

**Callable operations** for task manipulation:

### Business Queries
- `query_tasks(filters, sort, limit, offset)`
- `get_stats(filters)`
- `next_task(filters)`

### Task Management
- `add_task(task_input)`
- `update_task(task_id, task_input)` — Can be used for triage and advanced modifications
- `done_task(task_id)`
- `delete_task(task_id)`

### Workflow
- `start_task(task_id)`
- `stop_task(task_id)`

### Context Management
- `list_contexts()`
- `set_context(name)`
- `unset_context()`

### Sync *(registered only when a sync backend is configured)*
- `force_sync()` — trigger immediate TaskWarrior synchronization
- `sync_status()` — return health snapshot (mode, last\_sync, consecutive\_failures, sync\_configured)

## Data Flow

```
External Client
    ↓
FastMCP Server (taskmajor.bootstrap.server)
    ↓
MCP Component Registry (taskmajor.mcp)
    ├── Resources (query only)
    ├── Tools (query + mutate)
    └── Prompts (agent instructions)
    ↓
Task Service (taskmajor.domains.tasks.task_service)
    ↓
TaskWarriorProxy (utils/taskwarrior_proxy.py)   ←── SyncEngine (periodic timer)
    ↓
TaskWarrior (pytaskwarrior)
    ↓
TaskWarrior Database (.task/)
```

## Dependencies

- **FastMCP** — MCP framework
- **pytaskwarrior** — TaskWarrior Python wrapper
- **Pydantic** — Data validation
- **OpenTelemetry** — Observability (optional)

## Error Handling

Errors are captured in `domains/observability/agent_error_log.py`:

- Tool failures logged with context
- Errors accessible via `taskmajor://debug/errors` resource
- Traces available via OpenTelemetry when enabled


## Core Modules

### `domains/taskwarrior/config.py`
**Configuration management** using YAML-loaded Pydantic models.

- Loads from `taskmajor/config/config.yaml`
- Validates configuration
- Provides defaults

```python
from taskmajor.domains.taskwarrior import config
print(config.server_port)
```

### `domains/profiles/profile_manager.py`
**Profile system orchestrator (v2)**.

- Builds extends chain (parent → child profiles)
- Detects conflicts and cycles
- Three-tier profile resolution (absolute, user, built-in)
- Two-phase loading:
  - Phase 1: Build chain and load prompts/instructions (no TaskService)
  - Phase 2: Load resources (requires TaskService for backend dispatch)

```python
from taskmajor.domains.profiles import ProfileManager
pm = ProfileManager(config, cli_profile="my-profile")
pm.set_task_service(task_service)
manifests = pm.load_all()  # [parent, child]
```

### `bootstrap/core.py`
**MCP server factory and profile orchestrator**.

- Loads profile chain BEFORE creating TaskService
- Extracts review config from profile for TaskService initialization
- Registers static resources (4 always-on resources)
- Applies profile components dynamically (UDAs, contexts, prompts, resources)
- Entry point for the application

```python
from taskmajor.bootstrap import create_mcp
mcp, task_service, error_log = create_mcp()
```

**Initialization Order:**
1. Load config
2. Init telemetry
3. Create `TaskWarriorProxy` (spawns worker thread, `TaskWarrior` created inside worker)
4. **Load profile chain** ← early, to get review_config
5. Create TaskService (with review_config from profile)
6. Register static resources
7. Apply profile components dynamically

### `domains/tasks/task_service.py`
**Business logic layer**.

- Interfaces with TaskWarrior via `pytaskwarrior`
- Handles task queries, filtering, sorting
- Implements review queue and metadata

### `domains/taskwarrior/task_config.py`
**TaskWarrior configuration wrapper**.

- Reads `.taskrc` configuration
- Manages contexts
- Provides config metadata

### `domains/tasks/storage.py`
**In-memory task cache**.

- Local task storage for quick access
- Refresh mechanism from TaskWarrior
- Supports add/update/delete operations

### `domains/observability/instrumentation.py`
**OpenTelemetry tracing**.

- Traces MCP resources and tools
- Records timing and success/failure
- Decorators for automatic instrumentation

### `domains/agent/`
**Agent-facing helpers**.

- Resource tools for agent use
- Integrates with Pydantic-AI for structured agent interactions

## MCP Component Registry (`mcp/__init__.py`)

Registers all resources, tools, prompts, and templates:

```python
def register_all(mcp: FastMCP, task_service: TaskService, error_log: AgentErrorLog):
    # Register resources
    register_resources(mcp, task_service, error_log)
    
    # Register tools
    register_tools(mcp, task_service, error_log)
    
    # Register prompts (optional)
    register_prompts(mcp, task_service)
```

## Resources

**Read-only data views** exposing task information via the `taskmajor://` URI scheme.

Resources come from two sources:

### Static resources (always registered — `mcp/resources/`)

| Module | URI | Description |
|--------|-----|-------------|
| `context_resources.py` | `taskmajor://context/current` | Active TaskWarrior context |
| `date_resources.py` | `taskmajor://now` | Current date/time and timezone |
| `debug_resources.py` | `taskmajor://debug/errors` | Agent error history |
| `history_resources.py` | `taskmajor://history/undo` | Undo stack |

### Profile-declared resources (registered dynamically from `profiles/*/manifest.yaml`)

Profiles declare additional resources under `resources:` in their `manifest.yaml`. The `standard` profile, for example, registers:

| URI | Description |
|-----|-------------|
| `taskmajor://agenda/today` | Tasks due today |
| `taskmajor://agenda/week` | Tasks due next 7 days |
| `taskmajor://status/overdue` | Overdue tasks |
| `taskmajor://queue/unsorted` | Inbox review queue |
| `taskmajor://analytics/summary` | Task aggregates |
| `taskmajor://config/schema` | API metadata |
| `taskmajor://roadmap/project` | Tasks grouped by project |
| `taskmajor://roadmap/priority` | Tasks grouped by priority |

Each resource specifies a `backend.function` (e.g. `query_tasks`, `get_stats`) and optional parameters. See [Profile Composition](profile-composition.md) for the full resource declaration format.

## Tools

**Callable operations** for task manipulation:

### Business Queries
- `query_tasks(filters, sort, limit, offset)`
- `get_stats(filters)`
- `next_task(filters)`

### Task Management
- `add_task(task_input)`
- `update_task(task_id, task_input)` — Can be used for triage and advanced modifications
- `done_task(task_id)`
- `delete_task(task_id)`

### Workflow
- `start_task(task_id)`
- `stop_task(task_id)`

### Context Management
- `list_contexts()`
- `set_context(name)`
- `unset_context()`

## Data Flow

```
External Client
    ↓
FastMCP Server (taskmajor.bootstrap.server)
    ↓
MCP Component Registry (taskmajor.mcp)
    ├── Resources (query only)
    ├── Tools (query + mutate)
    └── Prompts (agent instructions)
    ↓
Task Service (taskmajor.domains.tasks.task_service)
    ↓
TaskWarrior (pytaskwarrior)
    ↓
TaskWarrior Database (.task/)
```

## Dependencies

- **FastMCP** — MCP framework
- **pytaskwarrior** — TaskWarrior Python wrapper
- **Pydantic** — Data validation
- **OpenTelemetry** — Observability (optional)

## Error Handling

Errors are captured in `domains/observability/agent_error_log.py`:

- Tool failures logged with context
- Errors accessible via `taskmajor://debug/errors` resource
- Traces available via OpenTelemetry when enabled
