# Full documentation: docker-compose (local)

This document describes the local usage of the docker-compose files in this repository (scope: development/local only). It includes an inventory of services, environment variables, volumes, ports, start commands, and troubleshooting tips.

## Overview
The project exposes one primary service: taskmajor. The root Dockerfile is multi-stage: it builds TaskWarrior from source and then builds the Python application.

## Services (excerpt from docker/docker-compose.yaml)
- taskmajor
  - image: taskmajor:latest
  - ports: 7777:7777
  - volumes:
    - ./tests/fixtures/taskrc:/etc/task/.taskrc:ro
    - taskmajor_data:/data/task
  - environment (examples):
    - TASKMAJOR_SERVER_PORT=7777
    - TASKMAJOR_SERVER_HOST=0.0.0.0

## Environment variables (local)
Useful variables for local development. Use the `.env` file or export variables in your shell. All variables use the TASKMAJOR_ prefix.

| Variable | Default (local) | Required | Description |
|---|---:|---:|---|
| TASKMAJOR_SERVER_HOST | 0.0.0.0 | No | Server bind address
| TASKMAJOR_SERVER_PORT | 7777 | No | HTTP port exposed by the app (mapping in docker-compose.yaml)
| TASKMAJOR_SERVER_NAME | TaskMajor Server | No | Display name visible in metadata and logs
| TASKMAJOR_TASKRC | ~/.taskrc_mcp | No | Path to TaskWarrior config file mounted into container (`/etc/task/.taskrc` in compose)
| TASKMAJOR_TASKDATA | ~/.task_mcp | No | Path to TaskWarrior data directory (mounted at `/data/task` in compose)
| TASKMAJOR_LOG_LEVEL | INFO | No | Logging level (DEBUG, INFO, WARNING, ERROR)
| TASKMAJOR_LOG_FORMAT | json | No | Log format: `text` or `json`
| TASKMAJOR_OTEL_ENABLED | false | No | Enable OpenTelemetry export (set true to enable)
| TASKMAJOR_OTEL_EXPORTER_ENDPOINT | http://localhost:4317 | No | OTLP exporter endpoint for traces/metrics/logs
| TASKMAJOR_OTEL_SERVICE_NAME | taskmajor | No | Service name used in telemetry

Notes:
- For local testing the `tests/fixtures/taskrc` is mounted read-only. To use your own TaskWarrior config, mount `~/.taskrc` and set TASKMAJOR_TASKRC accordingly.
- Do not commit secrets into `.env` files. For production secret management, use Docker secrets or a secret manager (out of scope for this local doc).

Examples (`.env`):

```bash
TASKMAJOR_SERVER_HOST=0.0.0.0
TASKMAJOR_SERVER_PORT=7777
TASKMAJOR_TASKRC=/config/taskrc
TASKMAJOR_TASKDATA=/data/task
TASKMAJOR_LOG_FORMAT=json
TASKMAJOR_OTEL_ENABLED=false
```

## Volumes and persistent data
- taskmajor_data (named volume)
  - Mounted at /data/task inside the container
  - Contains TaskWarrior database and persistent data
  - Backup example: docker run --rm -v taskmajor_data:/data -v $(pwd):/backup busybox tar cf /backup/taskmajor_data.tar /data

- tests/fixtures/taskrc -> /etc/task/.taskrc:ro
  - Used for reproducible local tests and examples
  - Minimal example .taskrc (dev):

```
# Minimal .taskrc example for development
data.location=/data/task
journal.location=/data/task/journal
color=off
```

You can mount your own ~/.taskrc and set TASKMAJOR_TASKRC if needed.

## Ports
- 7777:7777 — main API/server port
- Avoid conflicts by adjusting the ports mapping in docker/docker-compose.yaml or using docker compose run -p

## Dockerfile notes
- The Dockerfile compiles TaskWarrior from source (taskbuilder). Building can be long and requires compilation packages.
- The appbuilder stage uses ghcr.io/astral-sh/uv:trixie-slim with mounts to speed builds (uv.lock, pyproject.toml).
- Final image is based on python:3.12-slim and runs as non-root user (tmajor).
- CMD: python -m taskmajor.bootstrap.server

## Quick local start
1. Build the image (option 1 — from repo)

```bash
docker build -t taskmajor:latest .
```

2. Start with Docker Compose

```bash
docker compose -f docker/docker-compose.yaml up -d --build
```

3. Follow logs

```bash
docker compose -f docker/docker-compose.yaml logs -f taskmajor
```

4. Access the API

Open http://localhost:7777

## Useful development workflows
- Rebuild without cache: docker compose build --no-cache taskmajor
- Open shell inside container: docker compose run --rm --service-ports taskmajor /bin/sh
- Mount custom .taskrc: -v ~/.taskrc:/etc/task/.taskrc:ro

## Observability (local)
To test traces/logs/metrics locally, run docker-compose.observability.yml (see docs/observability.md). Then set:

```bash
export TASKMAJOR_LOG_FORMAT=json
export TASKMAJOR_OTEL_ENABLED=true
export TASKMAJOR_OTEL_EXPORTER_ENDPOINT=http://localhost:4317
export TASKMAJOR_OTEL_SERVICE_NAME=taskmajor-dev
```

## Security (local)
- Expose only required ports locally
- Do not store production secrets in the repo
- Use read-only fixtures for local testing

## Troubleshooting
- Container fails to start: docker compose logs taskmajor — check Python dependency errors or missing TaskWarrior binary
- Volume permission errors: check uid/gid, adjust ownership or mount with --user
- TaskWarrior build failure: inspect docker build logs for missing packages (libgnutls28-dev, cmake, etc.)

## References
- Dockerfile (root)
- docker/docker-compose.yaml
- docs/deployment/docker.md (this file)
- docs/observability.md (local observability stack)

---
Written for local development. For staging/production, consult infra team for secrets and networking policies.
