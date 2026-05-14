"""Tests for mcp/resources/_utils.py."""

from __future__ import annotations

import json

from taskmajor.mcp.resources._utils import resource_response


class TestResourceResponse:
    def test_success_returns_json_serialized_result(self):
        result = resource_response(lambda: {"key": "value", "count": 42})

        parsed = json.loads(result)
        assert parsed == {"key": "value", "count": 42}

    def test_success_serializes_non_json_types_via_default_str(self):
        from datetime import datetime

        dt = datetime(2026, 5, 14, 12, 0, 0)
        result = resource_response(lambda: {"ts": dt})

        parsed = json.loads(result)
        assert "ts" in parsed

    def test_exception_returns_error_json(self):
        def raising():
            raise ValueError("something went wrong")

        result = resource_response(raising)
        parsed = json.loads(result)

        assert "error" in parsed
        assert "something went wrong" in parsed["error"]

    def test_exception_result_is_valid_json(self):
        result = resource_response(lambda: 1 / 0)

        parsed = json.loads(result)
        assert isinstance(parsed, dict)
