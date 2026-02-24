"""First-class self-knowledge manifest for Mind runtime introspection."""

from __future__ import annotations

from .config import (
    DEFAULT_MIND_MAX_TURNS,
    DEFAULT_SPAWN_MAX_CALLS,
    DEFAULT_SPAWN_MAX_TURNS,
    MAX_AUTOSAVE_MEMORIES_PER_RUN,
    MAX_STREAM_EVENTS,
    MAX_TEXT_DELTA_EVENTS,
)
from .schema import MindProfile

PROGRAM_PARTS = [
    {"name": "agent_runner", "path": "backend/agents/base.py"},
    {"name": "tool_registry", "path": "backend/agents/tools.py"},
    {"name": "reasoning", "path": "backend/mind/reasoning.py"},
    {"name": "pipeline", "path": "backend/mind/pipeline.py"},
    {"name": "memory_store", "path": "backend/mind/memory.py"},
    {"name": "persistence_store", "path": "backend/mind/store.py"},
    {"name": "event_contract", "path": "backend/mind/events.py"},
]


def default_mind_tool_names(*, include_spawn_agent: bool = True) -> list[str]:
    tools = [
        "read_file",
        "write_file",
        "edit_file",
        "run_command",
        "search_apis",
        "search_knowledge_base",
        "memory_save",
        "memory_search",
    ]
    if include_spawn_agent:
        tools.append("spawn_agent")
    return sorted(tools)


def build_self_knowledge_manifest(
    *,
    mind: MindProfile,
    team: str,
    tool_names: list[str],
    max_turns: int,
    include_spawn_agent: bool,
    stream_event_limit: int | None,
    text_delta_event_limit: int | None,
    autosave_memory_limit: int | None,
) -> dict:
    return {
        "identity": {
            "mind_id": mind.id,
            "mind_name": mind.name,
        },
        "instruction_tape": {
            "mission": mind.charter.mission,
            "reason_for_existence": mind.charter.reason_for_existence,
            "preferences_keys": sorted(mind.preferences.keys()),
            "has_system_prompt": bool(mind.system_prompt.strip()),
        },
        "runtime": {
            "team": team,
            "tools": tool_names,
            "limits": {
                "max_turns": max_turns,
                "stream_event_limit": stream_event_limit,
                "text_delta_event_limit": text_delta_event_limit,
                "autosave_memories_per_run": autosave_memory_limit,
                "spawn_agent_max_calls": DEFAULT_SPAWN_MAX_CALLS
                if include_spawn_agent
                else 0,
                "spawn_agent_max_turns": DEFAULT_SPAWN_MAX_TURNS
                if include_spawn_agent
                else 0,
            },
            "architecture": "direct_anthropic_openrouter_loop",
        },
        "program_parts": PROGRAM_PARTS,
        "self_programming_paths": {
            "inspect": ["read_file", "run_command", "search_apis"],
            "modify": ["edit_file", "write_file"],
            "learn": ["memory_search", "memory_save"],
            "delegate": ["spawn_agent"] if include_spawn_agent else [],
        },
    }


def build_default_self_knowledge(mind: MindProfile, *, team: str = "default") -> dict:
    return build_self_knowledge_manifest(
        mind=mind,
        team=team,
        tool_names=default_mind_tool_names(include_spawn_agent=True),
        max_turns=DEFAULT_MIND_MAX_TURNS,
        include_spawn_agent=True,
        stream_event_limit=MAX_STREAM_EVENTS,
        text_delta_event_limit=MAX_TEXT_DELTA_EVENTS,
        autosave_memory_limit=MAX_AUTOSAVE_MEMORIES_PER_RUN,
    )
