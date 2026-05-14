"""Tests for AgentErrorLog — append and read_all coverage."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from taskmajor.domains.observability.agent_error_log import AgentErrorLog


class TestAgentErrorLogAppend:
    def test_append_returns_entry_dict(self, tmp_path: Path):
        log = AgentErrorLog(str(tmp_path / "errors.jsonl"))
        entry = log.append("add_task", {"description": "x"}, "boom")
        assert entry["tool_name"] == "add_task"
        assert entry["error"] == "boom"
        assert entry["parameters"] == {"description": "x"}
        assert "timestamp" in entry

    def test_append_writes_line_to_file(self, tmp_path: Path):
        path = tmp_path / "errors.jsonl"
        log = AgentErrorLog(str(path))
        log.append("my_tool", {}, "some error")
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["tool_name"] == "my_tool"

    def test_append_multiple_entries(self, tmp_path: Path):
        path = tmp_path / "errors.jsonl"
        log = AgentErrorLog(str(path))
        log.append("tool_a", {}, "err1")
        log.append("tool_b", {}, "err2")
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 2

    def test_append_creates_parent_dirs(self, tmp_path: Path):
        nested = tmp_path / "a" / "b" / "c" / "errors.jsonl"
        log = AgentErrorLog(str(nested))
        log.append("t", {}, "e")
        assert nested.exists()

    def test_append_oserror_does_not_raise(self, tmp_path: Path):
        log = AgentErrorLog(str(tmp_path / "errors.jsonl"))
        with patch.object(Path, "open", side_effect=OSError("disk full")):
            # Should not raise — logs the error instead
            entry = log.append("t", {}, "e")
        assert entry["tool_name"] == "t"


class TestAgentErrorLogReadAll:
    def test_read_all_returns_empty_when_file_missing(self, tmp_path: Path):
        log = AgentErrorLog(str(tmp_path / "missing.jsonl"))
        assert log.read_all() == []

    def test_read_all_returns_entries_newest_first(self, tmp_path: Path):
        path = tmp_path / "errors.jsonl"
        log = AgentErrorLog(str(path))
        log.append("tool_a", {}, "first")
        log.append("tool_b", {}, "second")
        log.append("tool_c", {}, "third")

        entries = log.read_all()
        assert len(entries) == 3
        # newest-first ordering
        assert entries[0]["tool_name"] == "tool_c"
        assert entries[1]["tool_name"] == "tool_b"
        assert entries[2]["tool_name"] == "tool_a"

    def test_read_all_single_entry(self, tmp_path: Path):
        path = tmp_path / "errors.jsonl"
        log = AgentErrorLog(str(path))
        log.append("only_tool", {"k": "v"}, "only error")

        entries = log.read_all()
        assert len(entries) == 1
        assert entries[0]["error"] == "only error"

    def test_read_all_skips_blank_lines(self, tmp_path: Path):
        path = tmp_path / "errors.jsonl"
        path.write_text('{"tool_name":"t","error":"e","parameters":{},"timestamp":"x"}\n\n\n')
        log = AgentErrorLog(str(path))
        entries = log.read_all()
        assert len(entries) == 1

    def test_read_all_oserror_returns_empty(self, tmp_path: Path):
        path = tmp_path / "errors.jsonl"
        path.write_text('{"tool_name":"t","error":"e","parameters":{},"timestamp":"x"}\n')
        log = AgentErrorLog(str(path))
        with patch.object(Path, "open", side_effect=OSError("read error")):
            entries = log.read_all()
        assert entries == []
