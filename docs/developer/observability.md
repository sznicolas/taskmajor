# TaskMajor Observability

TaskMajor emits the three OpenTelemetry signals (traces, logs, metrics) through the OTLP standard, and it works with any backend (Grafana Stack, Elasticsearch, Datadog, Jaeger…).

## Emitted signals

| Signal     | Name / pattern                       | Description                                |
|------------|--------------------------------------|--------------------------------------------|
| **Traces** | one span per MCP call                | Duration, ok/error status, tool attributes |
| **Logs**   | Python logging bridged to OTel       | Correlated with spans via `trace_id`/`span_id` |
| **Metrics** | `mcp.calls.total`, `mcp.call.duration` | Counters and histograms per tool       |

### Semantic attributes on spans

| Attribute           | Values                   |
|---------------------|--------------------------|
| `mcp.call.type`     | `tool` \| `resource`     |
| `mcp.tool.name`     | function name            |
| `mcp.resource.uri`  | URI (resources only)     |
| `mcp.call.status`   | `ok` \| `error`          |
| `service.name`      | `TASKMAJOR_SERVER_NAME`    |

---

## Environment variables

```bash
# Log level (DEBUG, INFO, WARNING, ERROR)
TASKMAJOR_LOG_LEVEL=INFO

# Console format: "text" (dev) or "json" (prod/Loki)
TASKMAJOR_LOG_FORMAT=json

# Disable OTLP export (console only)
TASKMAJOR_OTEL_ENABLED=false

# Common OTLP endpoint (fallback if specific endpoints aren't set)
TASKMAJOR_OTEL_EXPORTER_ENDPOINT=http://localhost:4317

# Per-signal endpoints (override common endpoint)
TASKMAJOR_OTEL_TRACES_ENDPOINT=http://localhost:4317
TASKMAJOR_OTEL_METRICS_ENDPOINT=http://localhost:4317
TASKMAJOR_OTEL_LOGS_ENDPOINT=http://localhost:4317

# Service name (displayed in Grafana)
TASKMAJOR_OTEL_SERVICE_NAME=taskmajor-prod
```

---

## Alloy Configuration (Grafana)

Alloy receives TaskMajor OTLP data and routes it to Tempo, Loki, and Mimir.

> **Note:** The configuration files below (`alloy-config.alloy`, `docker-compose.observability.yml`, `tempo.yaml`, `mimir.yaml`) are **example templates** to be created in your own infrastructure — they are not shipped in this repository.

### `alloy-config.alloy`

```alloy
// ─── TaskMajor OTLP ingestion ─────────────────────────────────────────────────
otelcol.receiver.otlp "taskmajor" {
  grpc {
    endpoint = "0.0.0.0:4317"
  }
  http {
    endpoint = "0.0.0.0:4318"
  }
  output {
    traces  = [otelcol.exporter.otlp.tempo.input]
    metrics = [otelcol.exporter.prometheus.mimir.input]
    logs    = [otelcol.exporter.loki.default.input]
  }
}

// ─── Traces → Tempo ──────────────────────────────────────────────────────────
otelcol.exporter.otlp "tempo" {
  client {
    endpoint = "tempo:4317"
    tls { insecure = true }
  }
}

// ─── Metrics → Mimir (via Prometheus remote_write) ────────────────────────────
otelcol.exporter.prometheus "mimir" {
  forward_to = [prometheus.remote_write.mimir.receiver]
}

prometheus.remote_write "mimir" {
  endpoint {
    url = "http://mimir:9009/api/v1/push"
  }
}

// ─── Logs → Loki ─────────────────────────────────────────────────────────────
otelcol.exporter.loki "default" {
  forward_to = [loki.write.default.receiver]
}

loki.write "default" {
  endpoint {
    url = "http://loki:3100/loki/api/v1/push"
  }
}
```

---

## Local development Docker Compose

Run a complete stack (Alloy + Tempo + Loki + Mimir + Grafana) locally.

### `docker-compose.observability.yml`

```yaml
version: "3.9"

services:

  # ── OTLP collector ───────────────────────────────────────────────────────────
  alloy:
    image: grafana/alloy:latest
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
      - "12345:12345" # UI Alloy
    volumes:
      - ./alloy-config.alloy:/etc/alloy/config.alloy
    command: ["run", "--server.http.listen-addr=0.0.0.0:12345", "/etc/alloy/config.alloy"]
    depends_on: [tempo, loki, mimir]

  # ── Traces ───────────────────────────────────────────────────────────────────
  tempo:
    image: grafana/tempo:latest
    ports:
      - "3200:3200"
      - "4317"        # OTLP gRPC internal
    command: ["-config.file=/etc/tempo.yaml"]
    volumes:
      - ./tempo.yaml:/etc/tempo.yaml
      - tempo-data:/var/tempo

  # ── Logs ─────────────────────────────────────────────────────────────────────
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    command: ["-config.file=/etc/loki/local-config.yaml"]
    volumes:
      - loki-data:/loki

  # ── Metrics ──────────────────────────────────────────────────────────────────
  mimir:
    image: grafana/mimir:latest
    ports:
      - "9009:9009"
    command: ["--config.file=/etc/mimir.yaml"]
    volumes:
      - ./mimir.yaml:/etc/mimir.yaml
      - mimir-data:/data

  # ── Visualization ───────────────────────────────────────────────────────────
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_AUTH_ANONYMOUS_ENABLED: "true"
      GF_AUTH_ANONYMOUS_ORG_ROLE: "Admin"
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning
      - grafana-data:/var/lib/grafana
    depends_on: [tempo, loki, mimir]

volumes:
  tempo-data:
  loki-data:
  mimir-data:
  grafana-data:
```

### Quick configuration for TaskMajor

```bash
# Start the stack
docker compose -f docker-compose.observability.yml up -d

# Configure TaskMajor to point to local Alloy
export TASKMAJOR_LOG_FORMAT=json
export TASKMAJOR_OTEL_ENABLED=true
export TASKMAJOR_OTEL_EXPORTER_ENDPOINT=http://localhost:4317
export TASKMAJOR_OTEL_SERVICE_NAME=taskmajor-dev

# Start the server
uv run -m taskmajor.bootstrap.server
```

Grafana is available at http://localhost:3000 — Tempo, Loki, and Mimir datasources must be configured manually or via provisioning.

---

## Development mode (without OTLP)

```bash
# Console logs in text mode, without OTLP export
TASKMAJOR_LOG_FORMAT=text TASKMAJOR_OTEL_ENABLED=false uv run -m taskmajor.bootstrap.server
```

Logs appear like this:
```
2026-03-20 21:00:00,123 INFO taskmajor.domains.observability.instrumentation: MCP tool done_task OK (12.3ms)
```

## Production mode (JSON + Alloy)

```bash
TASKMAJOR_LOG_FORMAT=json \
TASKMAJOR_OTEL_ENABLED=true \
TASKMAJOR_OTEL_EXPORTER_ENDPOINT=http://alloy.internal:4317 \
TASKMAJOR_OTEL_SERVICE_NAME=taskmajor-prod \
uv run -m taskmajor.bootstrap.server
```

Each log line is a JSON object with `trace_id` and `span_id` for Loki ↔ Tempo correlation.

---

## Troubleshooting

Common observability issues and quick checks:

- OpenTelemetry exporter unreachable: verify TASKMAJOR_OTEL_EXPORTER_ENDPOINT and network connectivity to the OTLP collector.
- Missing metrics: confirm TASKMAJOR_OTEL_METRICS_ENDPOINT and that the collector is configured to forward metrics to your backend.
- Logs not correlated: ensure TASKMAJOR_LOG_FORMAT=json and TASKMAJOR_OTEL_ENABLED=true so trace IDs are present.
- Debugging traces: set TASKMAJOR_LOG_LEVEL=DEBUG and inspect spans in your tracing backend.

If the problem persists, consult the full Observability guide or open an issue with your logs and configuration.
