"""Main execution pipeline for Mind task delegation."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
import re

from .memory import MemoryManager
from .orchestrator import execute_task
from .schema import MemoryEntry, Task
from .store import MindStore

MAX_STREAM_EVENTS = 250
MAX_TEXT_DELTA_EVENTS = 4000
MAX_AUTOSAVE_MEMORIES_PER_RUN = 1
MAX_AUTOSAVE_INSIGHTS_PER_RUN = 1
MAX_MEMORY_CONTEXT_ITEMS = 16
MAX_FEEDBACK_CONTEXT_ITEMS = 4
MAX_IMPLICIT_CONTEXT_ITEMS = 4
MAX_INSIGHT_CONTEXT_ITEMS = 4
IMPLICIT_FOLLOWUP_WINDOW_SECONDS = 15 * 60
IMPLICIT_SIMILARITY_THRESHOLD = 0.3


def _merge_memory_context(
    groups: list[list[MemoryEntry]],
    *,
    limit: int,
) -> list[MemoryEntry]:
    merged: list[MemoryEntry] = []
    seen: set[str] = set()

    for group in groups:
        for entry in group:
            if entry.id in seen:
                continue
            seen.add(entry.id)
            merged.append(entry)
            if len(merged) >= limit:
                return merged

    return merged


def _event_type_counts(events: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        event_type = event.get("type")
        if isinstance(event_type, str):
            counts[event_type] = counts.get(event_type, 0) + 1
    return counts


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2}


def _text_similarity(left: str, right: str) -> float:
    left_tokens = _tokenize(left)
    right_tokens = _tokenize(right)

    if not left_tokens or not right_tokens:
        return 0.0

    overlap = left_tokens & right_tokens
    universe = left_tokens | right_tokens
    return len(overlap) / len(universe)


def _infer_implicit_feedback(
    *,
    mind_store: MindStore,
    mind_id: str,
    current_task: Task,
) -> MemoryEntry | None:
    recent_tasks = [
        task for task in mind_store.list_tasks(mind_id) if task.id != current_task.id
    ]
    if not recent_tasks:
        return None

    previous_task = recent_tasks[0]
    similarity = _text_similarity(current_task.description, previous_task.description)
    seconds_since_previous = (
        current_task.created_at - previous_task.created_at
    ).total_seconds()

    lines = [
        "Inferred implicit feedback from user behavior:",
        f"- Previous task: {previous_task.id} ({previous_task.status})",
        f"- Current task: {current_task.id}",
        f"- Similarity: {similarity:.2f}",
    ]

    keywords = {"implicit_feedback", "behavior_signal", "learning"}

    if previous_task.status == "failed":
        lines.append("- Signal: user retried after failure.")
        lines.append(
            "- Inference: prioritize resilience, faster checkpoints, and clearer completion signals."
        )
        keywords.update({"retry_after_failure", "reliability_expectation"})

        if similarity >= IMPLICIT_SIMILARITY_THRESHOLD:
            keywords.add("same_topic_retry")

        return MemoryEntry(
            mind_id=mind_id,
            content="\n".join(lines),
            category="implicit_feedback",
            relevance_keywords=sorted(keywords),
        )

    if (
        previous_task.status == "completed"
        and seconds_since_previous <= IMPLICIT_FOLLOWUP_WINDOW_SECONDS
        and similarity >= IMPLICIT_SIMILARITY_THRESHOLD
    ):
        lines.append("- Signal: user started a quick follow-up on a similar task.")
        lines.append(
            "- Inference: previous answer likely needed refinement; improve specificity and actionable structure."
        )
        keywords.update({"rapid_followup", "refinement_signal"})

        return MemoryEntry(
            mind_id=mind_id,
            content="\n".join(lines),
            category="implicit_feedback",
            relevance_keywords=sorted(keywords),
        )

    return None


def _save_if_new(memory_manager: MemoryManager, entry: MemoryEntry) -> bool:
    existing = memory_manager.list_all(entry.mind_id, category=entry.category)
    if existing and existing[-1].content == entry.content:
        return False

    memory_manager.save(entry)
    return True


def _compact_text(value: str | None, *, limit: int = 240) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = value.strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit]}..."


def _build_autonomous_insight(
    *,
    description: str,
    status: str,
    latest_text: str | None,
    failure_reason: str | None,
    feedback_context_count: int,
    implicit_context_count: int,
    event_counts: dict[str, int],
) -> tuple[str, list[str]]:
    tool_uses = event_counts.get("tool_use", 0)
    text_outputs = event_counts.get("text", 0)
    errors = event_counts.get("error", 0)

    keywords = ["insight", "learning", status]
    if failure_reason:
        keywords.append("failure")

    lines = [
        "Autonomous run insight:",
        f"- Task: {description}",
        f"- Status: {status}",
        f"- Signals: tool_use={tool_uses}, text={text_outputs}, errors={errors}",
    ]

    if failure_reason:
        lines.append(f"- Failure: {failure_reason}")

    result_preview = _compact_text(latest_text)
    if result_preview:
        lines.append(f"- Result preview: {result_preview}")

    if feedback_context_count > 0:
        lines.append(f"- Feedback memories considered: {feedback_context_count}")

    if implicit_context_count > 0:
        lines.append(f"- Implicit signals considered: {implicit_context_count}")

    return "\n".join(lines), sorted(set(keywords))


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
    text_delta_count = 0
    latest_text: str | None = None
    autosaved_memories = 0
    autosaved_insights = 0
    run_failure_reason: str | None = None
    feedback_memories: list[MemoryEntry] = []
    implicit_feedback_memories: list[MemoryEntry] = []

    def _save_autonomous_insight(
        *, status: str, failure_reason: str | None
    ) -> dict | None:
        nonlocal autosaved_insights

        if autosaved_insights >= MAX_AUTOSAVE_INSIGHTS_PER_RUN:
            return None

        insight_text, keywords = _build_autonomous_insight(
            description=description,
            status=status,
            latest_text=latest_text,
            failure_reason=failure_reason,
            feedback_context_count=len(feedback_memories),
            implicit_context_count=len(implicit_feedback_memories),
            event_counts=_event_type_counts(trace_events),
        )

        memory = MemoryEntry(
            mind_id=mind_id,
            content=insight_text,
            category="mind_insight",
            relevance_keywords=keywords,
        )
        memory_manager.save(memory)
        autosaved_insights += 1

        return {
            "type": "memory_saved",
            "content": {
                "id": memory.id,
                "mind_id": mind_id,
                "category": memory.category,
            },
        }

    start_event = {
        "type": "task_started",
        "content": {"task_id": task.id, "mind_id": mind_id},
    }
    _record(start_event)
    yield start_event

    inferred_implicit = _infer_implicit_feedback(
        mind_store=mind_store,
        mind_id=mind_id,
        current_task=task,
    )

    if inferred_implicit and _save_if_new(memory_manager, inferred_implicit):
        implicit_event = {
            "type": "implicit_feedback_inferred",
            "content": {
                "id": inferred_implicit.id,
                "mind_id": mind_id,
                "category": "implicit_feedback",
            },
        }
        _record(implicit_event)
        yield implicit_event

    searched_memories = memory_manager.search(mind_id, description, top_k=8)
    feedback_memories = memory_manager.list_all(mind_id, category="user_feedback")[
        -MAX_FEEDBACK_CONTEXT_ITEMS:
    ]
    implicit_feedback_memories = memory_manager.list_all(
        mind_id,
        category="implicit_feedback",
    )[-MAX_IMPLICIT_CONTEXT_ITEMS:]
    insight_memories = memory_manager.list_all(mind_id, category="mind_insight")[
        -MAX_INSIGHT_CONTEXT_ITEMS:
    ]
    memories = _merge_memory_context(
        [
            feedback_memories,
            implicit_feedback_memories,
            insight_memories,
            searched_memories,
        ],
        limit=MAX_MEMORY_CONTEXT_ITEMS,
    )

    memory_event = {
        "type": "memory_context",
        "content": {
            "count": len(memories),
            "memory_ids": [m.id for m in memories],
            "feedback_count": len(feedback_memories),
            "implicit_count": len(implicit_feedback_memories),
            "insight_count": len(insight_memories),
        },
    }
    _record(memory_event)
    yield memory_event

    try:
        async for event in execute_task(
            mind=mind,
            task=description,
            task_id=task.id,
            team=team,
            memories=memories,
            memory_manager=memory_manager,
            mind_store=mind_store,
            stream_event_limit=MAX_STREAM_EVENTS,
            text_delta_event_limit=MAX_TEXT_DELTA_EVENTS,
            autosave_memory_limit=MAX_AUTOSAVE_MEMORIES_PER_RUN,
        ):
            event_type = event.get("type")
            content = event.get("content")

            if event_type == "text_delta":
                text_delta_count += 1
                if text_delta_count > MAX_TEXT_DELTA_EVENTS:
                    raise RuntimeError(
                        f"Text delta limit reached ({MAX_TEXT_DELTA_EVENTS})"
                    )
            else:
                event_count += 1
                if event_count > MAX_STREAM_EVENTS:
                    raise RuntimeError(f"Event limit reached ({MAX_STREAM_EVENTS})")

            if event_type == "text" and isinstance(content, str):
                latest_text = content

            if event_type == "result" and isinstance(content, dict):
                final_text = content.get("final_text")
                if isinstance(final_text, str) and final_text.strip():
                    latest_text = final_text.strip()

                subtype = content.get("subtype")
                error_message = content.get("error_message")
                if isinstance(subtype, str) and subtype in {"error", "aborted"}:
                    if isinstance(error_message, str) and error_message.strip():
                        run_failure_reason = error_message.strip()
                    else:
                        run_failure_reason = f"Mind run ended with subtype={subtype}"

            _record(event)
            yield event

        if run_failure_reason:
            raise RuntimeError(run_failure_reason)

        task.status = "completed"
        task.result = latest_text
        task.completed_at = datetime.now(timezone.utc)
        mind_store.save_task(mind_id, task)

        if latest_text and autosaved_memories < MAX_AUTOSAVE_MEMORIES_PER_RUN:
            memory = MemoryEntry(
                mind_id=mind_id,
                content=f"Completed task: {description}\nResult: {latest_text}",
                category="task_result",
                relevance_keywords=["task", "result", "completion"],
            )
            memory_manager.save(memory)
            autosaved_memories += 1

            memory_saved_event = {
                "type": "memory_saved",
                "content": {
                    "id": memory.id,
                    "mind_id": mind_id,
                    "category": memory.category,
                },
            }
            _record(memory_saved_event)
            yield memory_saved_event

        insight_saved_event = _save_autonomous_insight(
            status=task.status,
            failure_reason=None,
        )
        if insight_saved_event is not None:
            _record(insight_saved_event)
            yield insight_saved_event

    except Exception as exc:
        task.status = "failed"
        task.result = str(exc)
        task.completed_at = datetime.now(timezone.utc)
        mind_store.save_task(mind_id, task)
        error_event = {"type": "error", "content": f"Mind execution failed: {exc}"}
        _record(error_event)
        yield error_event

        insight_saved_event = _save_autonomous_insight(
            status=task.status,
            failure_reason=str(exc),
        )
        if insight_saved_event is not None:
            _record(insight_saved_event)
            yield insight_saved_event
    finally:
        complete_event = {
            "type": "task_finished",
            "content": {"task_id": task.id, "status": task.status},
        }
        _record(complete_event)
        mind_store.save_task_trace(mind_id, task.id, trace_events)
        yield complete_event
