"""Mind orchestrator: currently runs a single focused Mind execution."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from tempfile import TemporaryDirectory
from typing import Any

from ..agents.base import run_agent
from .memory import MemoryManager
from .reasoning import build_system_prompt
from .schema import Drone, MemoryEntry, MindProfile
from .store import MindStore
from .tools import create_mind_tools, tool_names
from .tools.primitives import (
    DEFAULT_MEMORY_SAVE_MAX_CALLS,
    DEFAULT_SPAWN_MAX_CALLS,
    DEFAULT_SPAWN_MAX_TURNS,
)

DEFAULT_MIND_MAX_TURNS = 40


def _build_runtime_manifest(
    *,
    team: str,
    tools: list[str],
    max_turns: int,
    include_spawn_agent: bool,
    stream_event_limit: int | None,
    text_delta_event_limit: int | None,
    autosave_memory_limit: int | None,
) -> dict[str, Any]:
    return {
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
            "Task traces and memories are persisted to SQLite for continuity.",
        ],
    }


async def execute_task(
    *,
    mind: MindProfile,
    task: str,
    task_id: str,
    team: str,
    memories: list[MemoryEntry],
    memory_manager: MemoryManager,
    mind_store: MindStore,
    stream_event_limit: int | None = None,
    text_delta_event_limit: int | None = None,
    autosave_memory_limit: int | None = None,
) -> AsyncGenerator[dict, None]:
    """Execute one task with one Mind run.

    Note: automatic orchestration is intentionally minimal.
    Sub-agents are available only through the explicit spawn_agent tool.
    """
    with TemporaryDirectory(prefix="mind-") as workspace:

        async def _spawn_agent(objective: str, max_turns: int) -> str:
            drone = Drone(
                mind_id=mind.id,
                task_id=task_id,
                objective=objective,
                status="running",
            )
            mind_store.save_drone(drone)

            chunks: list[str] = []
            trace_events: list[dict] = []

            try:
                with TemporaryDirectory(prefix="drone-") as drone_workspace:
                    drone_tools = create_mind_tools(
                        team=team,
                        workspace_dir=drone_workspace,
                        memory_manager=memory_manager,
                        mind_id=mind.id,
                        spawn_agent_fn=_spawn_agent,
                        include_spawn_agent=False,
                    )
                    drone_tool_names = tool_names(drone_tools)
                    drone_manifest = _build_runtime_manifest(
                        team=team,
                        tools=drone_tool_names,
                        max_turns=max_turns,
                        include_spawn_agent=False,
                        stream_event_limit=stream_event_limit,
                        text_delta_event_limit=text_delta_event_limit,
                        autosave_memory_limit=autosave_memory_limit,
                    )

                    async for event in run_agent(
                        prompt=f"[Drone Objective] {objective}",
                        system_prompt=build_system_prompt(mind, memories, drone_manifest),
                        workspace_dir=drone_workspace,
                        team=team,
                        tools_override=drone_tools,
                        allowed_tools=drone_tool_names,
                        max_turns=max_turns,
                    ):
                        trace_events.append(event)
                        if event.get("type") == "text" and isinstance(
                            event.get("content"), str
                        ):
                            chunks.append(event["content"])

                result = "\n".join(chunks[-3:]) if chunks else "Sub-agent completed with no textual output."
                drone.status = "completed"
                drone.result = result
            except Exception as exc:
                result = f"Drone failed: {exc}"
                drone.status = "failed"
                drone.result = result
            finally:
                drone.completed_at = datetime.now(timezone.utc)
                mind_store.save_drone(drone)
                mind_store.save_drone_trace(mind.id, drone.id, trace_events)

            return result

        tools = create_mind_tools(
            team=team,
            workspace_dir=workspace,
            memory_manager=memory_manager,
            mind_id=mind.id,
            spawn_agent_fn=_spawn_agent,
            include_spawn_agent=True,
        )
        tools_for_run = tool_names(tools)
        runtime_manifest = _build_runtime_manifest(
            team=team,
            tools=tools_for_run,
            max_turns=DEFAULT_MIND_MAX_TURNS,
            include_spawn_agent=True,
            stream_event_limit=stream_event_limit,
            text_delta_event_limit=text_delta_event_limit,
            autosave_memory_limit=autosave_memory_limit,
        )

        yield {
            "type": "tool_registry",
            "content": {
                "tools": tools_for_run,
            },
        }

        async for event in run_agent(
            prompt=task,
            system_prompt=build_system_prompt(mind, memories, runtime_manifest),
            workspace_dir=workspace,
            team=team,
            tools_override=tools,
            max_turns=DEFAULT_MIND_MAX_TURNS,
        ):
            yield event
