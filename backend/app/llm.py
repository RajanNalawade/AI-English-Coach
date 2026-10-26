import json
from typing import Any, Protocol

import httpx

from .config import settings


class LLMError(Exception):
    pass


class LLM(Protocol):
    async def complete_json(self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]: ...


class OllamaLLM:
    """Talks to a local Ollama server and asks for JSON matching a schema."""

    def __init__(self, base_url: str, model: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def complete_json(self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, *messages],
            "format": schema,
            "stream": False,
            "options": {"temperature": 0.3},
        }
        # Qwen3 "thinks" before answering by default, which is slow on CPU and not needed here.
        if self.model.startswith("qwen3"):
            body["think"] = False
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=body)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"Could not reach the model at {self.base_url}: {exc}") from exc
        content = response.json().get("message", {}).get("content", "")
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError("The model did not return valid JSON") from exc

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
        except httpx.HTTPError:
            return {"ollama": False, "model": self.model, "model_installed": False}
        names = {m.get("name", "") for m in response.json().get("models", [])}
        installed = self.model in names or f"{self.model}:latest" in names
        return {"ollama": True, "model": self.model, "model_installed": installed}


def get_llm() -> LLM:
    return OllamaLLM(settings.ollama_url, settings.model, settings.llm_timeout)
