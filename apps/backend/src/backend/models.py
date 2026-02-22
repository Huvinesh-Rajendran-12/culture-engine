"""API models for FlowForge."""

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str = "FlowForge Backend"


class MindCreateRequest(BaseModel):
    """Create a new Mind identity."""

    name: str
    personality: str = ""
    preferences: dict[str, Any] = Field(default_factory=dict)
    system_prompt: str = ""


class DelegateTaskRequest(BaseModel):
    """Delegate a task to a Mind."""

    description: str
    team: str = "default"
