import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from .config import settings
from .schemas import Change

SCHEMA = """
CREATE TABLE IF NOT EXISTS mistakes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    source TEXT NOT NULL,
    original TEXT NOT NULL,
    correction TEXT NOT NULL,
    category TEXT NOT NULL,
    explanation TEXT NOT NULL
)
"""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.execute(SCHEMA)


def log_changes(source: str, changes: list[Change]) -> None:
    if not changes:
        return
    with connect() as conn:
        conn.executemany(
            "INSERT INTO mistakes (source, original, correction, category, explanation) VALUES (?, ?, ?, ?, ?)",
            [(source, c.original, c.correction, c.category, c.explanation) for c in changes],
        )


def summary(recent_limit: int = 20) -> dict:
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0]
        top = conn.execute(
            "SELECT category, COUNT(*) AS count FROM mistakes GROUP BY category ORDER BY count DESC, category LIMIT 5"
        ).fetchall()
        recent = conn.execute(
            "SELECT created_at, source, original, correction, category, explanation FROM mistakes ORDER BY id DESC LIMIT ?",
            (recent_limit,),
        ).fetchall()
    return {
        "total": total,
        "top_categories": [dict(row) for row in top],
        "recent": [dict(row) for row in recent],
    }
