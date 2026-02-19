"""Mind orchestrator: currently runs a single focused Mind execution."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from tempfile import TemporaryDirectory

from .memory import MemoryManager
from .reasoning import run_mind_reasoning
from .schema import MemoryEntry, MindProfile
from .tools import create_mind_tool_registry


async def execute_task(
    *,
    mind: MindProfile,
    task: str,
    team: str,
    memories: list[MemoryEntry],
    memory_manager: MemoryManager,
) -> AsyncGenerator[dict, None]:
    """Execute one task with one Mind run.

    Note: Drone spawning is intentionally disabled for now to keep Phase 1 simple.
    It will be reintroduced through explicit tool-driven delegation in Phase 2.
    """
    with TemporaryDirectory(prefix="mind-") as workspace:
        registry = create_mind_tool_registry(
            team=team,
            workspace_dir=workspace,
            memory_manager=memory_manager,
            mind_id=mind.id,
        )
        yield {"type": "tool_registry", "content": {"tools": registry.names()}}

        async for event in run_mind_reasoning(
            mind=mind,
            task=task,
            workspace_dir=workspace,
            team=team,
            memories=memories,
            tool_registry=registry,
        ):
            yield event
