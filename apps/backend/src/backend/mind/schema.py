"""Schema definitions for the Culture Engine (Mind/Drone) architecture."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MemoryEntry(BaseModel):
    """A single piece of persistent knowledge stored by a Mind."""

    id: str = Field(default_factory=_new_id)
    mind_id: str
    content: str
    category: Optional[str] = None
    relevance_keywords: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)


class MindProfile(BaseModel):
    """Profile describing a Mind's identity and behavior."""

    id: str = Field(default_factory=_new_id)
    name: str
    personality: str = ""
    preferences: dict[str, Any] = Field(default_factory=dict)
    system_prompt: str = ""
    created_at: datetime = Field(default_factory=_now)


class Drone(BaseModel):
    """A focused sub-agent spawned by a Mind."""

    id: str = Field(default_factory=_new_id)
    mind_id: str
    objective: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    result: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    completed_at: Optional[datetime] = None


class Task(BaseModel):
    """A task assigned to or completed by a Mind."""

    id: str = Field(default_factory=_new_id)
    mind_id: str
    description: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    result: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    completed_at: Optional[datetime] = None
