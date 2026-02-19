"""Reasoning core for a Mind built on top of the shared pi-agent-core runner."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from ..agents.base import run_agent
from .schema import MemoryEntry, MindProfile
from .tools.registry import ToolRegistry


def build_system_prompt(mind: MindProfile, memories: list[MemoryEntry]) -> str:
    """Build a dynamic system prompt from identity + relevant memory."""
    lines = [
        "You are a Culture Engine Mind: an autonomous digital operator.",
        "Operate safely, explain key decisions, and use tools when useful.",
        f"Mind name: {mind.name}",
    ]

    if mind.personality.strip():
        lines.append(f"Personality: {mind.personality.strip()}")

    if mind.preferences:
        lines.append(f"Preferences: {mind.preferences}")

    if memories:
        lines.append("Relevant long-term memory:")
        for item in memories[:10]:
            lines.append(f"- ({item.category or 'general'}) {item.content}")

    if mind.system_prompt.strip():
        lines.append("Additional operating instructions:")
        lines.append(mind.system_prompt.strip())

    return "\n".join(lines)


async def run_mind_reasoning(
    *,
    mind: MindProfile,
    task: str,
    workspace_dir: str,
    team: str,
    memories: list[MemoryEntry],
    tool_registry: ToolRegistry,
    allowed_tools: list[str] | None = None,
    max_turns: int = 40,
) -> AsyncGenerator[dict, None]:
    """Execute one Mind reasoning run and stream SSE-compatible events."""
    async for event in run_agent(
        prompt=task,
        system_prompt=build_system_prompt(mind, memories),
        workspace_dir=workspace_dir,
        team=team,
        allowed_tools=allowed_tools,
        tools_override=tool_registry.tools(),
        max_turns=max_turns,
    ):
        yield event
