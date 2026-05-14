"""Tests for mcp/templates/date_templates.py."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from taskmajor.mcp.templates.date_templates import register_date_templates


def _capture_get_date(taskwarrior_client):
    """Register date templates and return the captured get_date handler."""
    captured: dict = {}

    class CaptureMCP:
        def resource(self, uri, **kwargs):
            def decorator(fn):
                captured[uri] = fn
                return fn

            return decorator

    register_date_templates(CaptureMCP(), taskwarrior_client)
    return captured.get("taskmajor://date/{expression}")


class TestGetDateTemplate:
    def test_happy_path_with_time_part(self):
        tw = MagicMock()
        tw.task_calc.return_value = "2026-05-14T18:30:00"

        fn = _capture_get_date(tw)
        result = json.loads(fn("tomorrow"))

        assert result["expression"] == "tomorrow"
        assert result["resolved"] == "2026-05-14T18:30:00"
        assert result["date"] == "2026-05-14"
        assert result["time"] == "18:30:00"

    def test_happy_path_without_time_part(self):
        tw = MagicMock()
        tw.task_calc.return_value = "2026-05-14"  # no T separator

        fn = _capture_get_date(tw)
        result = json.loads(fn("today"))

        assert result["date"] == "2026-05-14"
        assert result["time"] is None

    def test_exception_returns_error_json(self):
        tw = MagicMock()
        tw.task_calc.side_effect = RuntimeError("task binary not found")

        fn = _capture_get_date(tw)
        result = json.loads(fn("bad-expr"))

        assert result["expression"] == "bad-expr"
        assert "error" in result
        assert "task binary not found" in result["error"]

    def test_handler_is_registered_under_correct_uri(self):
        tw = MagicMock()
        tw.task_calc.return_value = "2026-01-01T00:00:00"

        captured: dict = {}

        class CaptureMCP:
            def resource(self, uri, **kwargs):
                def decorator(fn):
                    captured[uri] = fn
                    return fn

                return decorator

        register_date_templates(CaptureMCP(), tw)
        assert "taskmajor://date/{expression}" in captured
