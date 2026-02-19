"""Mind orchestrator: currently runs a single focused Mind execution."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from tempfile import TemporaryDirectory

from .memory import MemoryManager
from .reasoning import run_mind_reasoning
from .schema import MemoryEntry, MindProfile
from .tools import RuntimeToolStore, create_mind_tool_registry


async def execute_task(
    *,
    mind: MindProfile,
    task: str,
    team: str,
    memories: list[MemoryEntry],
    memory_manager: MemoryManager,
    runtime_tool_store: RuntimeToolStore,
) -> AsyncGenerator[dict, None]:
    """Execute one task with one Mind run.

    Note: automatic orchestration is intentionally minimal.
    Sub-agents are available only through the explicit spawn_agent tool.
    """
    with TemporaryDirectory(prefix="mind-") as workspace:
        runtime_specs = runtime_tool_store.list_tools(mind.id)

        async def _spawn_agent(objective: str, max_turns: int) -> str:
            allowed_tools = [name for name in registry.names() if name != "spawn_agent"]
            chunks: list[str] = []

            with TemporaryDirectory(prefix="drone-") as drone_workspace:
                async for event in run_mind_reasoning(
                    mind=mind,
                    task=f"[Drone Objective] {objective}",
                    workspace_dir=drone_workspace,
                    team=team,
                    memories=memories,
                    tool_registry=registry,
                    allowed_tools=allowed_tools,
                    max_turns=max(1, min(max_turns, 20)),
                ):
                    if event.get("type") == "text" and isinstance(event.get("content"), str):
                        chunks.append(event["content"])

            if chunks:
                return "\n".join(chunks[-3:])
            return "Sub-agent completed with no textual output."

        registry = create_mind_tool_registry(
            team=team,
            workspace_dir=workspace,
            memory_manager=memory_manager,
            mind_id=mind.id,
            runtime_specs=runtime_specs,
            spawn_agent_fn=_spawn_agent,
        )

        yield {
            "type": "tool_registry",
            "content": {
                "tools": registry.names(),
                "runtime_tool_count": len(runtime_specs),
            },
        }

        async for event in run_mind_reasoning(
            mind=mind,
            task=task,
            workspace_dir=workspace,
            team=team,
            memories=memories,
            tool_registry=registry,
        ):
            yield event
