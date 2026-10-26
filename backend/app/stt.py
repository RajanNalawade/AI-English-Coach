import io
from functools import lru_cache
from typing import Protocol

import httpx

from .config import settings


class STTError(Exception):
    pass


class Transcriber(Protocol):
    def transcribe(self, audio: bytes) -> str: ...


class WhisperTranscriber:
    """Local speech-to-text with faster-whisper on the CPU.

    The model (about 150 MB for "base") downloads on first use and is then cached.
    """

    def __init__(self, model: str, language: str) -> None:
        self.model_name = model
        self.language = language
        self._model = None

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
        return self._model

    def transcribe(self, audio: bytes) -> str:
        try:
            segments, _ = self._load().transcribe(io.BytesIO(audio), language=self.language, vad_filter=True)
            return " ".join(segment.text.strip() for segment in segments).strip()
        except Exception as exc:  # decoding and model errors surface as many types
            raise STTError(f"Could not transcribe the recording: {exc}") from exc


class RemoteTranscriber:
    """Speech-to-text through an OpenAI-compatible /audio/transcriptions API (e.g. Groq's Whisper)."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        language: str,
        timeout: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.url = f"{base_url.rstrip('/')}/audio/transcriptions"
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.data = {"model": model, "language": language, "response_format": "json"}
        self.timeout = timeout
        self.transport = transport

    def transcribe(self, audio: bytes) -> str:
        try:
            with httpx.Client(timeout=self.timeout, headers=self.headers, transport=self.transport) as client:
                response = client.post(self.url, data=self.data, files={"file": ("recording.webm", audio)})
                response.raise_for_status()
            return (response.json().get("text") or "").strip()
        except (httpx.HTTPError, ValueError) as exc:
            raise STTError(f"Could not transcribe the recording: {exc}") from exc


@lru_cache
def get_transcriber() -> Transcriber:
    if settings.stt_provider == "openai" and settings.remote_url:
        return RemoteTranscriber(
            settings.remote_url, settings.remote_api_key, settings.stt_remote_model, settings.stt_language, settings.remote_timeout
        )
    return WhisperTranscriber(settings.stt_model, settings.stt_language)
