import pytest
from fastapi.testclient import TestClient


def create(client: TestClient, title: str = "Comprar leche", **extra) -> dict:
    response = client.post("/tasks", json={"title": title, **extra})
    assert response.status_code == 201
    return response.json()


def test_get_tasks_starts_empty(client: TestClient) -> None:
    response = client.get("/tasks")

    assert response.status_code == 200
    assert response.json() == []


def test_post_creates_task_with_default_done(client: TestClient) -> None:
    assert create(client) == {"id": 1, "title": "Comprar leche", "done": False}
    assert create(client, "Llamar a Ana", done=True) == {
        "id": 2,
        "title": "Llamar a Ana",
        "done": True,
    }
    assert [task["id"] for task in client.get("/tasks").json()] == [1, 2]


def test_post_strips_title_whitespace(client: TestClient) -> None:
    assert create(client, "  Comprar leche  ")["title"] == "Comprar leche"


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"title": ""},
        {"title": "   "},
        {"title": 123},
        {"title": "Comprar leche", "done": "quizas"},
    ],
)
def test_post_rejects_invalid_body(client: TestClient, body: dict) -> None:
    assert client.post("/tasks", json=body).status_code == 422


def test_post_rejects_non_json_body(client: TestClient) -> None:
    response = client.post(
        "/tasks", content="no es json", headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422


def test_put_replaces_task(client: TestClient) -> None:
    create(client)

    response = client.put("/tasks/1", json={"title": "Comprar pan", "done": True})

    assert response.status_code == 200
    assert response.json() == {"id": 1, "title": "Comprar pan", "done": True}
    assert client.get("/tasks").json() == [response.json()]


def test_put_requires_all_fields(client: TestClient) -> None:
    create(client)

    assert client.put("/tasks/1", json={"title": "Comprar pan"}).status_code == 422


def test_patch_updates_only_given_fields(client: TestClient) -> None:
    create(client)

    response = client.patch("/tasks/1", json={"done": True})

    assert response.status_code == 200
    assert response.json() == {"id": 1, "title": "Comprar leche", "done": True}


def test_patch_rejects_empty_title(client: TestClient) -> None:
    create(client)

    assert client.patch("/tasks/1", json={"title": ""}).status_code == 422


def test_delete_removes_task(client: TestClient) -> None:
    create(client)

    response = client.delete("/tasks/1")

    assert response.status_code == 200
    assert response.json() == {"message": "Task 1 deleted"}
    assert client.get("/tasks").json() == []


def test_ids_not_reused_after_delete(client: TestClient) -> None:
    create(client, "A")
    create(client, "B")
    client.delete("/tasks/2")

    assert create(client, "C")["id"] == 3


@pytest.mark.parametrize(
    ("method", "body"),
    [
        ("PUT", {"title": "X", "done": False}),
        ("PATCH", {"done": True}),
        ("DELETE", None),
    ],
)
def test_missing_task_returns_404(client: TestClient, method: str, body) -> None:
    response = client.request(method, "/tasks/99", json=body)

    assert response.status_code == 404
    assert response.json() == {"detail": "Task 99 not found"}


def test_non_integer_id_returns_422(client: TestClient) -> None:
    assert client.patch("/tasks/abc", json={"done": True}).status_code == 422
