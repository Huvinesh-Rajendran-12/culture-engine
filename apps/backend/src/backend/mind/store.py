"""SQLite-backed persistence primitives for Minds, tasks, and drone traces."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from .database import create_connection, init_db
from .schema import Drone, MindProfile, Task


@contextmanager
def connect(db_path: Path):
    conn = create_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


# ── Mind primitives ────────────────────────────────────────────────────────


def save_mind(db_path: Path, mind: MindProfile) -> str:
    with connect(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO minds
               (id, name, personality, preferences, system_prompt, charter, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                mind.id,
                mind.name,
                mind.personality,
                json.dumps(mind.preferences),
                mind.system_prompt,
                json.dumps(mind.charter.model_dump(mode="json")),
                mind.created_at.isoformat(),
            ),
        )
        conn.commit()
    return mind.id


def load_mind(db_path: Path, mind_id: str) -> Optional[MindProfile]:
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM minds WHERE id = ?", (mind_id,)).fetchone()
    if row is None:
        return None
    return _row_to_mind(row)


def list_minds(db_path: Path) -> list[MindProfile]:
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM minds ORDER BY created_at").fetchall()
    return [_row_to_mind(row) for row in rows]


def delete_mind(db_path: Path, mind_id: str) -> bool:
    with connect(db_path) as conn:
        conn.execute("DELETE FROM task_traces WHERE mind_id = ?", (mind_id,))
        conn.execute("DELETE FROM drone_traces WHERE mind_id = ?", (mind_id,))
        conn.execute("DELETE FROM drones WHERE mind_id = ?", (mind_id,))
        conn.execute("DELETE FROM tasks WHERE mind_id = ?", (mind_id,))
        conn.execute("DELETE FROM memories WHERE mind_id = ?", (mind_id,))
        cursor = conn.execute("DELETE FROM minds WHERE id = ?", (mind_id,))
        conn.commit()
    return cursor.rowcount > 0


# ── Task primitives ────────────────────────────────────────────────────────


def save_task(db_path: Path, mind_id: str, task: Task) -> str:
    with connect(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO tasks
               (id, mind_id, description, status, result, created_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                task.id,
                mind_id,
                task.description,
                task.status,
                task.result,
                task.created_at.isoformat(),
                task.completed_at.isoformat() if task.completed_at else None,
            ),
        )
        conn.commit()
    return task.id


def load_task(db_path: Path, mind_id: str, task_id: str) -> Optional[Task]:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ? AND mind_id = ?",
            (task_id, mind_id),
        ).fetchone()
    if row is None:
        return None
    return _row_to_task(row)


def list_tasks(db_path: Path, mind_id: str) -> list[Task]:
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE mind_id = ? ORDER BY created_at DESC",
            (mind_id,),
        ).fetchall()
    return [_row_to_task(row) for row in rows]


def save_task_trace(db_path: Path, mind_id: str, task_id: str, events: list[dict]) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO task_traces (mind_id, task_id, events)
               VALUES (?, ?, ?)""",
            (mind_id, task_id, json.dumps(events, default=str)),
        )
        conn.commit()


def load_task_trace(db_path: Path, mind_id: str, task_id: str) -> Optional[dict]:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM task_traces WHERE mind_id = ? AND task_id = ?",
            (mind_id, task_id),
        ).fetchone()
    if row is None:
        return None
    return {
        "mind_id": row["mind_id"],
        "task_id": row["task_id"],
        "events": json.loads(row["events"]),
    }


# ── Drone primitives ───────────────────────────────────────────────────────


def save_drone(db_path: Path, drone: Drone) -> str:
    with connect(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO drones
               (id, mind_id, task_id, objective, status, result, created_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                drone.id,
                drone.mind_id,
                drone.task_id,
                drone.objective,
                drone.status,
                drone.result,
                drone.created_at.isoformat(),
                drone.completed_at.isoformat() if drone.completed_at else None,
            ),
        )
        conn.commit()
    return drone.id


def list_drones(db_path: Path, mind_id: str, task_id: str) -> list[Drone]:
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM drones WHERE mind_id = ? AND task_id = ? ORDER BY created_at",
            (mind_id, task_id),
        ).fetchall()
    return [_row_to_drone(row) for row in rows]


def save_drone_trace(db_path: Path, mind_id: str, drone_id: str, events: list[dict]) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO drone_traces (mind_id, drone_id, events)
               VALUES (?, ?, ?)""",
            (mind_id, drone_id, json.dumps(events, default=str)),
        )
        conn.commit()


def load_drone_trace(db_path: Path, mind_id: str, drone_id: str) -> Optional[dict]:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM drone_traces WHERE mind_id = ? AND drone_id = ?",
            (mind_id, drone_id),
        ).fetchone()
    if row is None:
        return None
    return {
        "mind_id": row["mind_id"],
        "drone_id": row["drone_id"],
        "events": json.loads(row["events"]),
    }


def _row_to_mind(row: dict) -> MindProfile:
    return MindProfile(
        id=row["id"],
        name=row["name"],
        personality=row["personality"],
        preferences=json.loads(row["preferences"]),
        system_prompt=row["system_prompt"],
        charter=json.loads(row["charter"] or "{}"),
        created_at=row["created_at"],
    )


def _row_to_task(row: dict) -> Task:
    return Task(
        id=row["id"],
        mind_id=row["mind_id"],
        description=row["description"],
        status=row["status"],
        result=row["result"],
        created_at=row["created_at"],
        completed_at=row["completed_at"],
    )


def _row_to_drone(row: dict) -> Drone:
    return Drone(
        id=row["id"],
        mind_id=row["mind_id"],
        task_id=row["task_id"],
        objective=row["objective"],
        status=row["status"],
        result=row["result"],
        created_at=row["created_at"],
        completed_at=row["completed_at"],
    )
