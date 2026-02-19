"""Main execution pipeline for Mind task delegation."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from .memory import MemoryManager
from .orchestrator import execute_task
from .schema import MemoryEntry, Task
from .store import MindStore

MAX_STREAM_EVENTS = 250
MAX_AUTOSAVE_MEMORIES_PER_RUN = 1


async def delegate_to_mind(
    *,
    mind_store: MindStore,
    memory_manager: MemoryManager,
    mind_id: str,
    description: str,
    team: str = "default",
) -> AsyncGenerator[dict, None]:
    """Delegate a task to a Mind and stream execution events."""
    mind = mind_store.load_mind(mind_id)
    if mind is None:
        yield {"type": "error", "content": f"Mind '{mind_id}' not found"}
        return

    task = Task(mind_id=mind_id, description=description, status="running")
    mind_store.save_task(mind_id, task)

    trace_events: list[dict] = []

    def _record(event: dict) -> None:
        trace_events.append(
            {
                "type": event.get("type"),
                "content": event.get("content"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    event_count = 0
    latest_text: str | None = None
    autosaved_memories = 0

    start_event = {"type": "task_started", "content": {"task_id": task.id, "mind_id": mind_id}}
    _record(start_event)
    yield start_event

    memories = memory_manager.search(mind_id, description, top_k=8)
    if memories:
        memory_event = {
            "type": "memory_context",
            "content": {"count": len(memories), "memory_ids": [m.id for m in memories]},
        }
        _record(memory_event)
        yield memory_event

    try:
        async for event in execute_task(
            mind=mind,
            task=description,
            team=team,
            memories=memories,
            memory_manager=memory_manager,
        ):
            event_count += 1
            if event_count > MAX_STREAM_EVENTS:
                raise RuntimeError(f"Event limit reached ({MAX_STREAM_EVENTS})")

            if event.get("type") == "text" and isinstance(event.get("content"), str):
                latest_text = event["content"]

            _record(event)
            yield event

        task.status = "completed"
        task.result = latest_text
        task.completed_at = datetime.now(timezone.utc)
        mind_store.save_task(mind_id, task)

        if latest_text and autosaved_memories < MAX_AUTOSAVE_MEMORIES_PER_RUN:
            memory_manager.save(
                MemoryEntry(
                    mind_id=mind_id,
                    content=f"Completed task: {description}\nResult: {latest_text}",
                    category="task_result",
                    relevance_keywords=["task", "result", "completion"],
                )
            )
            autosaved_memories += 1

    except Exception as exc:
        task.status = "failed"
        task.result = str(exc)
        task.completed_at = datetime.now(timezone.utc)
        mind_store.save_task(mind_id, task)
        error_event = {"type": "error", "content": f"Mind execution failed: {exc}"}
        _record(error_event)
        yield error_event
    finally:
        complete_event = {
            "type": "task_finished",
            "content": {"task_id": task.id, "status": task.status},
        }
        _record(complete_event)
        mind_store.save_task_trace(mind_id, task.id, trace_events)
        yield complete_event
