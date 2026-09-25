import httpx
import pytest
from fastapi.testclient import TestClient
from groq import NOT_GIVEN, APIConnectionError

from src.app.services import task_store
from tests.fakes import FakeGroq

CREATE_MILK = '{"endpoint": "/tasks", "method": "POST", "params": {"title": "Comprar leche"}}'


def post_audio(client: TestClient, audio: bytes = b"fake-webm", filename: str = "command.webm", **form):
    return client.post("/transcribe", files={"file": (filename, audio, "audio/webm")}, data=form)


def test_audio_flow_transcribes_routes_and_executes(
    client: TestClient, fake_groq: FakeGroq
) -> None:
    fake_groq.transcript = "  Añade comprar leche a mi lista. "
    fake_groq.llm_content = CREATE_MILK

    response = post_audio(client, language="ES")

    assert response.status_code == 200
    assert response.json() == {
        "transcription": "Añade comprar leche a mi lista.",
        "instruction": {"endpoint": "/tasks", "method": "POST", "params": {"title": "Comprar leche"}},
        "result": {"id": 1, "title": "Comprar leche", "done": False},
    }
    assert task_store.list_tasks() == [{"id": 1, "title": "Comprar leche", "done": False}]

    audio_call = fake_groq.audio_calls[0]
    assert audio_call["file"] == ("command.webm", b"fake-webm")
    assert audio_call["language"] == "es"


def test_audio_without_language_lets_whisper_autodetect(
    client: TestClient, fake_groq: FakeGroq
) -> None:
    fake_groq.transcript = "what are my tasks"
    fake_groq.llm_content = '{"endpoint": "/tasks", "method": "GET", "params": {}}'

    assert post_audio(client).status_code == 200
    assert fake_groq.audio_calls[0]["language"] is NOT_GIVEN


def test_manual_json_flow_skips_whisper(client: TestClient, fake_groq: FakeGroq) -> None:
    task_store.create_task("Comprar leche")
    fake_groq.llm_content = '{"endpoint": "/tasks/1", "method": "PATCH", "params": {"done": true}}'

    response = client.post("/transcribe", json={"transcription": "marca comprar leche como completada"})

    assert response.status_code == 200
    assert response.json()["result"] == {"id": 1, "title": "Comprar leche", "done": True}
    assert task_store.list_tasks()[0]["done"] is True
    assert fake_groq.audio_calls == []


@pytest.mark.parametrize(
    ("llm_content", "expected_result"),
    [
        ('{"endpoint": "/tasks", "method": "GET", "params": {}}', [{"id": 1, "title": "Comprar leche", "done": False}]),
        ('{"endpoint": "/tasks/1", "method": "PUT", "params": {"title": "Comprar pan", "done": true}}', {"id": 1, "title": "Comprar pan", "done": True}),
        ('{"endpoint": "/tasks/1", "method": "DELETE", "params": {}}', {"message": "Task 1 deleted"}),
    ],
)
def test_manual_flow_result_matches_crud_endpoint(
    client: TestClient, fake_groq: FakeGroq, llm_content: str, expected_result
) -> None:
    task_store.create_task("Comprar leche")
    fake_groq.llm_content = llm_content

    response = client.post("/transcribe", json={"transcription": "algo"})

    assert response.status_code == 200
    assert response.json()["result"] == expected_result


def test_missing_task_returns_404(client: TestClient, fake_groq: FakeGroq) -> None:
    fake_groq.llm_content = '{"endpoint": "/tasks/0", "method": "DELETE", "params": {}}'

    response = client.post("/transcribe", json={"transcription": "elimina pasear al perro"})

    assert response.status_code == 404


def test_invalid_params_from_model_return_502(client: TestClient, fake_groq: FakeGroq) -> None:
    fake_groq.llm_content = '{"endpoint": "/tasks", "method": "POST", "params": {"title": "  "}}'

    response = client.post("/transcribe", json={"transcription": "añade"})

    assert response.status_code == 502
    assert task_store.list_tasks() == []


@pytest.mark.parametrize("body", ['{"transcription": ""}', '{"transcription": "   "}', "{}", "no json"])
def test_manual_flow_rejects_invalid_body(client: TestClient, fake_groq: FakeGroq, body: str) -> None:
    response = client.post("/transcribe", content=body, headers={"Content-Type": "application/json"})

    assert response.status_code == 422
    assert fake_groq.chat_calls == []


def test_unsupported_content_type_returns_415(client: TestClient, fake_groq: FakeGroq) -> None:
    response = client.post("/transcribe", content="hola", headers={"Content-Type": "text/plain"})

    assert response.status_code == 415


def test_missing_file_returns_400(client: TestClient, fake_groq: FakeGroq) -> None:
    response = client.post("/transcribe", data={"language": "es"}, files={"other": ("x.txt", b"x")})

    assert response.status_code == 400


def test_empty_audio_returns_400(client: TestClient, fake_groq: FakeGroq) -> None:
    assert post_audio(client, audio=b"").status_code == 400
    assert fake_groq.audio_calls == []


@pytest.mark.parametrize("filename", ["command.txt", "command"])
def test_unsupported_audio_format_returns_415(
    client: TestClient, fake_groq: FakeGroq, filename: str
) -> None:
    assert post_audio(client, filename=filename).status_code == 415
    assert fake_groq.audio_calls == []


def test_invalid_language_returns_400(client: TestClient, fake_groq: FakeGroq) -> None:
    assert post_audio(client, language="español").status_code == 400
    assert fake_groq.audio_calls == []


def test_empty_transcription_returns_422(client: TestClient, fake_groq: FakeGroq) -> None:
    fake_groq.transcript = "   "

    response = post_audio(client)

    assert response.status_code == 422
    assert response.json() == {"detail": "No speech was detected in the audio."}
    assert fake_groq.chat_calls == []


def test_whisper_failure_returns_502(client: TestClient, fake_groq: FakeGroq) -> None:
    fake_groq.stt_error = APIConnectionError(request=httpx.Request("POST", "https://api.groq.com"))

    response = post_audio(client)

    assert response.status_code == 502
    assert response.json() == {"detail": "The transcription request failed."}
    assert "test-key" not in response.text
