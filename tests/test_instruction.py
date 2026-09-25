import json

import httpx
import pytest
from fastapi.testclient import TestClient
from groq import APIConnectionError

from src.app.services import task_store
from src.app.services.instruction_resolver import InvalidInstructionError, parse_instruction
from tests.fakes import FakeGroq


def test_returns_routing_without_executing(
    client: TestClient, fake_groq: FakeGroq
) -> None:
    fake_groq.llm_content = '{"endpoint": "/tasks", "method": "post", "params": {"title": "Comprar leche"}}'

    response = client.post("/instruction", json={"transcription": "añade comprar leche"})

    assert response.status_code == 200
    assert response.json() == {
        "endpoint": "/tasks",
        "method": "POST",
        "params": {"title": "Comprar leche"},
    }
    assert task_store.list_tasks() == []


def test_sends_current_tasks_and_command_to_model(
    client: TestClient, fake_groq: FakeGroq
) -> None:
    task_store.create_task("Comprar leche")
    fake_groq.llm_content = '{"endpoint": "/tasks/1", "method": "PATCH", "params": {"done": true}}'

    client.post("/instruction", json={"transcription": "marca comprar leche"})

    call = fake_groq.chat_calls[0]
    assert call["response_format"] == {"type": "json_object"}
    assert json.loads(call["messages"][1]["content"]) == {
        "current_tasks": [{"id": 1, "title": "Comprar leche", "done": False}],
        "command": "marca comprar leche",
    }


@pytest.mark.parametrize("body", [{}, {"transcription": ""}, {"transcription": "   "}])
def test_rejects_empty_transcription(
    client: TestClient, fake_groq: FakeGroq, body: dict
) -> None:
    assert client.post("/instruction", json=body).status_code == 422
    assert fake_groq.chat_calls == []


def test_invalid_model_output_returns_502(
    client: TestClient, fake_groq: FakeGroq
) -> None:
    fake_groq.llm_content = "Claro, aquí tienes: POST /tasks"

    response = client.post("/instruction", json={"transcription": "añade pan"})

    assert response.status_code == 502
    assert response.json() == {"detail": "The language model did not return valid JSON."}


def test_groq_failure_returns_502_without_secrets(
    client: TestClient, fake_groq: FakeGroq
) -> None:
    fake_groq.llm_error = APIConnectionError(request=httpx.Request("POST", "https://api.groq.com"))

    response = client.post("/instruction", json={"transcription": "añade pan"})

    assert response.status_code == 502
    assert response.json() == {"detail": "The language model request failed."}
    assert "test-key" not in response.text


@pytest.mark.parametrize(
    "raw",
    [
        '{"endpoint": "/tasks", "method": "GET", "params": {}}',
        '{"endpoint": "/tasks", "method": "POST", "params": {"title": "Pan"}}',
        '{"endpoint": "/tasks/3", "method": "PUT", "params": {"title": "Pan", "done": true}}',
        '{"endpoint": "/tasks/3", "method": "PATCH", "params": {"done": true}}',
        '{"endpoint": "/tasks/3", "method": "DELETE", "params": {}}',
    ],
)
def test_parse_accepts_valid_combinations(raw: str) -> None:
    assert parse_instruction(raw).model_dump() == json.loads(raw)


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "```json\n{}\n```",
        "[]",
        '{"endpoint": "/tasks", "method": "GET"}',
        '{"endpoint": "/tasks", "method": "GET", "params": {}, "reason": "x"}',
        '{"endpoint": "/tasks", "method": "HEAD", "params": {}}',
        '{"endpoint": "/tasks", "method": 1, "params": {}}',
        '{"endpoint": "/users", "method": "GET", "params": {}}',
        '{"endpoint": "/tasks/abc", "method": "PATCH", "params": {}}',
        '{"endpoint": "/tasks/1/extra", "method": "PATCH", "params": {}}',
        '{"endpoint": null, "method": "GET", "params": {}}',
        '{"endpoint": "/tasks/1", "method": "GET", "params": {}}',
        '{"endpoint": "/tasks/1", "method": "POST", "params": {"title": "x"}}',
        '{"endpoint": "/tasks", "method": "DELETE", "params": {}}',
        '{"endpoint": "/tasks", "method": "PATCH", "params": {"done": true}}',
        '{"endpoint": "/tasks", "method": "GET", "params": []}',
    ],
)
def test_parse_rejects_invalid_output(raw: str | None) -> None:
    with pytest.raises(InvalidInstructionError):
        parse_instruction(raw)
