"""Reasoning core for a Mind built on top of the shared pi-agent-core runner."""

from __future__ import annotations

from typing import Any

from .config import MAX_MEMORY_CONTEXT_ITEMS
from .schema import MemoryEntry, MindProfile


def build_system_prompt(
    mind: MindProfile,
    memories: list[MemoryEntry],
    runtime_manifest: dict[str, Any] | None = None,
) -> str:
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

    lines.append("Mind charter:")
    lines.append(f"- Mission: {mind.charter.mission}")
    lines.append(f"- Reason for existence: {mind.charter.reason_for_existence}")

    if mind.charter.operating_principles:
        lines.append("- Operating principles:")
        for principle in mind.charter.operating_principles:
            lines.append(f"  - {principle}")

    if mind.charter.non_goals:
        lines.append("- Non-goals:")
        for non_goal in mind.charter.non_goals:
            lines.append(f"  - {non_goal}")

    if mind.charter.reflection_focus:
        lines.append("- Reflection focus:")
        for focus_item in mind.charter.reflection_focus:
            lines.append(f"  - {focus_item}")

    if runtime_manifest:
        lines.append("Runtime capability manifest:")

        tools = runtime_manifest.get("tool_names")
        if isinstance(tools, list):
            lines.append(f"- Tools available in this run: {', '.join(tools)}")

        limits = runtime_manifest.get("limits")
        if isinstance(limits, dict) and limits:
            lines.append("- Runtime limits:")
            for key in sorted(limits):
                lines.append(f"  - {key}: {limits[key]}")

        architecture_notes = runtime_manifest.get("architecture_notes")
        if isinstance(architecture_notes, list) and architecture_notes:
            lines.append("- Architecture notes:")
            for note in architecture_notes:
                lines.append(f"  - {note}")

        team = runtime_manifest.get("team")
        if isinstance(team, str) and team.strip():
            lines.append(f"- Team context: {team.strip()}")

    if memories:
        lines.append("Relevant long-term memory:")
        for item in memories[:MAX_MEMORY_CONTEXT_ITEMS]:
            content = item.content if len(item.content) <= 400 else f"{item.content[:400]}..."
            lines.append(f"- ({item.category or 'general'}) {content}")

    if mind.system_prompt.strip():
        lines.append("Additional operating instructions:")
        lines.append(mind.system_prompt.strip())

    lines.extend(
        [
            "Meta conversation policy:",
            "- When asked why you exist or how you are built, answer from the charter and runtime manifest.",
            "- Distinguish current capabilities from recommended future capabilities.",
            "- Do not claim tools, permissions, or architecture that are not explicitly listed.",
            "- Treat memories in category 'user_feedback' as high-priority user preference signals.",
            "- Treat memories in category 'implicit_feedback' as inferred preference signals with medium confidence.",
            "- Treat memories in category 'mind_insight' as evolving heuristics: apply them, then refine when contradicted.",
            "- When user feedback changes your direction, explain the adaptation explicitly.",
        ]
    )

    return "\n".join(lines)
