# Architecture

TaskMajor is a MCP server bridging AI agents to TaskWarrior. It exposes tools and read-only resources, filtered by an active profile that defines the agent's allowed capabilities and behavioral instructions.

## Modules

- **`bootstrap/`** — server factory (`create_mcp()`), entry point. Orchestrates initialization order: telemetry → FastMCP → TaskWarrior → **proxy** → **SyncEngine** (optional) → profiles → TaskService → resources → tools → start.
- **`domains/`** — business logic: `tasks/` (TaskService, filters, storage), `profiles/` (loading, composition), `taskwarrior/` (config wrapper), `observability/`, `agent/`, `sync/` (SyncEngine, SyncHealth).
- **`mcp/`** — MCP layer: `tools/` (callable operations), `resources/` (read-only views), `prompts/`, `templates/`.
- **`profiles/`** — built-in profile definitions (base, minimal, standard, productivity, project-mgmt).
- **`utils/`** — cross-cutting utilities: `taskwarrior_proxy` (thread-safe proxy that confines the `TaskWarrior` instance and its PyO3 `Replica` to a single worker thread, routing all calls through a `queue.Queue`).

## Two-Phase Initialization

**Phase 1** (no TaskService required): resolve profile chain, validate, load instructions and prompts.  
**Phase 2** (requires TaskService): register resources via ResourceMapper, register tools against profile whitelist.

This separation makes profile loading independently testable.

## Key Classes

- `ProfileManager` — resolves inheritance chain, accumulates instructions/prompts/resources
- `TaskService` — all task business logic; used by tools and resource backends
- `ResourceMapper` — maps resource URIs declared in manifests to TaskService methods
- `SyncEngine` — periodic or manual TaskWarrior sync. Reads `SyncConfig` from `TaskMajorConfig.sync`. Only created when a sync backend is configured (local or remote). Calls `synchronize()` through the `TaskWarriorProxy` (thread-safe). Exposes `force_sync` and `sync_status` MCP tools.

## SyncEngine

`SyncEngine` (`domains/sync/sync_engine.py`) is independent of `TaskWarriorProxy` — it holds a reference to the proxy and routes all calls through the normal queue.

**Modes:**
- `periodic` — `threading.Timer` fires every `interval_seconds` (first sync after one full interval, not at startup).
- `manual` — no automatic timer; callers use `force_sync` tool explicitly.

**Lifecycle in `create_mcp()`:**
1. Extract `cfg.sync` (a `SyncConfig` Pydantic model, top-level in `config.yaml`)
2. If a sync backend is configured, create `SyncEngine(tw_proxy, cfg.sync)`
3. Call `engine.start()`
4. Register `atexit.register(engine.stop)` — triggers `on_exit` sync if configured
5. Pass engine to `register_tools()` → `register_sync_tools()` adds `force_sync` / `sync_status`

## See Also

- `→ doc_agents/PROFILES.md` — profile system detail
- `→ doc_agents/MCP_INTERFACE.md` — tools and resources catalog
- `→ doc_agents/DEPENDENCIES.md` — pytaskwarrior boundary
