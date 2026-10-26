import os
from dataclasses import dataclass, field


def _split(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass
class Settings:
    ollama_url: str = field(default_factory=lambda: os.getenv("OLLAMA_URL", "http://localhost:11434"))
    model: str = field(default_factory=lambda: os.getenv("COACH_MODEL", "qwen3:4b"))
    db_path: str = field(default_factory=lambda: os.getenv("COACH_DB", "coach.db"))
    # Seconds to wait for the model; CPU inference on a laptop can be slow.
    llm_timeout: float = field(default_factory=lambda: float(os.getenv("COACH_LLM_TIMEOUT", "180")))
    # How long Ollama keeps the model loaded after a request (Ollama duration, e.g. "30m", "-1" = forever).
    keep_alive: str = field(default_factory=lambda: os.getenv("COACH_KEEP_ALIVE", "30m"))
    # Optional hosted open model. "ollama" (default) runs everything locally; "openai" sends AI requests to any
    # OpenAI-compatible API (DeepInfra, Groq, OpenRouter...) and falls back to local Ollama if that fails.
    llm_provider: str = field(default_factory=lambda: os.getenv("COACH_LLM_PROVIDER", "ollama").strip().lower())
    remote_url: str = field(default_factory=lambda: os.getenv("COACH_REMOTE_URL", ""))
    remote_api_key: str = field(default_factory=lambda: os.getenv("COACH_REMOTE_API_KEY", ""))
    remote_model: str = field(default_factory=lambda: os.getenv("COACH_REMOTE_MODEL", ""))
    remote_timeout: float = field(default_factory=lambda: float(os.getenv("COACH_REMOTE_TIMEOUT", "60")))
    # For reasoning models such as gpt-oss ("low", "medium", "high"); empty sends nothing.
    remote_reasoning_effort: str = field(default_factory=lambda: os.getenv("COACH_REMOTE_REASONING_EFFORT", ""))
    # "local" runs faster-whisper on this machine; "openai" sends recordings to the hosted API above
    # (its /audio/transcriptions endpoint, e.g. Groq's free Whisper).
    stt_provider: str = field(default_factory=lambda: os.getenv("COACH_STT_PROVIDER", "local").strip().lower())
    stt_remote_model: str = field(default_factory=lambda: os.getenv("COACH_STT_REMOTE_MODEL", "whisper-large-v3-turbo"))
    # faster-whisper model: tiny, base, small... ("base" is a good speed/accuracy trade-off on CPU).
    stt_model: str = field(default_factory=lambda: os.getenv("COACH_STT_MODEL", "base"))
    stt_language: str = field(default_factory=lambda: os.getenv("COACH_STT_LANGUAGE", "en"))
    # When set, every request needs this login (for hosting the app publicly without a proxy in front).
    auth_user: str = field(default_factory=lambda: os.getenv("COACH_USER", "coach"))
    auth_password: str = field(default_factory=lambda: os.getenv("COACH_PASSWORD", ""))
    # Folder with the built PWA, served at / by the backend itself (single-service hosting).
    static_dir: str = field(default_factory=lambda: os.getenv("COACH_STATIC_DIR", ""))
    cors_origins: list[str] = field(
        default_factory=lambda: _split(os.getenv("COACH_CORS_ORIGINS", "http://localhost:5173"))
    )


settings = Settings()
