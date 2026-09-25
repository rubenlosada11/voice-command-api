import pytest

from src.app.services import task_store
from src.app.services.task_store import TaskNotFoundError


def test_starts_empty() -> None:
    assert task_store.list_tasks() == []


def test_create_assigns_incremental_ids() -> None:
    first = task_store.create_task("Comprar leche")
    second = task_store.create_task("Llamar a Ana", done=True)

    assert first == {"id": 1, "title": "Comprar leche", "done": False}
    assert second == {"id": 2, "title": "Llamar a Ana", "done": True}
    assert task_store.list_tasks() == [first, second]


def test_ids_are_not_reused_after_delete() -> None:
    task_store.create_task("A")
    task_store.create_task("B")
    task_store.delete_task(2)

    assert task_store.create_task("C")["id"] == 3


def test_replace_overwrites_title_and_done() -> None:
    task_store.create_task("Comprar leche")

    replaced = task_store.replace_task(1, "Comprar pan", True)

    assert replaced == {"id": 1, "title": "Comprar pan", "done": True}
    assert task_store.list_tasks() == [replaced]


def test_update_changes_only_given_fields() -> None:
    task_store.create_task("Comprar leche")

    assert task_store.update_task(1, done=True) == {
        "id": 1,
        "title": "Comprar leche",
        "done": True,
    }
    assert task_store.update_task(1, title="Comprar pan") == {
        "id": 1,
        "title": "Comprar pan",
        "done": True,
    }


def test_delete_removes_task_and_confirms() -> None:
    task_store.create_task("Comprar leche")

    assert task_store.delete_task(1) == {"message": "Task 1 deleted"}
    assert task_store.list_tasks() == []


@pytest.mark.parametrize(
    "operation",
    [
        lambda: task_store.replace_task(99, "X", False),
        lambda: task_store.update_task(99, done=True),
        lambda: task_store.delete_task(99),
    ],
)
def test_missing_id_raises(operation) -> None:
    with pytest.raises(TaskNotFoundError):
        operation()


def test_returned_dicts_do_not_mutate_store() -> None:
    created = task_store.create_task("Comprar leche")
    created["title"] = "Hackeado"
    task_store.list_tasks()[0]["done"] = True

    assert task_store.list_tasks() == [
        {"id": 1, "title": "Comprar leche", "done": False}
    ]
