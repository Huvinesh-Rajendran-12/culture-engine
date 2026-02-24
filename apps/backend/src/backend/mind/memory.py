"""SQLite-backed memory persistence primitives for Mind long-term context."""

from __future__ import annotations

import json
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from .database import create_connection
from .schema import MemoryEntry


@contextmanager
def connect(db_path: Path):
    conn = create_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


# ── Memory primitives ──────────────────────────────────────────────────────


def save_memory(db_path: Path, entry: MemoryEntry) -> str:
    with connect(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO memories
               (id, mind_id, content, category, relevance_keywords, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                entry.id,
                entry.mind_id,
                entry.content,
                entry.category,
                json.dumps(entry.relevance_keywords),
                entry.created_at.isoformat(),
            ),
        )
        conn.commit()
    return entry.id


def retrieve_memory(db_path: Path, mind_id: str, memory_id: str) -> Optional[MemoryEntry]:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM memories WHERE id = ? AND mind_id = ?",
            (memory_id, mind_id),
        ).fetchone()
    if row is None:
        return None
    return _row_to_memory(row)


def search_memory(db_path: Path, mind_id: str, query: str, top_k: int = 10) -> list[MemoryEntry]:
    """Search memory using FTS5, with LIKE fallback for tokenizer edge cases."""
    query_text = query.strip()
    if not query_text:
        return []

    fts_query = _build_fts_query(query_text)

    with connect(db_path) as conn:
        rows = []
        if fts_query:
            rows = conn.execute(
                """SELECT m.* FROM memories m
                   JOIN memories_fts ON memories_fts.rowid = m.rowid
                   WHERE memories_fts MATCH ? AND m.mind_id = ?
                   ORDER BY memories_fts.rank
                   LIMIT ?""",
                (fts_query, mind_id, top_k),
            ).fetchall()

        if not rows:
            rows = conn.execute(
                """SELECT * FROM memories
                   WHERE mind_id = ? AND content LIKE ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (mind_id, f"%{query_text}%", top_k),
            ).fetchall()

    return [_row_to_memory(row) for row in rows]


def list_memories(
    db_path: Path,
    mind_id: str,
    category: Optional[str] = None,
) -> list[MemoryEntry]:
    with connect(db_path) as conn:
        if category is not None:
            rows = conn.execute(
                "SELECT * FROM memories WHERE mind_id = ? AND category = ? ORDER BY created_at",
                (mind_id, category),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM memories WHERE mind_id = ? ORDER BY created_at",
                (mind_id,),
            ).fetchall()
    return [_row_to_memory(row) for row in rows]


def delete_memory(db_path: Path, mind_id: str, memory_id: str) -> bool:
    with connect(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM memories WHERE id = ? AND mind_id = ?",
            (memory_id, mind_id),
        )
        conn.commit()
    return cursor.rowcount > 0


def _row_to_memory(row: dict) -> MemoryEntry:
    return MemoryEntry(
        id=row["id"],
        mind_id=row["mind_id"],
        content=row["content"],
        category=row["category"],
        relevance_keywords=json.loads(row["relevance_keywords"]),
        created_at=row["created_at"],
    )


def _build_fts_query(query: str) -> str:
    """Convert a natural-language query to an FTS5 OR query."""
    tokens = re.findall(r"[^\W_]+", query.lower(), flags=re.UNICODE)
    if not tokens:
        return ""
    return " OR ".join(tokens)
