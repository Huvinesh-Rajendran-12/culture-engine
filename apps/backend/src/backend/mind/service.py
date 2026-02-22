"""Protocol-agnostic service layer for Mind operations.

All business logic lives here.  HTTP handlers (and future WebSocket / MCP /
CLI adapters) delegate to ``MindService`` and translate domain exceptions
into transport-specific error responses.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Any, Optional

from .events import Event, EventStream
from .exceptions import MindNotFoundError, TaskNotFoundError, ValidationError
from .memory import MemoryManager
from .pipeline import delegate_to_mind
from .schema import Drone, MemoryEntry, MindCharter, MindProfile, Task
from .store import MindStore


def _preview(text: str, limit: int = 160) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit]}..."


def _build_profile_update_signal(
    before: MindProfile,
    after: MindProfile,
) -> MemoryEntry | None:
    changes: list[str] = []
    keywords = {"implicit_feedback", "profile_update", "preference_signal"}

    if before.name != after.name:
        changes.append(
            f"- User renamed the mind from '{before.name}' to '{after.name}'."
        )
        keywords.add("identity_update")

    if before.personality != after.personality:
        changes.append(
            "- User updated personality guidance to: "
            f"'{_preview(after.personality or 'not set')}'."
        )
        keywords.add("personality_update")

    if before.system_prompt != after.system_prompt:
        changes.append(
            "- User changed system prompt preference; new emphasis: "
            f"'{_preview(after.system_prompt or 'not set')}'."
        )
        keywords.add("system_prompt_update")

    if before.preferences != after.preferences:
        before_keys = set(before.preferences.keys())
        after_keys = set(after.preferences.keys())
        changed_keys = sorted(before_keys | after_keys)
        keys_text = ", ".join(changed_keys) if changed_keys else "none"
        changes.append(f"- User changed preference JSON keys: {keys_text}.")
        keywords.add("preferences_update")

    if before.charter.mission != after.charter.mission:
        changes.append(
            "- User changed charter mission toward: "
            f"'{_preview(after.charter.mission)}'."
        )
        keywords.add("charter_mission_update")

    if before.charter.reason_for_existence != after.charter.reason_for_existence:
        changes.append(
            "- User updated reason-for-existence framing to: "
            f"'{_preview(after.charter.reason_for_existence)}'."
        )
        keywords.add("charter_reason_update")

    if before.charter.operating_principles != after.charter.operating_principles:
        changes.append("- User revised operating principles.")
        keywords.add("charter_principles_update")

    if before.charter.non_goals != after.charter.non_goals:
        changes.append("- User revised non-goals and boundaries.")
        keywords.add("charter_non_goals_update")

    if before.charter.reflection_focus != after.charter.reflection_focus:
        changes.append("- User revised reflection focus priorities.")
        keywords.add("charter_reflection_update")

    if not changes:
        return None

    lines = [
        "Inferred implicit feedback from profile update:",
        f"Mind: {after.name} ({after.id})",
        *changes,
        "- Inference: treat these updates as stronger default user preferences until contradicted.",
    ]

    return MemoryEntry(
        mind_id=after.id,
        content="\n".join(lines),
        category="implicit_feedback",
        relevance_keywords=sorted(keywords),
    )


class MindService:
    """Protocol-agnostic service for all Mind operations."""

    def __init__(self, store: MindStore, memory: MemoryManager) -> None:
        self.store = store
        self.memory = memory

    # ── Mind CRUD ──────────────────────────────────────────────────────────

    def create_mind(
        self,
        name: str,
        personality: str = "",
        preferences: dict[str, Any] | None = None,
        system_prompt: str = "",
        charter: MindCharter | None = None,
    ) -> MindProfile:
        mind = MindProfile(
            name=name,
            personality=personality,
            preferences=preferences or {},
            system_prompt=system_prompt,
            charter=charter or MindCharter(),
        )
        self.store.save_mind(mind)
        return mind

    def get_mind(self, mind_id: str) -> MindProfile:
        mind = self.store.load_mind(mind_id)
        if mind is None:
            raise MindNotFoundError(f"Mind '{mind_id}' not found")
        return mind

    def list_minds(self) -> list[MindProfile]:
        return self.store.list_minds()

    def update_mind(
        self,
        mind_id: str,
        *,
        name: Optional[str] = None,
        personality: Optional[str] = None,
        preferences: Optional[dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
        charter: Optional[Any] = None,
    ) -> MindProfile:
        mind = self.get_mind(mind_id)
        before = mind.model_copy(deep=True)

        if name is not None:
            mind.name = name

        if personality is not None:
            mind.personality = personality

        if preferences is not None:
            mind.preferences = preferences

        if system_prompt is not None:
            mind.system_prompt = system_prompt

        if charter is not None:
            charter_updates = (
                charter.model_dump(exclude_none=True)
                if hasattr(charter, "model_dump")
                else charter
            )
            charter_updates = {
                k: v
                for k, v in charter_updates.items()
                if not (isinstance(v, str) and v == "")
            }
            if charter_updates:
                charter_data = mind.charter.model_dump(mode="python")
                charter_data.update(charter_updates)
                mind.charter = MindCharter.model_validate(charter_data)

        self.store.save_mind(mind)

        implicit_signal = _build_profile_update_signal(before, mind)
        if implicit_signal is not None:
            self.memory.save(implicit_signal)

        return mind

    # ── Feedback ───────────────────────────────────────────────────────────

    def submit_feedback(
        self,
        mind_id: str,
        content: str,
        task_id: Optional[str] = None,
        rating: Optional[int] = None,
        tags: list[str] | None = None,
    ) -> MemoryEntry:
        mind = self.get_mind(mind_id)

        content = content.strip()
        if not content:
            raise ValidationError("Feedback content cannot be empty")

        related_task = None
        if task_id:
            related_task = self.store.load_task(mind_id, task_id)
            if related_task is None:
                raise TaskNotFoundError(f"Task '{task_id}' not found")

        lines = [
            "User feedback for Mind behavior:",
            f"Mind: {mind.name} ({mind.id})",
        ]

        if task_id:
            lines.append(f"Task ID: {task_id}")
            if related_task is not None:
                lines.append(f"Task description: {related_task.description}")

        if rating is not None:
            lines.append(f"Rating: {rating}/5")

        lines.append(f"Feedback: {content}")

        keywords = ["feedback", "user_preference", "alignment"]
        if rating is not None and rating >= 4:
            keywords.append("positive_feedback")
        if rating is not None and rating <= 2:
            keywords.append("corrective_feedback")

        for tag in tags or []:
            cleaned = tag.strip().lower().replace(" ", "_")
            if cleaned:
                keywords.append(cleaned)

        memory = MemoryEntry(
            mind_id=mind_id,
            content="\n".join(lines),
            category="user_feedback",
            relevance_keywords=sorted(set(keywords)),
        )
        self.memory.save(memory)
        return memory

    # ── Delegation ─────────────────────────────────────────────────────────

    async def delegate(
        self,
        mind_id: str,
        description: str,
        team: str = "default",
    ) -> AsyncGenerator[Event, None]:
        trace_id = uuid.uuid4().hex
        raw_stream = delegate_to_mind(
            mind_store=self.store,
            memory_manager=self.memory,
            mind_id=mind_id,
            description=description,
            team=team,
        )
        async for event in EventStream(raw_stream, trace_id=trace_id):
            yield event

    # ── Tasks ──────────────────────────────────────────────────────────────

    def list_tasks(self, mind_id: str) -> list[Task]:
        self.get_mind(mind_id)  # raises MindNotFoundError if missing
        return self.store.list_tasks(mind_id)

    def get_task(self, mind_id: str, task_id: str) -> Task:
        task = self.store.load_task(mind_id, task_id)
        if task is None:
            raise TaskNotFoundError(f"Task '{task_id}' not found")
        return task

    def get_task_trace(self, mind_id: str, task_id: str) -> dict:
        trace = self.store.load_task_trace(mind_id, task_id)
        if trace is None:
            raise TaskNotFoundError(f"Task trace for '{task_id}' not found")
        return trace

    # ── Drones ─────────────────────────────────────────────────────────────

    def list_drones(self, mind_id: str, task_id: str) -> list[Drone]:
        task = self.store.load_task(mind_id, task_id)
        if task is None:
            raise TaskNotFoundError(f"Task '{task_id}' not found")
        return self.store.list_drones(mind_id, task_id)

    def get_drone_trace(self, mind_id: str, drone_id: str) -> dict:
        trace = self.store.load_drone_trace(mind_id, drone_id)
        if trace is None:
            raise TaskNotFoundError(f"Drone trace for '{drone_id}' not found")
        return trace

    # ── Memory ─────────────────────────────────────────────────────────────

    def list_memory(
        self,
        mind_id: str,
        category: Optional[str] = None,
    ) -> list[MemoryEntry]:
        self.get_mind(mind_id)  # raises MindNotFoundError if missing
        return self.memory.list_all(mind_id, category=category)
