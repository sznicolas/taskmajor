"""
Task Storage - Handles persistent storage of tasks
"""

from __future__ import annotations

from uuid import UUID

from taskwarrior import TaskOutputDTO

TaskID = str | UUID


class TaskStorage:
    """
    Manages storage of tasks with their IDs.
    """

    def __init__(self) -> None:
        self._storage: dict[str, TaskOutputDTO] = {}
        self._completed_tasks: dict[str, TaskOutputDTO] = {}
        self._deleted_tasks: dict[str, TaskOutputDTO] = {}

    def get_task(self, task_id: TaskID) -> TaskOutputDTO | None:
        """Get a task by its ID."""
        return self._storage.get(str(task_id))

    def store_task(self, task_id: TaskID, task: TaskOutputDTO) -> None:
        """Store a task by its ID."""
        self._storage[str(task_id)] = task

    def delete_task(self, task_id: TaskID) -> bool:
        """Delete a task by its ID."""
        key = str(task_id)
        if key in self._storage:
            # Move to deleted tasks
            task = self._storage[key]
            self._deleted_tasks[key] = task
            del self._storage[key]
            return True
        return False

    def refresh_task(self, task_id: TaskID, task: TaskOutputDTO) -> None:
        """Refresh a task by replacing its stored version."""
        self._storage[str(task_id)] = task

    def list_tasks(self) -> dict[str, TaskOutputDTO]:
        """List all stored tasks."""
        return self._storage.copy()

    def list_completed_tasks(self) -> list[TaskOutputDTO]:
        """List all completed tasks."""
        return list(self._completed_tasks.values())

    def list_deleted_tasks(self) -> list[TaskOutputDTO]:
        """List all deleted tasks."""
        return list(self._deleted_tasks.values())

    def mark_task_completed(self, task_id: TaskID) -> bool:
        """Mark a task as completed."""
        key = str(task_id)
        if key in self._storage:
            task = self._storage[key]
            self._completed_tasks[key] = task
            del self._storage[key]
            return True
        return False
