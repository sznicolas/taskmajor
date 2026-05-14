# Agent configuration — Server & transport

This document explains how to configure the TaskMajor server transport (MCP transport) and the related CLI flags and configuration file values that affect how agents connect.

## Where configuration lives
- Project config file: `taskmajor/config/config.yaml` (preferred for persistent defaults)
- Runtime overrides: CLI flags passed to the server entrypoint (highest precedence)
- Program defaults: `TaskMajorConfig` model defaults in `taskmajor/domains/taskwarrior/config.py`

## Key settings
- `server_transport` (config.yaml): transport backend used by FastMCP. Default: `streamable-http`.
- CLI flag `--transport <name>`: overrides `server_transport` at process start.
- `--server-port` and `--server-host`: used for network transports only (HTTP/SSE/streamable-http).

Example config snippet (taskmajor/config/config.yaml):

```yaml
# taskmajor/config/config.yaml
server_host: 0.0.0.0
server_port: 8888
server_transport: streamable-http  # options: stdio, streamable-http, sse, http
```

## CLI precedence and examples
Priority order: CLI flags > config.yaml value > TaskMajorConfig defaults.

- Start server with default transport from config:

```bash
uv run -m taskmajor.bootstrap.server
```

- Start server with explicit streamable HTTP transport on port 8888:

```bash
uv run -m taskmajor.bootstrap.server --transport streamable-http --server-port 8888
```

- Start server using stdio transport (for tightly-coupled local agent processes):

```bash
uv run -m taskmajor.bootstrap.server --transport stdio
```

Important: the `stdio` transport is not a network transport — it connects the MCP to the agent over stdin/stdout. When using `stdio`, `--server-port` and `--server-host` are ignored. Internally TaskMajor calls FastMCP.run_async without `port`/`host` for `stdio`.

## Transport behaviors (short)
- stdio: local, process-bound; no host/port; suitable for agents launched as subprocesses that speak MCP over stdin/stdout.
- streamable-http / http / sse: network transports; accept `--server-port` and `--server-host`.

## Agent integration notes
- Make sure the agent supports the chosen transport. Many editor integrations use `streamable-http` or `http`.
- For `stdio`, start the agent as a subprocess and configure it to use stdin/stdout as MCP transport.

## Troubleshooting
- If `uv run -m taskmajor.bootstrap.server --transport stdio` raises an error about unexpected `port` kwarg, ensure your server version includes the stdio-transport fix that omits `port`/`host` when calling FastMCP.run_async.
- Use `--log-level DEBUG` to get detailed startup logs including `Using MCP transport: <transport>`.

---

## Sync CLI flags

All sync flags are optional. CLI overrides config.yaml, which overrides Pydantic model defaults.

| Flag | Type | Description |
|---|---|---|
| `--sync-enabled` | flag | Enable sync (overrides config.yaml) |
| `--no-sync` | flag | Disable sync (overrides config.yaml and backend auto-enable; always wins) |
| `--sync-mode {periodic,manual}` | string | `periodic` = timer; `manual` = force_sync tool only |
| `--sync-interval SECONDS` | int | Periodic interval in seconds (default: 300) |
| `--sync-local-dir PATH` | path | Local sync server directory. Auto-enables local sync and top-level sync. |
| `--sync-remote-origin URL` | string | Remote sync server URL. Auto-enables remote sync and top-level sync. |
| `--sync-remote-client-id UUID` | string | Client UUID for remote sync server. |

> **Security note:** `--sync-remote-secret` is intentionally not available as a CLI flag.
> Passing secrets via argv exposes them in process listings (`ps aux`) and shell history.
> Set `encryption_secret` in `config.yaml` instead.

### Resolution order
1. Backend flags (`--sync-local-dir`, `--sync-remote-origin`) can auto-enable sync.
2. `--sync-enabled` / `--no-sync` is applied last and **always wins**.

### Examples

```bash
# Disable sync for this run (even if config.yaml has enabled: true)
uv run -m taskmajor.bootstrap.server --no-sync

# Override to manual mode for this run
uv run -m taskmajor.bootstrap.server --sync-mode manual

# Use a specific local sync server dir and start periodic sync
uv run -m taskmajor.bootstrap.server --sync-local-dir ~/.my_sync_server

# Fully configure remote sync via CLI (secret must be in config.yaml)
uv run -m taskmajor.bootstrap.server \
  --sync-remote-origin https://sync.example.com \
  --sync-remote-client-id your-uuid
```

### config.yaml sync section reference

```yaml
sync:
  enabled: true           # bool — enable/disable sync engine
  mode: "periodic"        # periodic | manual
  interval_seconds: 300   # seconds between syncs (periodic mode only)
  on_exit: true           # sync on server shutdown

  # local:                # uncomment to use a local sync server
  #   enabled: true
  #   server_dir: "~/.task_sync_server"

  # remote:               # uncomment to use a remote sync server
  #   enabled: true
  #   origin: "https://sync.example.com"
  #   client_id: "your-uuid"
  #   encryption_secret: "your-secret"   # store here, not on CLI
```

## See also
- MCP interface reference: `doc_agents/MCP_INTERFACE.md`
- Profiles and resources: `doc_agents/PROFILES.md`
