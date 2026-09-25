import os
from itertools import count

import pytest

# Environment variables take precedence over .env, so tests never use the real key.
os.environ["GROQ_API_KEY"] = "test-key"

from fastapi.testclient import TestClient  # noqa: E402

from src.app.main import app  # noqa: E402
from src.app.services import instruction_resolver, speech_to_text, task_store  # noqa: E402
from tests.fakes import FakeGroq  # noqa: E402


@pytest.fixture(autouse=True)
def empty_task_store(monkeypatch: pytest.MonkeyPatch) -> None:
    task_store.tasks.clear()
    monkeypatch.setattr(task_store, "_ids", count(1))


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def fake_groq(monkeypatch: pytest.MonkeyPatch) -> FakeGroq:
    fake = FakeGroq()
    monkeypatch.setattr(instruction_resolver, "get_groq_client", lambda: fake)
    monkeypatch.setattr(speech_to_text, "get_groq_client", lambda: fake)
    return fake
