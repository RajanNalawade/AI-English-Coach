"""Settings for hosting on a small free server: no login, hosted speech-to-text, serving the app."""

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import main
from app.config import settings
from app.stt import RemoteTranscriber, STTError, WhisperTranscriber, get_transcriber


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "test.db"))
    with TestClient(main.app) as c:
        yield c


def test_app_is_open_without_login(client, monkeypatch):
    # An old COACH_PASSWORD left in the host's settings no longer locks the app.
    monkeypatch.setenv("COACH_PASSWORD", "s3cret")
    res = client.get("/api/mistakes")
    assert res.status_code == 200
    assert "www-authenticate" not in res.headers

def test_remote_transcriber_posts_audio_to_the_api():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"text": " I goes to market. "})

    stt = RemoteTranscriber("https://api.groq.com/openai/v1/", "key", "whisper-large-v3-turbo", "en", 5, httpx.MockTransport(handler))
    assert stt.transcribe(b"audio-bytes") == "I goes to market."
    req = seen[0]
    assert str(req.url) == "https://api.groq.com/openai/v1/audio/transcriptions"
    assert req.headers["authorization"] == "Bearer key"
    body = req.content
    assert b"whisper-large-v3-turbo" in body and b"audio-bytes" in body


def test_remote_transcriber_errors_become_stt_errors():
    stt = RemoteTranscriber("https://x/v1", "k", "m", "en", 5, httpx.MockTransport(lambda r: httpx.Response(429)))
    with pytest.raises(STTError):
        stt.transcribe(b"a")


def test_get_transcriber_picks_the_provider(monkeypatch):
    get_transcriber.cache_clear()
    assert isinstance(get_transcriber(), WhisperTranscriber)
    get_transcriber.cache_clear()
    monkeypatch.setattr(settings, "stt_provider", "openai")
    monkeypatch.setattr(settings, "remote_url", "https://api.groq.com/openai/v1")
    assert isinstance(get_transcriber(), RemoteTranscriber)
    get_transcriber.cache_clear()


def test_serves_the_built_app_next_to_the_api(tmp_path):
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("<h1>coach</h1>")
    site = FastAPI()

    @site.get("/api/ping")
    def ping() -> dict:
        return {"ok": True}

    main.mount_web(site, str(web))
    c = TestClient(site)
    assert "coach" in c.get("/").text
    assert c.get("/api/ping").json() == {"ok": True}


def test_missing_static_dir_is_ignored():
    site = FastAPI()
    main.mount_web(site, "/does/not/exist")
    assert TestClient(site).get("/").status_code == 404
