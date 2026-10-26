import asyncio
import json

import httpx
import pytest

from app.config import settings
from app.llm import FallbackLLM, LLMError, OllamaLLM, OpenAICompatLLM, get_llm

SCHEMA = {"type": "object", "properties": {"corrected": {"type": "string"}}}


def run(coro):
    return asyncio.run(coro)


async def collect(stream) -> list[str]:
    return [text async for text in stream]


def completion(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_openai_compat_requests_json_schema_and_sends_key():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return completion('{"corrected": "Hi."}')

    llm = OpenAICompatLLM("https://api.example.com/v1/", "secret", "qwen", 5, httpx.MockTransport(handler))
    assert run(llm.complete_json("sys", [{"role": "user", "content": "hi"}], SCHEMA)) == {"corrected": "Hi."}
    body = json.loads(seen[0].content)
    assert str(seen[0].url) == "https://api.example.com/v1/chat/completions"
    assert seen[0].headers["authorization"] == "Bearer secret"
    assert body["model"] == "qwen"
    assert body["response_format"]["json_schema"]["schema"] == SCHEMA


def test_openai_compat_falls_back_to_json_mode_when_schema_is_unsupported():
    bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        bodies.append(body)
        if body["response_format"]["type"] == "json_schema":
            return httpx.Response(400, json={"error": "json_schema not supported"})
        return completion('{"corrected": "Hi."}')

    llm = OpenAICompatLLM("https://api.example.com/v1", "k", "m", 5, httpx.MockTransport(handler))
    assert run(llm.complete_json("sys", [], SCHEMA)) == {"corrected": "Hi."}
    assert bodies[1]["response_format"] == {"type": "json_object"}
    assert "JSON Schema" in bodies[1]["messages"][0]["content"]


def test_openai_compat_streams_sse_deltas():
    sse = (
        'data: {"choices":[{"delta":{"role":"assistant"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":" there"}}]}\n\n'
        "data: [DONE]\n\n"
    )
    llm = OpenAICompatLLM(
        "https://api.example.com/v1", "k", "m", 5, httpx.MockTransport(lambda r: httpx.Response(200, text=sse))
    )
    assert run(collect(llm.stream_text("sys", []))) == ["Hello", " there"]


def test_openai_compat_errors_become_llm_errors():
    llm = OpenAICompatLLM("https://api.example.com/v1", "k", "m", 5, httpx.MockTransport(lambda r: httpx.Response(401)))
    with pytest.raises(LLMError):
        run(llm.complete_json("sys", [], SCHEMA))
    with pytest.raises(LLMError):
        run(collect(llm.stream_text("sys", [])))


class Scripted:
    def __init__(self, tokens=(), answer=None, fail_after=None):
        self.tokens, self.answer, self.fail_after = list(tokens), answer, fail_after

    async def complete_json(self, system, messages, schema):
        if self.answer is None:
            raise LLMError("down")
        return self.answer

    async def stream_text(self, system, messages):
        for i, token in enumerate(self.tokens):
            if self.fail_after == i:
                raise LLMError("down")
            yield token
        if self.fail_after == len(self.tokens):
            raise LLMError("down")


def test_fallback_uses_local_model_when_hosted_one_fails():
    llm = FallbackLLM(Scripted(), Scripted(tokens=["local"], answer={"ok": 1}))
    assert run(llm.complete_json("s", [], SCHEMA)) == {"ok": 1}
    assert run(collect(FallbackLLM(Scripted(fail_after=0), Scripted(tokens=["local"])).stream_text("s", []))) == ["local"]


def test_fallback_does_not_switch_models_mid_reply():
    llm = FallbackLLM(Scripted(tokens=["Hel"], fail_after=1), Scripted(tokens=["local"]))
    with pytest.raises(LLMError):
        run(collect(llm.stream_text("s", [])))


def test_get_llm_defaults_to_ollama_and_switches_with_settings(monkeypatch):
    assert isinstance(get_llm(), OllamaLLM)
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "remote_url", "https://api.deepinfra.com/v1/openai")
    monkeypatch.setattr(settings, "remote_model", "Qwen/Qwen3.5-9B")
    llm = get_llm()
    assert isinstance(llm, FallbackLLM) and isinstance(llm.fallback, OllamaLLM)
    # Without a model name the hosted provider can't be used, so stay local.
    monkeypatch.setattr(settings, "remote_model", "")
    assert isinstance(get_llm(), OllamaLLM)


def test_get_llm_without_local_ollama_uses_only_the_hosted_model(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "remote_url", "https://api.groq.com/openai/v1")
    monkeypatch.setattr(settings, "remote_model", "openai/gpt-oss-20b")
    for no_local in ("", "none"):
        monkeypatch.setattr(settings, "ollama_url", no_local)
        assert isinstance(get_llm(), OpenAICompatLLM)


def test_openai_compat_sends_reasoning_effort_only_when_set():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return completion('{"corrected": "Hi."}')

    for effort in ("", "low"):
        llm = OpenAICompatLLM("https://api.example.com/v1", "k", "m", 5, httpx.MockTransport(handler), reasoning_effort=effort)
        run(llm.complete_json("sys", [{"role": "user", "content": "hi"}], SCHEMA))
    assert "reasoning_effort" not in seen[0]
    assert seen[1]["reasoning_effort"] == "low"
