import io
from functools import lru_cache
from typing import Protocol

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


@lru_cache
def get_transcriber() -> Transcriber:
    return WhisperTranscriber(settings.stt_model, settings.stt_language)
