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
server_port: 7777
server_name: TaskMajor Server

# TaskWarrior
taskrc: /data/task/.taskrc
taskdata: /data/task

# Profile
profile: standard                   # Profile name or path

# Logging
log_level: INFO
log_format: text
agent_errors_path: /data/task/agent_errors.jsonl

# Observability (OpenTelemetry)
otel_enabled: true
otel_service_name: TaskMajor
```

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
