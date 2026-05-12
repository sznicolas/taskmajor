"""OpenTelemetry helpers shared between TaskMajor components."""

from __future__ import annotations

import logging
import sys
from collections.abc import Mapping

from opentelemetry import metrics, trace

try:
    from opentelemetry import logs as otel_logs  # type: ignore[attr-defined]
except ImportError:
    from opentelemetry import _logs as otel_logs  # type: ignore[import]
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

__all__ = ["configure_telemetry"]

_configured = False


def _build_console_formatter(log_format: str) -> logging.Formatter:
    """Return a log formatter appropriate for the chosen format."""
    if log_format == "json":
        try:
            from pythonjsonlogger.json import JsonFormatter  # type: ignore[import]

            return JsonFormatter(
                fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(trace_id)s %(span_id)s",
                rename_fields={"levelname": "level", "asctime": "timestamp"},
            )
        except ImportError:
            logging.warning("python-json-logger not available; falling back to text format")
    return logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")


class _SpanContextFilter(logging.Filter):
    """Inject the current OTel trace_id and span_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        from opentelemetry import trace as _trace

        span = _trace.get_current_span()
        ctx = span.get_span_context()
        if ctx.is_valid:
            record.trace_id = format(ctx.trace_id, "032x")
            record.span_id = format(ctx.span_id, "016x")
        else:
            record.trace_id = None
            record.span_id = None
        return True


def configure_telemetry(
    service_name: str,
    *,
    log_level: int = logging.DEBUG,
    log_format: str = "text",
    otel_enabled: bool = True,
    traces_endpoint: str | None = None,
    metrics_endpoint: str | None = None,
    logs_endpoint: str | None = None,
    resource_attributes: Mapping[str, str] | None = None,
) -> None:
    """
    Configure logging and OpenTelemetry providers for traces, metrics, and logs.

    Args:
        service_name: The name reported as ``service.name``.
        log_level: Python logging level for the console handler.
        log_format: ``"text"`` for human-readable output, ``"json"`` for structured JSON.
        otel_enabled: When ``False``, OTLP exporters are skipped (console logging still works).
        traces_endpoint: OTLP endpoint used for traces export.
        metrics_endpoint: OTLP endpoint used for metrics export.
        logs_endpoint: OTLP endpoint used for log export.
        resource_attributes: Additional resource attributes attached to all signals.
    """
    global _configured
    if _configured:
        return

    # --- Console handler (always active) ---
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(_build_console_formatter(log_format))
    console_handler.addFilter(_SpanContextFilter())
    root_logger.addHandler(console_handler)

    # --- OpenTelemetry providers ---
    resource = Resource.create(
        {
            "service.name": service_name,
            **(resource_attributes or {}),
        }
    )

    # Traces
    tracer_provider = TracerProvider(resource=resource)
    if otel_enabled and traces_endpoint:
        tracer_provider.add_span_processor(
            BatchSpanProcessor(_build_span_exporter(traces_endpoint))
        )
    trace.set_tracer_provider(tracer_provider)

    # Metrics
    if otel_enabled and metrics_endpoint:
        metric_reader = PeriodicExportingMetricReader(_build_metric_exporter(metrics_endpoint))
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    else:
        meter_provider = MeterProvider(resource=resource)
    metrics.set_meter_provider(meter_provider)

    # Logs — bridge OTel LoggerProvider to Python logging
    logger_provider = LoggerProvider(resource=resource)
    if otel_enabled and logs_endpoint:
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(_build_log_exporter(logs_endpoint))
        )
    otel_logs.set_logger_provider(logger_provider)
    otel_handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    root_logger.addHandler(otel_handler)

    _configured = True


# --- Exporter factories (isolated for future OTLP/HTTP support) ---


def _build_span_exporter(endpoint: str):
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    return OTLPSpanExporter(endpoint=endpoint)


def _build_metric_exporter(endpoint: str):
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

    return OTLPMetricExporter(endpoint=endpoint)


def _build_log_exporter(endpoint: str):
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

    return OTLPLogExporter(endpoint=endpoint)
