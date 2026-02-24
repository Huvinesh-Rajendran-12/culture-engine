"""Main execution pipeline for Mind task delegation."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from ..agents.base import run_agent
from ..agents.tools import create_culture_engine_tools
from ..agents.types import AgentTool
from .config import (
    DEFAULT_MEMORY_SAVE_MAX_CALLS,
    DEFAULT_MIND_MAX_TURNS,
    DEFAULT_SPAWN_MAX_CALLS,
    DEFAULT_SPAWN_MAX_TURNS,
    MAX_AUTOSAVE_INSIGHTS_PER_RUN,
    MAX_AUTOSAVE_MEMORIES_PER_RUN,
    MAX_FEEDBACK_CONTEXT_ITEMS,
    MAX_IMPLICIT_CONTEXT_ITEMS,
    MAX_INSIGHT_CONTEXT_ITEMS,
    MAX_MEMORY_CONTEXT_ITEMS,
    MAX_STREAM_EVENTS,
    MAX_TEXT_DELTA_EVENTS,
)
from .reasoning import build_system_prompt
from .schema import Drone, MemoryEntry, MindProfile, Task
from .self_knowledge import build_self_knowledge_manifest
from .store import load_mind
from .tools.primitives import create_memory_tools, create_spawn_agent_tool


def create_mind_tools(
    *,
    team: str,
    workspace_dir: str,
    memory_manager: Any,
    mind_id: str,
    spawn_agent_fn: Callable[[str, int], Awaitable[str]],
    include_spawn_agent: bool = True,
) -> list[AgentTool]:
    tools = [
        *create_culture_engine_tools(team=team, workspace_dir=workspace_dir),
        *create_memory_tools(memory_manager=memory_manager, mind_id=mind_id),
    ]
    if include_spawn_agent:
        tools.append(create_spawn_agent_tool(spawn_agent_fn))
    return tools


def tool_names(tools: list[AgentTool]) -> list[str]:
    return sorted([tool.name for tool in tools])


def _merge_memory_context(
    groups: list[list[MemoryEntry]],
    *,
    limit: int,
) -> list[MemoryEntry]:
    if limit <= 0:
        return []

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


class _EphemeralMemory:
    """Per-run in-memory memory adapter (no persistence across runs)."""

    def __init__(self, mind_id: str):
        self._mind_id = mind_id
        self._entries: list[MemoryEntry] = []

    def save(self, entry: MemoryEntry) -> str:
        if entry.mind_id == self._mind_id:
            self._entries.append(entry)
        return entry.id

    def search(self, mind_id: str, query: str, top_k: int = 10) -> list[MemoryEntry]:
        if mind_id != self._mind_id:
            return []
        q = query.strip().lower()
        if not q:
            return []
        matches = [e for e in self._entries if q in e.content.lower()]
        return matches[-top_k:]

    def list_all(self, mind_id: str, category: str | None = None) -> list[MemoryEntry]:
        if mind_id != self._mind_id:
            return []
        if category is None:
            return list(self._entries)
        return [e for e in self._entries if e.category == category]


def _build_runtime_manifest(
    *,
    mind: MindProfile,
    team: str,
    tools: list[str],
    max_turns: int,
    include_spawn_agent: bool,
    stream_event_limit: int | None,
    text_delta_event_limit: int | None,
    autosave_memory_limit: int | None,
) -> dict[str, Any]:
    manifest = {
        "team": team,
        "tool_names": tools,
        "limits": {
            "max_turns": max_turns,
            "memory_save_max_calls": DEFAULT_MEMORY_SAVE_MAX_CALLS,
            "spawn_agent_max_calls": DEFAULT_SPAWN_MAX_CALLS
            if include_spawn_agent
            else 0,
            "spawn_agent_max_turns": DEFAULT_SPAWN_MAX_TURNS
            if include_spawn_agent
            else 0,
            "stream_event_limit": stream_event_limit,
            "text_delta_event_limit": text_delta_event_limit,
            "autosave_memories_per_run": autosave_memory_limit,
        },
        "architecture_notes": [
            "Single-path orchestration per delegation run.",
            "Sub-agents are explicit via spawn_agent; no implicit auto-splitting.",
            "This runtime is stateless across runs (no task/memory persistence in loop).",
            "For workspace discovery, use run_command with rg (content) and fd (file paths).",
            "Keep filesystem searches scoped and bounded before reading large files.",
        ],
    }
    manifest["self_knowledge"] = build_self_knowledge_manifest(
        mind=mind,
        team=team,
        tool_names=tools,
        max_turns=max_turns,
        include_spawn_agent=include_spawn_agent,
        stream_event_limit=stream_event_limit,
        text_delta_event_limit=text_delta_event_limit,
        autosave_memory_limit=autosave_memory_limit,
    )
    return manifest


async def delegate_to_mind(
    *,
    db_path: Path,
    mind_id: str,
    description: str,
    team: str = "default",
) -> AsyncGenerator[dict, None]:
    """Delegate a task to a Mind and stream execution events."""
    mind = load_mind(db_path, mind_id)
    if mind is None:
        yield {"type": "error", "content": f"Mind '{mind_id}' not found"}
        return

    task = Task(mind_id=mind_id, description=description, status="running")

    # Stateless runtime: use per-run in-memory memory only.
    runtime_memory = _EphemeralMemory(mind_id)

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
    emitted_terminal_result_error = False
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
        runtime_memory.save(memory)
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

    searched_memories = runtime_memory.search(mind_id, description, top_k=8)
    feedback_memories = runtime_memory.list_all(mind_id, category="user_feedback")[
        -MAX_FEEDBACK_CONTEXT_ITEMS:
    ]
    implicit_feedback_memories = runtime_memory.list_all(
        mind_id,
        category="implicit_feedback",
    )[-MAX_IMPLICIT_CONTEXT_ITEMS:]
    insight_memories = runtime_memory.list_all(mind_id, category="mind_insight")[
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
        with TemporaryDirectory(prefix="mind-") as workspace:

            async def _spawn_agent(objective: str, max_turns: int) -> str:
                drone = Drone(
                    mind_id=mind.id,
                    task_id=task.id,
                    objective=objective,
                    status="running",
                )

                chunks: list[str] = []
                drone_trace_events: list[dict] = []

                try:
                    with TemporaryDirectory(prefix="drone-") as drone_workspace:
                        drone_tools = create_mind_tools(
                            team=team,
                            workspace_dir=drone_workspace,
                            memory_manager=runtime_memory,
                            mind_id=mind.id,
                            spawn_agent_fn=_spawn_agent,
                            include_spawn_agent=False,
                        )
                        drone_tool_names = tool_names(drone_tools)
                        drone_manifest = _build_runtime_manifest(
                            mind=mind,
                            team=team,
                            tools=drone_tool_names,
                            max_turns=max_turns,
                            include_spawn_agent=False,
                            stream_event_limit=MAX_STREAM_EVENTS,
                            text_delta_event_limit=MAX_TEXT_DELTA_EVENTS,
                            autosave_memory_limit=MAX_AUTOSAVE_MEMORIES_PER_RUN,
                        )

                        async for event in run_agent(
                            prompt=f"[Drone Objective] {objective}",
                            system_prompt=build_system_prompt(
                                mind, memories, drone_manifest
                            ),
                            workspace_dir=drone_workspace,
                            team=team,
                            tools_override=drone_tools,
                            allowed_tools=drone_tool_names,
                            max_turns=max_turns,
                        ):
                            drone_trace_events.append(event)
                            if event.get("type") == "text" and isinstance(
                                event.get("content"), str
                            ):
                                chunks.append(event["content"])

                    result = (
                        "\n".join(chunks[-3:])
                        if chunks
                        else "Sub-agent completed with no textual output."
                    )
                    drone.status = "completed"
                    drone.result = result
                except Exception as exc:
                    result = f"Drone failed: {exc}"
                    drone.status = "failed"
                    drone.result = result
                finally:
                    drone.completed_at = datetime.now(timezone.utc)

                return result

            tools = create_mind_tools(
                team=team,
                workspace_dir=workspace,
                memory_manager=runtime_memory,
                mind_id=mind.id,
                spawn_agent_fn=_spawn_agent,
                include_spawn_agent=True,
            )
            tools_for_run = tool_names(tools)
            runtime_manifest = _build_runtime_manifest(
                mind=mind,
                team=team,
                tools=tools_for_run,
                max_turns=DEFAULT_MIND_MAX_TURNS,
                include_spawn_agent=True,
                stream_event_limit=MAX_STREAM_EVENTS,
                text_delta_event_limit=MAX_TEXT_DELTA_EVENTS,
                autosave_memory_limit=MAX_AUTOSAVE_MEMORIES_PER_RUN,
            )

            tool_registry_event = {
                "type": "tool_registry",
                "content": {
                    "tools": tools_for_run,
                },
            }
            event_count += 1
            if event_count > MAX_STREAM_EVENTS:
                raise RuntimeError(f"Event limit reached ({MAX_STREAM_EVENTS})")
            _record(tool_registry_event)
            yield tool_registry_event

            async for event in run_agent(
                prompt=description,
                system_prompt=build_system_prompt(mind, memories, runtime_manifest),
                workspace_dir=workspace,
                team=team,
                tools_override=tools,
                max_turns=DEFAULT_MIND_MAX_TURNS,
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
                        emitted_terminal_result_error = True
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

        if latest_text and autosaved_memories < MAX_AUTOSAVE_MEMORIES_PER_RUN:
            memory = MemoryEntry(
                mind_id=mind_id,
                content=f"Completed task: {description}\nResult: {latest_text}",
                category="task_result",
                relevance_keywords=["task", "result", "completion"],
            )
            runtime_memory.save(memory)
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
        should_emit_error_event = not (
            emitted_terminal_result_error and run_failure_reason == str(exc)
        )
        if should_emit_error_event:
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
        yield complete_event
