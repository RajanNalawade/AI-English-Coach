from contextlib import asynccontextmanager
from typing import TypeVar

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError

from . import db, prompts
from .config import settings
from .llm import LLM, LLMError, OllamaLLM, get_llm
from .schemas import (
    Change,
    ChatRequest,
    ChatResponse,
    GrammarRequest,
    GrammarResponse,
    MistakeSummary,
    RephraseRequest,
    RephraseResponse,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


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


@app.get("/api/mistakes", response_model=MistakeSummary)
def mistakes() -> dict:
    return db.summary()
