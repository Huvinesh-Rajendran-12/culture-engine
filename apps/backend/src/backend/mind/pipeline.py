"""Main execution pipeline for Mind task delegation."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from .memory import MemoryManager
from .orchestrator import execute_task
from .schema import MemoryEntry, Task
from .store import MindStore
from .tools import RuntimeToolStore


async def delegate_to_mind(
    *,
    mind_store: MindStore,
    memory_manager: MemoryManager,
    runtime_tool_store: RuntimeToolStore,
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

    memories = memory_manager.search(mind_id, description, top_k=8)
    if memories:
        yield {
            "type": "memory_context",
            "content": {"count": len(memories), "memory_ids": [m.id for m in memories]},
        }

    latest_text: str | None = None

    try:
        async for event in execute_task(
            mind=mind,
            task=description,
            team=team,
            memories=memories,
            memory_manager=memory_manager,
            runtime_tool_store=runtime_tool_store,
        ):
            if event.get("type") == "text" and isinstance(event.get("content"), str):
                latest_text = event["content"]
            yield event

        task.status = "completed"
        task.result = latest_text
        task.completed_at = datetime.now(timezone.utc)
        mind_store.save_task(mind_id, task)

        if latest_text:
            memory_manager.save(
                MemoryEntry(
                    mind_id=mind_id,
                    content=f"Completed task: {description}\nResult: {latest_text}",
                    category="task_result",
                    relevance_keywords=["task", "result", "completion"],
                )
            )

    except Exception as exc:
        task.status = "failed"
        task.result = str(exc)
        task.completed_at = datetime.now(timezone.utc)
        mind_store.save_task(mind_id, task)
        yield {"type": "error", "content": f"Mind execution failed: {exc}"}
