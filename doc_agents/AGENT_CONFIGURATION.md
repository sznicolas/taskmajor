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

## Synchronization Configuration

Synchronization is controlled by the `tw_conf.sync` block in `config.yaml`.
It is **enabled by default** if a `local` or `remote` backend is present.
If neither is present, a default local backend is injected automatically for robustness.

### Configuration Example

```yaml
tw_conf:
  taskrc: "~/.taskrc_mcp"
  taskdata: "~/.task_mcp"
  
  sync:
    mode: "periodic"          # periodic | manual
    interval_seconds: 300     # ignored if mode: manual
    on_exit: true             # force sync on shutdown
    
    # Local backend (default, robustness)
    local:
      server_dir: "~/.task_mcp/sync_server"
    
    # Remote backend (optional)
    # remote:
    #   origin: "https://sync.example.com"
    #   client_id: "your-uuid"
    #   encryption_secret: "your-secret"
```

### CLI Overrides

- `--sync-mode {periodic,manual}`: Override sync mode.
- `--sync-interval SECONDS`: Override interval.
- `--sync-local-dir PATH`: Force local backend with custom path.
- `--sync-remote-origin URL`: Force remote backend.
- `--no-sync`: Disable sync entirely (clears local and remote).

### Behavior

- **Default**: If `sync:` exists but no `local` or `remote` is defined, a local backend is auto-injected at `~/.task_mcp/sync_server`.
- **Disabled**: If `--no-sync` is passed or if `sync:` is completely absent, no sync occurs.
- **Guard**: If sync is configured but invalid (e.g., remote without origin), it logs a warning and skips sync.

## See also
- MCP interface reference: `doc_agents/MCP_INTERFACE.md`
- Profiles and resources: `doc_agents/PROFILES.md`
