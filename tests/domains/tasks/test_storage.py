from __future__ import annotations

from taskwarrior import TaskOutputDTO

from taskmajor.domains.tasks import TaskStorage


def test_store_and_retrieve_task():
    """Test storing and retrieving a task"""
    storage = TaskStorage()

    # Create a test task with valid UUID and id
    task = TaskOutputDTO(
        id=1, uuid="12345678-1234-1234-1234-123456789012", description="Test task", status="pending"
    )

    # Store the task
    storage.store_task("12345678-1234-1234-1234-123456789012", task)

    # Retrieve the task
    retrieved_task = storage.get_task("12345678-1234-1234-1234-123456789012")

    assert retrieved_task is not None
    assert str(retrieved_task.uuid) == "12345678-1234-1234-1234-123456789012"
    assert retrieved_task.description == "Test task"


def test_list_tasks():
    """Test listing all tasks"""
    storage = TaskStorage()

    # Store multiple tasks with valid UUIDs and ids
    task1 = TaskOutputDTO(
        id=1, uuid="11111111-1111-1111-1111-111111111111", description="Task 1", status="pending"
    )
    task2 = TaskOutputDTO(
        id=2, uuid="22222222-2222-2222-2222-222222222222", description="Task 2", status="pending"
    )

    storage.store_task("11111111-1111-1111-1111-111111111111", task1)
    storage.store_task("22222222-2222-2222-2222-222222222222", task2)

    # List all tasks
    tasks = storage.list_tasks()

    assert len(tasks) == 2
    assert "11111111-1111-1111-1111-111111111111" in tasks
    assert "22222222-2222-2222-2222-222222222222" in tasks


def test_delete_task():
    """Test deleting a task"""
    storage = TaskStorage()

    # Store a task
    task = TaskOutputDTO(
        id=1, uuid="12345678-1234-1234-1234-123456789012", description="Test task", status="pending"
    )
    storage.store_task("12345678-1234-1234-1234-123456789012", task)

    # Delete the task
    result = storage.delete_task("12345678-1234-1234-1234-123456789012")

    assert result is True
    assert storage.get_task("12345678-1234-1234-1234-123456789012") is None


def test_refresh_task():
    """Test refreshing a task"""
    storage = TaskStorage()

    # Store a task
    task1 = TaskOutputDTO(
        id=1, uuid="12345678-1234-1234-1234-123456789012", description="Old task", status="pending"
    )
    storage.store_task("12345678-1234-1234-1234-123456789012", task1)

    # Refresh with new data
    task2 = TaskOutputDTO(
        id=1, uuid="12345678-1234-1234-1234-123456789012", description="New task", status="pending"
    )
    storage.refresh_task("12345678-1234-1234-1234-123456789012", task2)

    # Verify refresh
    retrieved_task = storage.get_task("12345678-1234-1234-1234-123456789012")
    assert retrieved_task.description == "New task"
