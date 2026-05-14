"""Tests for taskmajor/mcp/errors.py."""

from __future__ import annotations

import pytest

from taskmajor.mcp.errors import (
    CONFIG_ERROR,
    INTERNAL_ERROR,
    INVALID_INPUT,
    PROFILE_ERROR,
    TASK_ALREADY_STARTED,
    TASK_ALREADY_STOPPED,
    TASK_NOT_FOUND,
    ToolResult,
    fail,
    ok,
)

# ---------------------------------------------------------------------------
# Error code constants
# ---------------------------------------------------------------------------


class TestErrorCodeConstants:
    def test_all_constants_are_strings(self):
        for code in (
            TASK_NOT_FOUND,
            INVALID_INPUT,
            TASK_ALREADY_STARTED,
            TASK_ALREADY_STOPPED,
            CONFIG_ERROR,
            PROFILE_ERROR,
            INTERNAL_ERROR,
        ):
            assert isinstance(code, str)

    def test_constants_are_distinct(self):
        codes = [
            TASK_NOT_FOUND,
            INVALID_INPUT,
            TASK_ALREADY_STARTED,
            TASK_ALREADY_STOPPED,
            CONFIG_ERROR,
            PROFILE_ERROR,
            INTERNAL_ERROR,
        ]
        assert len(codes) == len(set(codes))


# ---------------------------------------------------------------------------
# ToolResult model
# ---------------------------------------------------------------------------


class TestToolResult:
    def test_success_result(self):
        result = ToolResult(success=True, data={"key": "value"})
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.error_code is None

    def test_failure_result(self):
        result = ToolResult(success=False, error="something went wrong", error_code=TASK_NOT_FOUND)
        assert result.success is False
        assert result.error == "something went wrong"
        assert result.error_code == TASK_NOT_FOUND
        assert result.data is None

    def test_model_dump_includes_all_fields(self):
        result = ToolResult(success=True, data=42)
        dumped = result.model_dump()
        assert "success" in dumped
        assert "error" in dumped
        assert "error_code" in dumped
        assert "data" in dumped

    def test_data_can_be_any_type(self):
        for value in (None, 0, "string", [1, 2], {"a": 1}, True):
            result = ToolResult(success=True, data=value)
            assert result.data == value


# ---------------------------------------------------------------------------
# ok() helper
# ---------------------------------------------------------------------------


class TestOk:
    def test_ok_sets_success_true(self):
        result = ok("done")
        assert result["success"] is True

    def test_ok_puts_payload_in_data(self):
        payload = {"tasks": [], "total": 0}
        result = ok(payload)
        assert result["data"] == payload

    def test_ok_error_fields_are_none(self):
        result = ok("anything")
        assert result["error"] is None
        assert result["error_code"] is None

    def test_ok_returns_dict(self):
        assert isinstance(ok("x"), dict)

    def test_ok_with_none_data(self):
        result = ok(None)
        assert result["success"] is True
        assert result["data"] is None

    def test_ok_with_list_data(self):
        result = ok([1, 2, 3])
        assert result["data"] == [1, 2, 3]


# ---------------------------------------------------------------------------
# fail() helper
# ---------------------------------------------------------------------------


class TestFail:
    def test_fail_sets_success_false(self):
        result = fail("error message")
        assert result["success"] is False

    def test_fail_sets_error_message(self):
        result = fail("Task not found")
        assert result["error"] == "Task not found"

    def test_fail_default_code_is_internal_error(self):
        result = fail("oops")
        assert result["error_code"] == INTERNAL_ERROR

    def test_fail_custom_code(self):
        result = fail("Task 42 not found", TASK_NOT_FOUND)
        assert result["error_code"] == TASK_NOT_FOUND

    def test_fail_data_is_none(self):
        result = fail("error")
        assert result["data"] is None

    def test_fail_returns_dict(self):
        assert isinstance(fail("error"), dict)

    @pytest.mark.parametrize(
        "code",
        [TASK_NOT_FOUND, INVALID_INPUT, TASK_ALREADY_STARTED, TASK_ALREADY_STOPPED, CONFIG_ERROR, PROFILE_ERROR, INTERNAL_ERROR],
    )
    def test_fail_accepts_all_error_codes(self, code: str):
        result = fail("msg", code)
        assert result["error_code"] == code
