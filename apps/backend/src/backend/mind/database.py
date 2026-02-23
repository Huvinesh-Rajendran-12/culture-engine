"""SQLite database setup for Mind/Culture Engine persistence.

Replaces the previous file-based JSON + flock persistence with SQLite WAL mode,
providing cross-platform locking, atomic transactions, and FTS5 full-text search.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS minds (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    personality TEXT NOT NULL DEFAULT '',
    preferences TEXT NOT NULL DEFAULT '{}',
    system_prompt TEXT NOT NULL DEFAULT '',
    charter TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    mind_id TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    result TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_mind_id ON tasks(mind_id);
CREATE INDEX IF NOT EXISTS idx_tasks_mind_created ON tasks(mind_id, created_at DESC);

CREATE TABLE IF NOT EXISTS task_traces (
    mind_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    events TEXT NOT NULL,
    PRIMARY KEY (mind_id, task_id)
);

CREATE TABLE IF NOT EXISTS drones (
    id TEXT PRIMARY KEY,
    mind_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    objective TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    result TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_drones_task ON drones(mind_id, task_id);

CREATE TABLE IF NOT EXISTS drone_traces (
    mind_id TEXT NOT NULL,
    drone_id TEXT NOT NULL,
    events TEXT NOT NULL,
    PRIMARY KEY (mind_id, drone_id)
);

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    mind_id TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT,
    relevance_keywords TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memories_mind_id ON memories(mind_id);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content,
    relevance_keywords,
    content='memories',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS memories_fts_insert AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, content, relevance_keywords)
    VALUES (new.rowid, new.content, new.relevance_keywords);
END;

CREATE TRIGGER IF NOT EXISTS memories_fts_delete AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, relevance_keywords)
    VALUES ('delete', old.rowid, old.content, old.relevance_keywords);
END;

CREATE TRIGGER IF NOT EXISTS memories_fts_update AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, relevance_keywords)
    VALUES ('delete', old.rowid, old.content, old.relevance_keywords);
    INSERT INTO memories_fts(rowid, content, relevance_keywords)
    VALUES (new.rowid, new.content, new.relevance_keywords);
END;
"""


def create_connection(db_path: Path) -> sqlite3.Connection:
    """Create a configured SQLite connection (WAL, foreign keys, busy timeout)."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize a SQLite database with WAL mode and create schema.

    Safe to call multiple times — all schema objects use IF NOT EXISTS.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = create_connection(db_path)
    conn.executescript(_SCHEMA)
    _migrate_schema(conn)
    return conn


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Backfill additive schema changes for existing local databases."""

    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(minds)").fetchall()
    }

    if "charter" not in columns:
        conn.execute("ALTER TABLE minds ADD COLUMN charter TEXT NOT NULL DEFAULT '{}'")
        conn.commit()
