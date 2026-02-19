"""Identity helpers for creating and updating Mind profiles."""

from __future__ import annotations

from .schema import MindProfile


def create_mind_identity(
    *,
    name: str,
    personality: str = "",
    preferences: dict | None = None,
    system_prompt: str = "",
) -> MindProfile:
    return MindProfile(
        name=name,
        personality=personality,
        preferences=preferences or {},
        system_prompt=system_prompt,
    )
