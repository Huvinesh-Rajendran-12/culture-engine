"""API models for Culture Engine."""

from typing import Any

from pydantic import BaseModel, Field

from .mind.schema import MindCharter


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str = "Culture Engine Backend"


class MindCreateRequest(BaseModel):
    """Create a new Mind identity."""

    name: str
    personality: str = ""
    preferences: dict[str, Any] = Field(default_factory=dict)
    system_prompt: str = ""
    charter: MindCharter = Field(default_factory=MindCharter)


class MindCharterPatchRequest(BaseModel):
    """Partial updates for a Mind charter."""

    mission: str | None = None
    reason_for_existence: str | None = None
    operating_principles: list[str] | None = None
    non_goals: list[str] | None = None
    reflection_focus: list[str] | None = None


class MindUpdateRequest(BaseModel):
    """Partial updates for a Mind profile."""

    name: str | None = None
    personality: str | None = None
    preferences: dict[str, Any] | None = None
    system_prompt: str | None = None
    charter: MindCharterPatchRequest | None = None


class MindFeedbackRequest(BaseModel):
    """User feedback payload for Mind learning."""

    content: str
    task_id: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    tags: list[str] = Field(default_factory=list)


class DelegateTaskRequest(BaseModel):
    """Delegate a task to a Mind."""

    description: str
    team: str = "default"
