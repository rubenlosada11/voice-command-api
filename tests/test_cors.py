from fastapi.testclient import TestClient


def preflight(client: TestClient, origin: str):
    return client.options(
        "/transcribe",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )


def test_preflight_allows_frontend_origin(client: TestClient) -> None:
    response = preflight(client, "http://localhost:5173")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-credentials" not in response.headers


def test_preflight_rejects_unknown_origin(client: TestClient) -> None:
    response = preflight(client, "http://evil.example")

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_simple_request_gets_cors_header(client: TestClient) -> None:
    response = client.get("/tasks", headers={"Origin": "http://127.0.0.1:5173"})

    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_healthcheck(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
