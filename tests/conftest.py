"""
Shared test fixtures and configuration for TaskMajor test suite.

This module provides reusable fixtures for all tests. Pytest automatically
discovers this file and makes all fixtures available to tests.

Fixtures are organized by:
1. Mock objects (TaskWarrior, TaskService)
2. Sample data (tasks, filters)
3. Temporary files and directories
4. Configuration objects
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock

import pytest
from taskwarrior import TaskOutputDTO

from taskmajor.domains.tasks import TaskService
from taskmajor.domains.taskwarrior.config import TaskMajorConfig

# ============================================================================
# Mock Objects
# ============================================================================


@pytest.fixture
def mock_taskwarrior():
    """Mock TaskWarrior client.

    Use this fixture when you want a pre-configured Mock for TaskWarrior.
    It's already set up with basic return values.

    Example:
        def test_something(mock_taskwarrior):
            mock_taskwarrior.add_task.return_value = _task("Test")
            service = TaskService(mock_taskwarrior)
            result = service.add_task(...)
            assert result.description == "Test"
    """
    mock = Mock()
    mock.get_tasks.return_value = []
    mock.add_task.return_value = None
    mock.modify_task.return_value = None
    mock.delete_task.return_value = True
    return mock


@pytest.fixture
def mock_task_service(mock_taskwarrior):
    """Pre-configured TaskService with mocked TaskWarrior.

    Use this when you want to test code that uses TaskService without
    actually calling TaskWarrior.

    Example:
        def test_something(mock_task_service):
            result = mock_task_service.query_tasks(project="Work")
            assert result['total'] == 0  # Empty by default
    """
    return TaskService(mock_taskwarrior)


# ============================================================================
# Sample Data
# ============================================================================


def _task(
    description: str,
    *,
    task_uuid: str | None = None,
    task_id: int = 1,
    status: str = "pending",
    project: str | None = None,
    priority: str | None = None,
    tags: list[str] | None = None,
    due: datetime | None = None,
    urgency: float | None = None,
    udas: dict | None = None,
) -> Any:
    """Helper function to create TaskOutputDTO objects for testing.

    This is used internally by fixtures and can be imported for custom test data:

    Example:
        from tests.conftest import _task

        def test_custom(mock_taskwarrior):
            my_task = _task("Buy milk", project="Shopping", priority="H")
            mock_taskwarrior.get_tasks.return_value = [my_task]
            ...
    """
    payload = {
        "id": task_id,
        "uuid": uuid.UUID(task_uuid or "12345678-1234-1234-1234-123456789012"),
        "description": description,
        "status": status,
        "project": project,
        "priority": priority,
        "tags": tags or [],
        "udas": udas or {},
    }
    if due is not None:
        payload["due"] = due
    if urgency is not None:
        payload["urgency"] = urgency
    return TaskOutputDTO(**cast(Any, payload))


@pytest.fixture
def sample_task() -> TaskOutputDTO:
    """A realistic sample task for testing.

    Returns a pending task with all common fields populated.

    Example:
        def test_serialization(sample_task):
            assert sample_task.uuid is not None
            assert sample_task.status == "pending"
    """
    now = datetime.now(UTC)
    return _task(
        "Review proposal for client",
        task_uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        task_id=1,
        status="pending",
        project="Work",
        priority="H",
        tags=["review", "urgent"],
        due=now + timedelta(days=3),
        urgency=42.5,
    )


@pytest.fixture
def sample_tasks() -> list[TaskOutputDTO]:
    """Multiple realistic sample tasks for testing pagination and filtering.

    Returns 6 diverse tasks with different projects, priorities, and statuses.

    Example:
        def test_filtering(mock_taskwarrior, sample_tasks):
            mock_taskwarrior.get_tasks.return_value = sample_tasks
            service = TaskService(mock_taskwarrior)
            result = service.query_tasks(project="Work")
            # Will include tasks 2, 4 (both have project="Work")
            assert result['total'] >= 2
    """
    now = datetime.now(UTC)
    return [
        _task("Fix bug in auth module", task_uuid="11111111-1111-1111-1111-111111111111",
              task_id=1, status="pending", project="Work", priority="H",
              due=now + timedelta(days=1)),
        _task("Review code for API", task_uuid="22222222-2222-2222-2222-222222222222",
              task_id=2, status="pending", project="Work", priority="M",
              due=now + timedelta(days=3)),
        _task("Prepare for meeting", task_uuid="33333333-3333-3333-3333-333333333333",
              task_id=3, status="pending", project="Inbox", priority="M",
              tags=["review"]),
        _task("Schedule dentist", task_uuid="44444444-4444-4444-4444-444444444444",
              task_id=4, status="completed", project="Personal", priority="L",
              due=now - timedelta(days=2)),
        _task("Learn Rust", task_uuid="55555555-5555-5555-5555-555555555555",
              task_id=5, status="pending", project=None, priority="L"),
        _task("Finished project", task_uuid="66666666-6666-6666-6666-666666666666",
              task_id=6, status="completed", project="Archive", priority=None),
    ]


# ============================================================================
# Configuration
# ============================================================================


@pytest.fixture
def default_config() -> TaskMajorConfig:
    """Default TaskMajor configuration for testing.

    Use this for tests that need configuration values without mocking
    environment variables.

    Example:
        def test_config(default_config):
            assert default_config.server_port == 8888
    """
    return TaskMajorConfig()


@pytest.fixture
def custom_config() -> TaskMajorConfig:
    """Custom TaskMajor configuration for testing alternate settings.

    Returns a config with non-standard values to test different scenarios.

    Example:
        def test_custom_port(custom_config):
            assert custom_config.server_port == 9999
    """
    config = TaskMajorConfig()
    config.server_port = 9999
    return config


# ============================================================================
# Temporary Files and Directories
# ============================================================================


@pytest.fixture
def tmp_taskrc(tmp_path: Path) -> Path:
    """Temporary TaskWarrior taskrc file for testing.

    Returns path to a temporary taskrc file that exists but is empty.
    Use this when tests need to interact with the filesystem.

    Example:
        def test_taskrc(tmp_taskrc):
            taskrc_content = tmp_taskrc.read_text()
            assert len(taskrc_content) == 0
    """
    taskrc = tmp_path / "taskrc"
    taskrc.touch()
    return taskrc


@pytest.fixture
def tmp_taskdata(tmp_path: Path) -> Path:
    """Temporary TaskWarrior data directory for testing.

    Returns path to a temporary directory for TaskWarrior task storage.

    Example:
        def test_with_data(tmp_taskdata):
            # Create task files
            (tmp_taskdata / "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.json").write_text(...)
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


# ============================================================================
# Hypothesis Strategies (for use with pytest fixtures)
# ============================================================================


@pytest.fixture
def hypothesis_settings():
    """Return a function to create Hypothesis settings.

    Use this in property-based tests to configure Hypothesis behavior.

    Example:
        from hypothesis import given, settings, strategies as st

        def test_property(hypothesis_settings):
            @given(limit=st.integers(1, 100))
            @settings(hypothesis_settings().max_examples(50))
            def inner(limit):
                assert limit > 0
            inner()
    """
    from hypothesis import settings

    def _settings():
        return settings(
            deadline=None,  # Don't timeout on slow tests
            max_examples=100,  # Default number of examples
        )

    return _settings


# ============================================================================
# Pytest Hooks and Configuration
# ============================================================================


def pytest_configure(config):
    """Configure pytest at startup.

    This hook is called before test collection. We use it to register
    custom markers and configure pytest behavior.
    """
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests",
    )
    config.addinivalue_line(
        "markers",
        "property: marks tests as property-based (Hypothesis)",
    )
    # Lightweight support for async tests that use @pytest.mark.asyncio.
    config.addinivalue_line(
        "markers",
        "asyncio: mark tests to run in an asyncio event loop (lightweight support)",
    )


def pytest_collection_modifyitems(config, items):
    """Modify test items during collection.

    This hook is called after tests are collected. We use it to apply
    custom behavior to specific test files or functions.
    """
    for item in items:
        # Mark all tests in test_edge_cases.py with the 'slow' marker
        if "test_edge_cases" in str(item.fspath):
            item.add_marker(pytest.mark.slow)

        # Mark all tests in test_property_based.py with the 'property' marker
        if "test_property_based" in str(item.fspath):
            item.add_marker(pytest.mark.property)

        # Mark integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


def pytest_pyfunc_call(pyfuncitem):
    """Run coroutine test functions under a fresh asyncio event loop.

    This provides lightweight async test support when pytest-asyncio is not
    installed (sufficient for these tests which don't rely on advanced
    asyncio fixtures).
    """
    import asyncio
    import inspect

    testfunction = pyfuncitem.obj
    if inspect.iscoroutinefunction(testfunction):
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(testfunction(**pyfuncitem.funcargs))
        finally:
            asyncio.set_event_loop(None)
            loop.close()
        return True
    return None
