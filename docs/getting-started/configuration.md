# Configuration

TaskMajor loads runtime configuration from `taskmajor/config/config.yaml`. Most customization is done via [profiles](../user-guides/profiles/profile-system.md) rather than configuration files.

## Layout

```text
taskmajor/config/
├── config.yaml
```

## `config.yaml`

Example:

```yaml
# Server
server_host: localhost
server_port: 8888
server_name: TaskMajor Server

# TaskWarrior
taskrc: ~/.taskrc_mcp
taskdata: ~/.task_mcp

# Profile
profile: productivity               # Profile name or path

# Logging
log_level: INFO
log_format: text
agent_errors_path: /data/task/agent_errors.jsonl

# Observability (OpenTelemetry)
otel_enabled: true
otel_service_name: TaskMajor

# Synchronization
# The is_sync_configured() guard skips sync silently when no server is set up,
# so enabled: true is safe even before configuring a sync server.
sync:
  enabled: true
  mode: "periodic"        # periodic | manual
  interval_seconds: 300   # 5 minutes (ignored in manual mode)
  on_exit: true           # sync on server shutdown

  # Local sync server — uncomment to activate:
  # local:
  #   enabled: true
  #   server_dir: "~/.task_sync_server"

  # Remote sync server — uncomment and fill in all fields:
  # Store encryption_secret here only, never pass it on the command line.
  # remote:
  #   enabled: true
  #   origin: "https://your-sync-server.example.com"
  #   client_id: "your-uuid"
  #   encryption_secret: "your-secret"
```

## CLI overrides

All settings can be overridden at startup. Sync-specific flags:

```bash
# Disable sync for this run
uv run -m taskmajor.bootstrap.server --no-sync

# Use manual mode with a specific local sync directory
uv run -m taskmajor.bootstrap.server --sync-mode manual --sync-local-dir ~/.my_sync

# Override interval
uv run -m taskmajor.bootstrap.server --sync-interval 60
```

See [Agent Configuration](../developer/agent-integrations.md) for the full CLI reference.

## Docker

Mount the config directory read-only:

```yaml
volumes:
  - ./app/config:/app/config:ro
  - taskmajor_data:/data/task
```

The container reads `config.yaml` from `/app/config`.

## Notes

- Missing config files fall back to built-in defaults
- **Profile Configuration** — Most TaskMajor customization (UDAs, contexts, resources, instructions) is declared in profiles (`taskmajor/profiles/`), not in `config.yaml`. See [Profiles](../user-guides/profiles/profile-system.md) for details.
