import json
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .mind.events import EventStream
from .mind.memory import MemoryManager
from .mind.pipeline import delegate_to_mind
from .mind.schema import MemoryEntry, MindCharter, MindProfile, Task
from .mind.self_knowledge import build_default_self_knowledge
from .mind.store import MindStore
from .models import (
    DelegateTaskRequest,
    HealthResponse,
    MindCreateRequest,
    MindFeedbackRequest,
    MindUpdateRequest,
)

logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(
    title="Culture Engine API",
    description="Culture Engine API for Mind delegation, memory, and task traces",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; connect-src 'self'"
        )
        return response


app.add_middleware(SecurityHeadersMiddleware)

ROOT_DIR = Path(__file__).resolve().parents[3]

# Culture Engine storage (preferred)
CULTURE_DATA_DIR = ROOT_DIR / "culture"
# Backward-compatible fallback for existing local data
LEGACY_MIND_DATA_DIR = ROOT_DIR / "mind"
if not CULTURE_DATA_DIR.exists() and LEGACY_MIND_DATA_DIR.exists():
    CULTURE_DATA_DIR = LEGACY_MIND_DATA_DIR

_DB_PATH = CULTURE_DATA_DIR / "culture.db"
mind_store = MindStore(_DB_PATH)
memory_manager = MemoryManager(_DB_PATH)


def _preview(text: str, limit: int = 160) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit]}..."


def _build_profile_update_signal(
    before: MindProfile,
    after: MindProfile,
) -> MemoryEntry | None:
    changes: list[str] = []
    keywords = {"implicit_feedback", "profile_update", "preference_signal"}

    if before.name != after.name:
        changes.append(
            f"- User renamed the mind from '{before.name}' to '{after.name}'."
        )
        keywords.add("identity_update")

    if before.personality != after.personality:
        changes.append(
            "- User updated personality guidance to: "
            f"'{_preview(after.personality or 'not set')}'."
        )
        keywords.add("personality_update")

    if before.system_prompt != after.system_prompt:
        changes.append(
            "- User changed system prompt preference; new emphasis: "
            f"'{_preview(after.system_prompt or 'not set')}'."
        )
        keywords.add("system_prompt_update")

    if before.preferences != after.preferences:
        before_keys = set(before.preferences.keys())
        after_keys = set(after.preferences.keys())
        changed_keys = sorted(before_keys | after_keys)
        keys_text = ", ".join(changed_keys) if changed_keys else "none"
        changes.append(f"- User changed preference JSON keys: {keys_text}.")
        keywords.add("preferences_update")

    if before.charter.mission != after.charter.mission:
        changes.append(
            "- User changed charter mission toward: "
            f"'{_preview(after.charter.mission)}'."
        )
        keywords.add("charter_mission_update")

    if before.charter.reason_for_existence != after.charter.reason_for_existence:
        changes.append(
            "- User updated reason-for-existence framing to: "
            f"'{_preview(after.charter.reason_for_existence)}'."
        )
        keywords.add("charter_reason_update")

    if before.charter.operating_principles != after.charter.operating_principles:
        changes.append("- User revised operating principles.")
        keywords.add("charter_principles_update")

    if before.charter.non_goals != after.charter.non_goals:
        changes.append("- User revised non-goals and boundaries.")
        keywords.add("charter_non_goals_update")

    if before.charter.reflection_focus != after.charter.reflection_focus:
        changes.append("- User revised reflection focus priorities.")
        keywords.add("charter_reflection_update")

    if not changes:
        return None

    lines = [
        "Inferred implicit feedback from profile update:",
        f"Mind: {after.name} ({after.id})",
        *changes,
        "- Inference: treat these updates as stronger default user preferences until contradicted.",
    ]

    return MemoryEntry(
        mind_id=after.id,
        content="\n".join(lines),
        category="implicit_feedback",
        relevance_keywords=sorted(keywords),
    )


def _migrate_legacy_json(base_dir: Path) -> None:
    """One-time migration: import legacy JSON files into SQLite if they exist."""
    minds_dir = base_dir / "minds"
    tasks_dir = base_dir / "tasks"
    memory_dirs: list[Path] = []
    traces_dir = base_dir / "traces"

    # Look for a sibling "memory" dir (old MemoryManager layout)
    memory_root = base_dir / "memory"
    if memory_root.exists():
        memory_dirs = [d for d in memory_root.iterdir() if d.is_dir()]

    if not any(d.exists() for d in [minds_dir, tasks_dir, memory_root, traces_dir]):
        return  # nothing to migrate

    marker = base_dir / ".migrated_to_sqlite"
    if marker.exists():
        return  # already migrated

    logger.info("Migrating legacy JSON data to SQLite from %s", base_dir)
    count = 0
    failures = 0

    # Minds
    if minds_dir.exists():
        for fp in minds_dir.glob("*.json"):
            try:
                mind = MindProfile.model_validate(json.loads(fp.read_text()))
                mind_store.save_mind(mind)
                count += 1
            except Exception:
                failures += 1
                logger.warning("Skipping invalid mind file: %s", fp)

    # Tasks (per-mind subdirectories)
    if tasks_dir.exists():
        for mind_dir in tasks_dir.iterdir():
            if not mind_dir.is_dir():
                continue
            for fp in mind_dir.glob("*.json"):
                try:
                    task = Task.model_validate(json.loads(fp.read_text()))
                    mind_store.save_task(mind_dir.name, task)
                    count += 1
                except Exception:
                    failures += 1
                    logger.warning("Skipping invalid task file: %s", fp)

    # Memories (per-mind subdirectories)
    for mind_dir in memory_dirs:
        for fp in mind_dir.glob("*.json"):
            try:
                entry = MemoryEntry.model_validate(json.loads(fp.read_text()))
                memory_manager.save(entry)
                count += 1
            except Exception:
                failures += 1
                logger.warning("Skipping invalid memory file: %s", fp)

    # Task traces (per-mind subdirectories)
    if traces_dir.exists():
        for mind_dir in traces_dir.iterdir():
            if not mind_dir.is_dir():
                continue
            for fp in mind_dir.glob("*.json"):
                try:
                    data = json.loads(fp.read_text())
                    mind_store.save_task_trace(
                        data["mind_id"], data["task_id"], data.get("events", [])
                    )
                    count += 1
                except Exception:
                    failures += 1
                    logger.warning("Skipping invalid trace file: %s", fp)

    if failures > 0 and count == 0:
        logger.error(
            "Legacy migration failed: all %d files were invalid. "
            "Schema may be incompatible. Migration marker NOT written — "
            "will retry on next startup.",
            failures,
        )
        return

    marker.write_text("migrated")
    logger.info(
        "Legacy migration complete — imported %d records (%d skipped)", count, failures
    )


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Run one-time startup tasks before serving requests."""
    _migrate_legacy_json(CULTURE_DATA_DIR)
    if LEGACY_MIND_DATA_DIR.exists() and LEGACY_MIND_DATA_DIR != CULTURE_DATA_DIR:
        _migrate_legacy_json(LEGACY_MIND_DATA_DIR)
    yield


app.router.lifespan_context = _lifespan


@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")


# --- Culture Engine Mind endpoints ---


@app.post("/api/minds")
def create_mind(request: MindCreateRequest):
    mind = MindProfile(
        name=request.name,
        personality=request.personality,
        preferences=request.preferences,
        system_prompt=request.system_prompt,
        charter=request.charter,
    )
    mind_store.save_mind(mind)
    return mind.model_dump(mode="json")


@app.get("/api/minds")
def list_minds():
    return [mind.model_dump(mode="json") for mind in mind_store.list_minds()]


@app.get("/api/minds/{mind_id}")
def get_mind(mind_id: str):
    mind = mind_store.load_mind(mind_id)
    if mind is None:
        raise HTTPException(status_code=404, detail="Mind not found")
    return mind.model_dump(mode="json")


@app.get("/api/minds/{mind_id}/self")
def get_mind_self_knowledge(mind_id: str, team: str = "default"):
    mind = mind_store.load_mind(mind_id)
    if mind is None:
        raise HTTPException(status_code=404, detail="Mind not found")
    return build_default_self_knowledge(mind, team=team)


@app.patch("/api/minds/{mind_id}")
def update_mind(mind_id: str, request: MindUpdateRequest):
    mind = mind_store.load_mind(mind_id)
    if mind is None:
        raise HTTPException(status_code=404, detail="Mind not found")

    before = mind.model_copy(deep=True)

    if request.name is not None:
        mind.name = request.name

    if request.personality is not None:
        mind.personality = request.personality

    if request.preferences is not None:
        mind.preferences = request.preferences

    if request.system_prompt is not None:
        mind.system_prompt = request.system_prompt

    if request.charter is not None:
        charter_updates: dict[str, Any] = request.charter.model_dump(exclude_none=True)
        if charter_updates:
            charter_data = mind.charter.model_dump(mode="python")
            charter_data.update(charter_updates)
            mind.charter = MindCharter.model_validate(charter_data)

    mind_store.save_mind(mind)

    implicit_signal = _build_profile_update_signal(before, mind)
    if implicit_signal is not None:
        memory_manager.save(implicit_signal)

    return mind.model_dump(mode="json")


@app.post("/api/minds/{mind_id}/feedback")
def add_mind_feedback(mind_id: str, request: MindFeedbackRequest):
    mind = mind_store.load_mind(mind_id)
    if mind is None:
        raise HTTPException(status_code=404, detail="Mind not found")

    content = request.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Feedback content cannot be empty")

    related_task = None
    if request.task_id:
        related_task = mind_store.load_task(mind_id, request.task_id)
        if related_task is None:
            raise HTTPException(status_code=404, detail="Task not found")

    lines = [
        "User feedback for Mind behavior:",
        f"Mind: {mind.name} ({mind.id})",
    ]

    if request.task_id:
        lines.append(f"Task ID: {request.task_id}")
        if related_task is not None:
            lines.append(f"Task description: {related_task.description}")

    if request.rating is not None:
        lines.append(f"Rating: {request.rating}/5")

    lines.append(f"Feedback: {content}")

    keywords = ["feedback", "user_preference", "alignment"]
    if request.rating is not None and request.rating >= 4:
        keywords.append("positive_feedback")
    if request.rating is not None and request.rating <= 2:
        keywords.append("corrective_feedback")

    for tag in request.tags or []:
        cleaned = tag.strip().lower().replace(" ", "_")
        if cleaned:
            keywords.append(cleaned)

    memory = MemoryEntry(
        mind_id=mind_id,
        content="\n".join(lines),
        category="user_feedback",
        relevance_keywords=sorted(set(keywords)),
    )
    memory_manager.save(memory)
    return memory.model_dump(mode="json")


@app.post("/api/minds/{mind_id}/delegate")
async def delegate_task(mind_id: str, request: DelegateTaskRequest):
    async def event_stream():
        trace_id = uuid.uuid4().hex
        raw_stream = delegate_to_mind(
            mind_store=mind_store,
            memory_manager=memory_manager,
            mind_id=mind_id,
            description=request.description,
            team=request.team,
        )
        async for event in EventStream(raw_stream, trace_id=trace_id):
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/minds/{mind_id}/tasks")
def list_mind_tasks(mind_id: str):
    mind = mind_store.load_mind(mind_id)
    if mind is None:
        raise HTTPException(status_code=404, detail="Mind not found")
    return [task.model_dump(mode="json") for task in mind_store.list_tasks(mind_id)]


@app.get("/api/minds/{mind_id}/tasks/{task_id}")
def get_mind_task(mind_id: str, task_id: str):
    task = mind_store.load_task(mind_id, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.model_dump(mode="json")


@app.get("/api/minds/{mind_id}/tasks/{task_id}/drones")
def list_task_drones(mind_id: str, task_id: str):
    task = mind_store.load_task(mind_id, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return [
        drone.model_dump(mode="json")
        for drone in mind_store.list_drones(mind_id, task_id)
    ]


@app.get("/api/minds/{mind_id}/drones/{drone_id}/trace")
def get_drone_trace(mind_id: str, drone_id: str):
    trace = mind_store.load_drone_trace(mind_id, drone_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Drone trace not found")
    return trace


@app.get("/api/minds/{mind_id}/tasks/{task_id}/trace")
def get_mind_task_trace(mind_id: str, task_id: str):
    trace = mind_store.load_task_trace(mind_id, task_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Task trace not found")
    return trace


@app.get("/api/minds/{mind_id}/memory")
def list_mind_memory(mind_id: str, category: str | None = None):
    mind = mind_store.load_mind(mind_id)
    if mind is None:
        raise HTTPException(status_code=404, detail="Mind not found")
    return [
        m.model_dump(mode="json")
        for m in memory_manager.list_all(mind_id, category=category)
    ]
