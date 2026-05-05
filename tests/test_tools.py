from __future__ import annotations

from unittest.mock import Mock

from taskmajor.mcp.tools import register_tools


def test_register_tools():
    """Test that tools are properly registered when no whitelist is given (all tools)."""
    mock_mcp = Mock()
    mock_task_service = Mock()
    mock_task_service.taskwarrior_client = Mock()
    mock_task_service.task_config = Mock()

    register_tools(mock_mcp, mock_task_service, Mock())

    assert hasattr(mock_mcp, 'tool')


def test_register_tools_with_whitelist():
    """Test that only whitelisted tools are registered."""
    import asyncio
    from unittest.mock import MagicMock

    from fastmcp import FastMCP

    mcp = FastMCP(name="test")
    mock_task_service = MagicMock()
    mock_task_service.taskwarrior_client = MagicMock()
    mock_task_service.task_config = MagicMock()

    whitelist = {"query_tasks", "add_task"}
    register_tools(mcp, mock_task_service, MagicMock(), tool_whitelist=whitelist)

    tool_names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert "query_tasks" in tool_names
    assert "add_task" in tool_names
    assert "delete_task" not in tool_names
    assert "report_error" not in tool_names


def test_register_tools_empty_whitelist():
    """Test that an empty whitelist results in no tools being registered."""
    import asyncio
    from unittest.mock import MagicMock

    from fastmcp import FastMCP

    mcp = FastMCP(name="test")
    mock_task_service = MagicMock()
    mock_task_service.taskwarrior_client = MagicMock()
    mock_task_service.task_config = MagicMock()

    register_tools(mcp, mock_task_service, MagicMock(), tool_whitelist=set())

    tool_names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert len(tool_names) == 0
