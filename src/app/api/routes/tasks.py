from typing import Any

from fastapi import APIRouter, status

from src.app.schemas.voice import Task, TaskCreate, TaskReplace, TaskUpdate
from src.app.services import task_store

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[Task])
def get_tasks() -> list[dict[str, Any]]:
    return task_store.list_tasks()


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate) -> dict[str, Any]:
    return task_store.create_task(payload.title, payload.done)


@router.put("/{task_id}", response_model=Task)
def replace_task(task_id: int, payload: TaskReplace) -> dict[str, Any]:
    return task_store.replace_task(task_id, payload.title, payload.done)


@router.patch("/{task_id}", response_model=Task)
def update_task(task_id: int, payload: TaskUpdate) -> dict[str, Any]:
    return task_store.update_task(task_id, payload.title, payload.done)


@router.delete("/{task_id}")
def delete_task(task_id: int) -> dict[str, str]:
    return task_store.delete_task(task_id)
