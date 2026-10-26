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


class OpenAICompatLLM:
    """Talks to a hosted model through an OpenAI-compatible chat completions API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
        reasoning_effort: str = "",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.reasoning_effort = reasoning_effort
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self.timeout, headers=self.headers, transport=self.transport)

    def _body(self, system: str, messages: list[dict[str, str]], stream: bool) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, *messages],
            "temperature": 0.3,
            "stream": stream,
        }
        if self.reasoning_effort:
            body["reasoning_effort"] = self.reasoning_effort
        return body

    async def complete_json(self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]:
        body = self._body(system, messages, stream=False)
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "answer", "schema": schema}}
        try:
            async with self._client() as client:
                response = await client.post(f"{self.base_url}/chat/completions", json=body)
                if response.status_code in (400, 422):
                    # Some providers only support plain JSON mode; describe the shape in the prompt instead.
                    body["response_format"] = {"type": "json_object"}
                    body["messages"][0] = {
                        "role": "system",
                        "content": f"{system}\nThe JSON must match this JSON Schema:\n{json.dumps(schema)}",
                    }
                    response = await client.post(f"{self.base_url}/chat/completions", json=body)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"The hosted model failed: {exc}") from exc
        try:
            content = response.json()["choices"][0]["message"]["content"] or ""
            return json.loads(content)
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise LLMError("The hosted model did not return valid JSON") from exc

    async def stream_text(self, system: str, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        body = self._body(system, messages, stream=True)
        try:
            async with self._client() as client:
                async with client.stream("POST", f"{self.base_url}/chat/completions", json=body) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        choices = json.loads(data).get("choices") or [{}]
                        text = (choices[0].get("delta") or {}).get("content") or ""
                        if text:
                            yield text
        except httpx.HTTPError as exc:
            raise LLMError(f"The hosted model failed: {exc}") from exc


class FallbackLLM:
    """Uses the hosted model first and the local one if it fails, so the coach keeps working."""

    def __init__(self, primary: LLM, fallback: LLM) -> None:
        self.primary = primary
        self.fallback = fallback

    async def complete_json(self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]:
        try:
            return await self.primary.complete_json(system, messages, schema)
        except LLMError:
            return await self.fallback.complete_json(system, messages, schema)

    async def stream_text(self, system: str, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        started = False
        try:
            async for text in self.primary.stream_text(system, messages):
                started = True
                yield text
            return
        except LLMError:
            # Once part of a reply has been shown, switching models mid-sentence would garble it.
            if started:
                raise
        async for text in self.fallback.stream_text(system, messages):
            yield text


def get_llm() -> LLM:
    local = OllamaLLM(settings.ollama_url, settings.model, settings.llm_timeout, settings.keep_alive)
    if settings.llm_provider == "openai" and settings.remote_url and settings.remote_model:
        remote = OpenAICompatLLM(
            settings.remote_url,
            settings.remote_api_key,
            settings.remote_model,
            settings.remote_timeout,
            reasoning_effort=settings.remote_reasoning_effort,
        )
        # OLLAMA_URL "none" (or empty) means there is no local model to fall back to, e.g. on a small free host.
        has_local = settings.ollama_url.strip().lower() not in ("", "none")
        return FallbackLLM(remote, local) if has_local else remote
    return local
