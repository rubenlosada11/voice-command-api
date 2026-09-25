"""In-memory task storage. Data lives only while the process runs."""

from itertools import count
from typing import Any

tasks: list[dict[str, Any]] = []
_ids = count(1)


class TaskNotFoundError(Exception):
    def __init__(self, task_id: int) -> None:
        super().__init__(f"Task {task_id} not found")


def _find(task_id: int) -> dict[str, Any]:
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise TaskNotFoundError(task_id)


def list_tasks() -> list[dict[str, Any]]:
    return [dict(task) for task in tasks]


def create_task(title: str, done: bool = False) -> dict[str, Any]:
    task = {"id": next(_ids), "title": title, "done": done}
    tasks.append(task)
    return dict(task)


def replace_task(task_id: int, title: str, done: bool) -> dict[str, Any]:
    task = _find(task_id)
    task["title"] = title
    task["done"] = done
    return dict(task)


def update_task(
    task_id: int, title: str | None = None, done: bool | None = None
) -> dict[str, Any]:
    task = _find(task_id)
    if title is not None:
        task["title"] = title
    if done is not None:
        task["done"] = done
    return dict(task)


def delete_task(task_id: int) -> dict[str, str]:
    tasks.remove(_find(task_id))
    return {"message": f"Task {task_id} deleted"}
