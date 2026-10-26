from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import settings
from app.llm import LLMError, get_llm
from app.main import app
from app.stt import STTError, get_transcriber


class FakeLLM:
    def __init__(self, answer: dict[str, Any] | Exception) -> None:
        self.answer = answer
        self.calls: list[dict[str, Any]] = []

    async def complete_json(self, system, messages, schema):
        self.calls.append({"system": system, "messages": messages, "schema": schema})
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "test.db"), raising=False)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def use(answer) -> FakeLLM:
    fake = FakeLLM(answer)
    app.dependency_overrides[get_llm] = lambda: fake
    return fake


def test_grammar_returns_corrections_and_logs_them(client):
    use(
        {
            "corrected": "She goes to school every day.",
            "changes": [
                {"original": "go", "correction": "goes", "category": "agreement", "explanation": "Use 'goes' with she."},
                {"original": "every day", "correction": "every day", "category": "other", "explanation": "No change."},
            ],
        }
    )
    res = client.post("/api/grammar", json={"text": "She go to school every day."})
    assert res.status_code == 200
    body = res.json()
    assert body["corrected"] == "She goes to school every day."
    assert [c["correction"] for c in body["changes"]] == ["goes"]

    summary = client.get("/api/mistakes").json()
    assert summary["total"] == 1
    assert summary["top_categories"] == [{"category": "agreement", "count": 1}]


def test_rephrase_passes_styles_to_prompt(client):
    fake = use({"variants": [{"style": "formal", "text": "Could you assist me?", "note": "More polite."}]})
    res = client.post("/api/rephrase", json={"text": "help me", "styles": ["formal"]})
    assert res.status_code == 200
    assert res.json()["variants"][0]["style"] == "formal"
    assert "formal" in fake.calls[0]["system"]


def test_chat_sends_history_and_requires_user_last(client):
    fake = use({"reply": "Nice! What did you eat?", "corrections": []})
    history = [
        {"role": "assistant", "content": "How was your weekend?"},
        {"role": "user", "content": "It was great, I eated pizza"},
    ]
    res = client.post("/api/chat", json={"messages": history, "topic": "weekends"})
    assert res.status_code == 200
    assert fake.calls[0]["messages"] == history
    assert "weekends" in fake.calls[0]["system"]

    res = client.post("/api/chat", json={"messages": [{"role": "assistant", "content": "Hi"}]})
    assert res.status_code == 422


def test_bad_model_output_is_a_502(client):
    use({"corrected": "x"})
    assert client.post("/api/grammar", json={"text": "x"}).status_code == 502


def test_unreachable_model_is_a_502(client):
    use(LLMError("Could not reach the model"))
    res = client.post("/api/grammar", json={"text": "x"})
    assert res.status_code == 502
    assert "reach" in res.json()["detail"]


class FakeTranscriber:
    def __init__(self, text: str = "", error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.received: list[bytes] = []

    def transcribe(self, audio: bytes) -> str:
        self.received.append(audio)
        if self.error:
            raise self.error
        return self.text


def use_stt(fake: FakeTranscriber) -> FakeTranscriber:
    app.dependency_overrides[get_transcriber] = lambda: fake
    return fake


def test_transcribe_returns_text(client):
    fake = use_stt(FakeTranscriber("I eated pizza yesterday"))
    res = client.post("/api/transcribe", files={"audio": ("clip.webm", b"fake-audio", "audio/webm")})
    assert res.status_code == 200
    assert res.json() == {"text": "I eated pizza yesterday"}
    assert fake.received == [b"fake-audio"]


def test_transcribe_rejects_empty_and_oversized_audio(client, monkeypatch):
    use_stt(FakeTranscriber("x"))
    res = client.post("/api/transcribe", files={"audio": ("clip.webm", b"", "audio/webm")})
    assert res.status_code == 422

    monkeypatch.setattr(main, "MAX_AUDIO_BYTES", 4)
    res = client.post("/api/transcribe", files={"audio": ("clip.webm", b"12345", "audio/webm")})
    assert res.status_code == 413


def test_transcribe_failure_is_a_502(client):
    use_stt(FakeTranscriber(error=STTError("Could not transcribe the recording: bad audio")))
    res = client.post("/api/transcribe", files={"audio": ("clip.webm", b"junk", "audio/webm")})
    assert res.status_code == 502
