import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TypeVar

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError

from . import db, prompts
from .config import settings
from .llm import LLM, LLMError, OllamaLLM, get_llm
from .stt import STTError, Transcriber, get_transcriber
from .schemas import (
    Change,
    ChatRequest,
    ChatResponse,
    CorrectionsResponse,
    GrammarRequest,
    GrammarResponse,
    MistakeSummary,
    RephraseRequest,
    RephraseResponse,
    TranscribeResponse,
)

MAX_AUDIO_BYTES = 10 * 1024 * 1024


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    llm = get_llm()
    warm = asyncio.create_task(llm.warm_up()) if isinstance(llm, OllamaLLM) else None
    yield
    if warm:
        warm.cancel()


app = FastAPI(title="AI English Coach", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


T = TypeVar("T", bound=BaseModel)


async def ask(llm: LLM, model: type[T], system: str, messages: list[dict[str, str]]) -> T:
    try:
        raw = await llm.complete_json(system, messages, model.model_json_schema())
        return model.model_validate(raw)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=502, detail="The model's answer was not in the expected format") from exc


def real_changes(changes: list[Change]) -> list[Change]:
    # Small models sometimes list "changes" that change nothing.
    return [c for c in changes if c.original.strip() != c.correction.strip()]


@app.get("/api/health")
async def health(llm: LLM = Depends(get_llm)) -> dict:
    status = await llm.health() if isinstance(llm, OllamaLLM) else {"ollama": True}
    return {"ok": True, **status}


@app.post("/api/grammar", response_model=GrammarResponse)
async def grammar(req: GrammarRequest, llm: LLM = Depends(get_llm)) -> GrammarResponse:
    result = await ask(llm, GrammarResponse, prompts.grammar_system(req.level), [{"role": "user", "content": req.text}])
    result.changes = real_changes(result.changes)
    db.log_changes("grammar", result.changes)
    return result


@app.post("/api/rephrase", response_model=RephraseResponse)
async def rephrase(req: RephraseRequest, llm: LLM = Depends(get_llm)) -> RephraseResponse:
    return await ask(llm, RephraseResponse, prompts.rephrase_system(req.styles), [{"role": "user", "content": req.text}])


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, llm: LLM = Depends(get_llm)) -> ChatResponse:
    if req.messages[-1].role != "user":
        raise HTTPException(status_code=422, detail="The last message must be from the user")
    messages = [m.model_dump() for m in req.messages]
    result = await ask(llm, ChatResponse, prompts.chat_system(req.topic, req.level), messages)
    result.corrections = real_changes(result.corrections)
    db.log_changes("chat", result.corrections)
    return result


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest, llm: LLM = Depends(get_llm)) -> StreamingResponse:
    """Streams the reply as it is generated, then sends the corrections.

    The body is newline-delimited JSON: {"type": "token", "text": ...} lines, then one
    {"type": "corrections", "corrections": [...]} line, then {"type": "done"}.
    An {"type": "error", "detail": ...} line replaces the rest if something fails.
    """
    if req.messages[-1].role != "user":
        raise HTTPException(status_code=422, detail="The last message must be from the user")
    messages = [m.model_dump() for m in req.messages]
    # Only the latest exchange matters for corrections; a shorter prompt is faster on CPU.
    latest = messages[-2:] if len(messages) > 1 else messages

    async def events() -> AsyncIterator[str]:
        def line(obj: dict) -> str:
            return json.dumps(obj) + "\n"

        try:
            async for text in llm.stream_text(prompts.chat_reply_system(req.topic, req.level), messages):
                yield line({"type": "token", "text": text})
            result = await ask(llm, CorrectionsResponse, prompts.chat_corrections_system(req.level), latest)
        except LLMError as exc:
            yield line({"type": "error", "detail": str(exc)})
            return
        except HTTPException as exc:
            yield line({"type": "error", "detail": exc.detail})
            return
        corrections = real_changes(result.corrections)
        db.log_changes("chat", corrections)
        yield line({"type": "corrections", "corrections": [c.model_dump() for c in corrections]})
        yield line({"type": "done"})

    return StreamingResponse(events(), media_type="application/x-ndjson")


@app.get("/api/mistakes", response_model=MistakeSummary)
def mistakes() -> dict:
    return db.summary()


@app.post("/api/transcribe", response_model=TranscribeResponse)
def transcribe(audio: UploadFile = File(...), stt: Transcriber = Depends(get_transcriber)) -> TranscribeResponse:
    # A plain def runs in FastAPI's thread pool, so slow CPU transcription doesn't block other requests.
    data = audio.file.read(MAX_AUDIO_BYTES + 1)
    if not data:
        raise HTTPException(status_code=422, detail="The recording is empty")
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="The recording is too long; keep it under about a minute")
    try:
        return TranscribeResponse(text=stt.transcribe(data))
    except STTError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
