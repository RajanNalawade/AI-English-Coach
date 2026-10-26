import json
from collections.abc import AsyncIterator
from typing import Any, Protocol

import httpx

from .config import settings


class LLMError(Exception):
    pass


class LLM(Protocol):
    async def complete_json(self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]: ...

    def stream_text(self, system: str, messages: list[dict[str, str]]) -> AsyncIterator[str]: ...


class OllamaLLM:
    """Talks to a local Ollama server."""

    def __init__(self, base_url: str, model: str, timeout: float, keep_alive: str = "30m") -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.keep_alive = keep_alive

    def _body(self, system: str, messages: list[dict[str, str]], stream: bool) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, *messages],
            "stream": stream,
            "options": {"temperature": 0.3},
            # Keep the model in memory between requests; loading it again takes many seconds on CPU.
            "keep_alive": self.keep_alive,
        }
        # Qwen3 "thinks" before answering by default, which is slow on CPU and not needed here.
        if self.model.startswith("qwen3"):
            body["think"] = False
        return body

    async def complete_json(self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]:
        body = self._body(system, messages, stream=False)
        body["format"] = schema
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

    async def stream_text(self, system: str, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        body = self._body(system, messages, stream=True)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", f"{self.base_url}/api/chat", json=body) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        chunk = json.loads(line)
                        if chunk.get("error"):
                            raise LLMError(chunk["error"])
                        text = chunk.get("message", {}).get("content", "")
                        if text:
                            yield text
        except httpx.HTTPError as exc:
            raise LLMError(f"Could not reach the model at {self.base_url}: {exc}") from exc

    async def warm_up(self) -> None:
        """Loads the model into memory so the first real request is not slow."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                await client.post(
                    f"{self.base_url}/api/generate", json={"model": self.model, "keep_alive": self.keep_alive}
                )
        except httpx.HTTPError:
            pass  # Ollama may not be running yet; /api/health reports that.

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
    return OllamaLLM(settings.ollama_url, settings.model, settings.llm_timeout, settings.keep_alive)
