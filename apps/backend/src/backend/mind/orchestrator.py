"""Mind orchestrator: currently runs a single focused Mind execution."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from tempfile import TemporaryDirectory

from .reasoning import run_mind_reasoning
from .schema import MemoryEntry, MindProfile


async def execute_task(
    *,
    mind: MindProfile,
    task: str,
    team: str,
    memories: list[MemoryEntry],
) -> AsyncGenerator[dict, None]:
    """Execute one task with one Mind run.

    Note: Drone spawning is intentionally disabled for now to keep Phase 1 simple.
    It will be reintroduced through explicit tool-driven delegation in Phase 2.
    """
    with TemporaryDirectory(prefix="mind-") as workspace:
        async for event in run_mind_reasoning(
            mind=mind,
            task=task,
            workspace_dir=workspace,
            team=team,
            memories=memories,
        ):
            yield event
