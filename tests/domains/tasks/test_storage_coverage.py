"""Coverage tests for TaskStorage — completed/deleted task lists."""

from __future__ import annotations

from typing import Any, cast
import uuid

from taskwarrior import TaskOutputDTO

from taskmajor.domains.tasks import TaskStorage


def _task(description: str, *, task_uuid: str, status: str = "pending") -> TaskOutputDTO:
    payload: dict[str, Any] = {
        "id": 1,
        "uuid": uuid.UUID(task_uuid),
        "description": description,
        "status": status,
        "project": None,
        "priority": None,
        "tags": [],
        "udas": {},
    }
    return TaskOutputDTO(**cast(Any, payload))


class TestListCompletedTasks:
    def test_empty_when_nothing_completed(self):
        storage = TaskStorage()
        assert storage.list_completed_tasks() == []

    def test_mark_task_completed_moves_to_completed_list(self):
        storage = TaskStorage()
        task = _task("Buy milk", task_uuid="11111111-1111-1111-1111-111111111111")
        storage.store_task("11111111-1111-1111-1111-111111111111", task)
        storage.mark_task_completed("11111111-1111-1111-1111-111111111111")

        completed = storage.list_completed_tasks()
        assert len(completed) == 1
        assert completed[0].description == "Buy milk"

    def test_mark_task_completed_removes_from_active_storage(self):
        storage = TaskStorage()
        task = _task("Old task", task_uuid="22222222-2222-2222-2222-222222222222")
        storage.store_task("22222222-2222-2222-2222-222222222222", task)
        storage.mark_task_completed("22222222-2222-2222-2222-222222222222")

        assert storage.get_task("22222222-2222-2222-2222-222222222222") is None

    def test_mark_task_completed_missing_key_returns_false(self):
        storage = TaskStorage()
        result = storage.mark_task_completed("99999999-9999-9999-9999-999999999999")
        assert result is False

    def test_multiple_completions_listed(self):
        storage = TaskStorage()
        for i, desc in enumerate(["Task A", "Task B", "Task C"]):
            uid = f"{'a' * 8}-{'a' * 4}-{'a' * 4}-{'a' * 4}-{'a' * 11}{i}"
            storage.store_task(uid, _task(desc, task_uuid=uid))
            storage.mark_task_completed(uid)

        assert len(storage.list_completed_tasks()) == 3


class TestListDeletedTasks:
    def test_empty_when_nothing_deleted(self):
        storage = TaskStorage()
        assert storage.list_deleted_tasks() == []

    def test_delete_task_moves_to_deleted_list(self):
        storage = TaskStorage()
        task = _task("To delete", task_uuid="33333333-3333-3333-3333-333333333333")
        storage.store_task("33333333-3333-3333-3333-333333333333", task)
        storage.delete_task("33333333-3333-3333-3333-333333333333")

        deleted = storage.list_deleted_tasks()
        assert len(deleted) == 1
        assert deleted[0].description == "To delete"

    def test_delete_task_removes_from_active_storage(self):
        storage = TaskStorage()
        task = _task("Gone", task_uuid="44444444-4444-4444-4444-444444444444")
        storage.store_task("44444444-4444-4444-4444-444444444444", task)
        storage.delete_task("44444444-4444-4444-4444-444444444444")

        assert storage.get_task("44444444-4444-4444-4444-444444444444") is None
        assert len(storage.list_deleted_tasks()) == 1
