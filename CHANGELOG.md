# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **`TaskWarriorProxy`** (`taskmajor/utils/taskwarrior_proxy.py`): thread-safe proxy that confines the `TaskWarrior` instance (and its PyO3 `Replica`) to a dedicated worker thread. All calls from FastMCP's `ThreadPoolExecutor` are routed through a `queue.Queue` + `concurrent.futures.Future`, eliminating the thread-affinity violation that caused crashes with `TaskChampionAdapter`.
  - `ProxyMetrics` — per-proxy counters for calls, errors, and wait/run timings.
  - `_ConfigStoreProxy` — explicit proxy for `config_store` operations (`config`, `set_value`, `delete_value`, `get_contexts`, `get_sync_config`), all routed through the worker thread.
  - Worker-death safety: pending futures are drained with `RuntimeError` if the worker exits unexpectedly.
  - Re-entrancy guard: calls from within the worker thread bypass the queue to avoid deadlocks.
  - Idempotent `shutdown(timeout)` with bounded `join`.

- **`SyncEngine`** (`taskmajor/domains/sync/sync_engine.py`): automatic TaskWarrior synchronization engine, independent of `TaskWarriorProxy`.
  - Two modes: `periodic` (recurring `threading.Timer`) and `manual` (on-demand via `force_sync` tool).
  - `SyncHealth` — tracks `last_sync`, `consecutive_failures`, `last_error`.
  - `is_sync_configured()` guard: sync calls are silently skipped when TaskWarrior has no sync server configured, so enabling sync is safe even without a sync server; activation now depends on configured backends (local or remote).
  - On-exit sync: optional final sync on server shutdown (`on_exit: true`).
  - Periodic mode defers the first sync by one full interval (no burst at startup).

- **Sync MCP tools** (`taskmajor/mcp/tools/sync_tools.py`): registered only when a sync backend is configured (local or remote).
  - `force_sync` — trigger an immediate synchronization.
  - `sync_status` — return health snapshot: mode, last\_sync, consecutive\_failures, sync\_configured.

- **`SyncConfig`**, **`LocalSyncConfig`**, **`RemoteSyncConfig`** Pydantic sub-models (`taskmajor/domains/taskwarrior/config.py`):
  - `SyncConfig.mode` validated as `Literal["periodic", "manual"]`.
  - `interval_seconds > 0` enforced.
  - `RemoteSyncConfig`: when configured (i.e., present in the config), requires a non-empty `origin`.
  - `LocalSyncConfig.server_dir` supports `~` tilde expansion.
  - All sub-models use `extra="forbid"`.

- **`resolve_sync_config()`** (`taskmajor/bootstrap/core.py`): merges YAML-loaded `SyncConfig` with CLI overrides. `--sync-enabled`/`--no-sync` is applied last and always wins over backend auto-enable flags.

- **CLI sync flags** (all optional; CLI overrides config.yaml):
  - `--sync-enabled` / `--no-sync` — enable or disable sync for this run.
  - `--sync-mode {periodic,manual}` — override sync mode.
  - `--sync-interval SECONDS` — override periodic interval.
  - `--sync-local-dir PATH` — set local sync server directory; auto-enables local sync and top-level sync.
  - `--sync-remote-origin URL` — set remote sync server URL; auto-enables remote sync and top-level sync.
  - `--sync-remote-client-id UUID` — set remote client UUID.
  - Note: `--sync-remote-secret` is intentionally absent — pass secrets via `config.yaml` only.

### Changed
- `bootstrap/core.py`: `TaskWarrior` is now created inside the proxy worker thread (factory pattern). Removed `install_serializer` call; replaced with `atexit.register(proxy.shutdown)`. `create_mcp()` now conditionally initializes `SyncEngine` when a sync backend is configured; `start_mcp()` parses sync CLI flags and calls `resolve_sync_config()` before `create_mcp()`.

- `config.yaml`: sync defaults updated; `sync.mode` now defaults to `periodic`. The `is_sync_configured()` guard ensures that no-op behavior occurs when no backend is configured.

- **Sync Configuration Refactor**: Sync is now activated by the presence of `local` or `remote` backends in the `tw_conf.sync` block. The `enabled` boolean was removed in favor of backend presence. If a `sync:` block is present but no backends are configured, a default local backend is injected at `~/.task_mcp/sync_server` for robustness.

- **CLI Improvements**: Added `--sync-local-dir`, `--sync-remote-origin` and refined `--no-sync` behavior (now clears backends when used). `--sync-mode` and `--sync-interval` continue to override config values.

### Removed
- `taskmajor/utils/task_serializer.py` and its tests: the `TaskCommandSerializer` (threading lock on `run_task_command`) was a no-op for `TaskChampionAdapter` and is fully superseded by `TaskWarriorProxy`.

- `enabled` field removed from `sync` configuration and from `local`/`remote` sub-blocks; presence of backend now determines activation.

### Fixed
- Potential silent failure where a top-level `enabled` flag indicated sync but no backend was configured: now a default local backend is injected when appropriate, or `--no-sync` can explicitly disable sync.
### Removed
- `taskmajor/utils/task_serializer.py` and its tests: the `TaskCommandSerializer` (threading lock on `run_task_command`) was a no-op for `TaskChampionAdapter` and is fully superseded by `TaskWarriorProxy`.

