"""Tests for mcp/resources/date_resources.py."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from taskmajor.mcp.resources.date_resources import register_date_resources


def _capture_get_now(tw, task_config):
    """Register date resources and return the captured get_now handler."""
    captured: dict = {}

    class CaptureMCP:
        def resource(self, uri, **kwargs):
            def decorator(fn):
                captured[uri] = fn
                return fn
            return decorator

    register_date_resources(CaptureMCP(), tw, task_config)
    return captured.get("taskmajor://now")


class TestGetNowResource:
    def test_happy_path_returns_valid_json_structure(self):
        tw = MagicMock()
        tw.task_calc.return_value = "2026-05-14T23:59:59Z"
        cfg = MagicMock()
        cfg.get_timezone.return_value = "Europe/Paris"

        fn = _capture_get_now(tw, cfg)
        result = json.loads(fn())

        assert "now" in result
        assert "date" in result
        assert "time" in result
        assert "weekday" in result
        assert result["timezone"] == "Europe/Paris"
        assert result["shortcuts"]["eod"] == "2026-05-14T23:59:59Z"
        assert result["shortcuts"]["eow"] == "2026-05-14T23:59:59Z"
        assert result["shortcuts"]["eom"] == "2026-05-14T23:59:59Z"

    def test_task_calc_exception_sets_shortcut_to_none(self):
        tw = MagicMock()
        tw.task_calc.side_effect = RuntimeError("task binary unavailable")
        cfg = MagicMock()
        cfg.get_timezone.return_value = "UTC"

        fn = _capture_get_now(tw, cfg)
        result = json.loads(fn())

        assert result["shortcuts"]["eod"] is None
        assert result["shortcuts"]["eow"] is None
        assert result["shortcuts"]["eom"] is None

    def test_partial_task_calc_failure_sets_only_failed_shortcut_to_none(self):
        tw = MagicMock()
        call_count = [0]

        def calc_side_effect(expr):
            call_count[0] += 1
            if call_count[0] == 2:  # second call (eow) fails
                raise RuntimeError("eow unavailable")
            return "2026-05-31T00:00:00Z"

        tw.task_calc.side_effect = calc_side_effect
        cfg = MagicMock()
        cfg.get_timezone.return_value = "UTC"

        fn = _capture_get_now(tw, cfg)
        result = json.loads(fn())

        assert result["shortcuts"]["eod"] == "2026-05-31T00:00:00Z"
        assert result["shortcuts"]["eow"] is None
        assert result["shortcuts"]["eom"] == "2026-05-31T00:00:00Z"

    def test_now_date_time_fields_are_formatted_strings(self):
        tw = MagicMock()
        tw.task_calc.return_value = "2026-05-14T23:59:59Z"
        cfg = MagicMock()
        cfg.get_timezone.return_value = "UTC"

        fn = _capture_get_now(tw, cfg)
        result = json.loads(fn())

        # now: ISO-like datetime string
        assert "T" in result["now"]
        # date: YYYY-MM-DD
        assert len(result["date"]) == 10
        # time: HH:MM:SS
        assert len(result["time"]) == 8
        assert result["weekday"] != ""
