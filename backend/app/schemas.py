from typing import Literal

from pydantic import BaseModel, Field

Level = Literal["A2", "B1", "B2", "C1"]

Category = Literal[
    "grammar",
    "tense",
    "article",
    "preposition",
    "agreement",
    "word_choice",
    "word_order",
    "spelling",
    "punctuation",
    "other",
]

Style = Literal["simpler", "formal", "casual", "natural", "concise"]


class Change(BaseModel):
    original: str
    correction: str
    category: Category
    explanation: str


class GrammarRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    level: Level = "B1"


class GrammarResponse(BaseModel):
    corrected: str
    changes: list[Change]


class RephraseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    styles: list[Style] = Field(default_factory=lambda: ["simpler", "formal", "natural"], min_length=1, max_length=5)


class Variant(BaseModel):
    style: Style
    text: str
    note: str


class RephraseResponse(BaseModel):
    variants: list[Variant]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=50)
    topic: str = Field(default="everyday small talk", max_length=200)
    level: Level = "B1"


class ChatResponse(BaseModel):
    reply: str
    corrections: list[Change]


class CategoryCount(BaseModel):
    category: Category
    count: int


class MistakeEntry(BaseModel):
    created_at: str
    source: str
    original: str
    correction: str
    category: Category
    explanation: str


class MistakeSummary(BaseModel):
    total: int
    top_categories: list[CategoryCount]
    recent: list[MistakeEntry]


class TranscribeResponse(BaseModel):
    text: str
