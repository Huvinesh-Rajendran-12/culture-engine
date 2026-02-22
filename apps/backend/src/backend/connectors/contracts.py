"""Shared connector contracts and execution trace models."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ServiceError(Exception):
    """Raised when a connector action cannot be completed."""

    def __init__(self, message: str, error_type: str = "connector_error"):
        self.error_type = error_type
        super().__init__(message)


class ServiceLayerState(BaseModel):
    """Execution-scoped state container for connector orchestration."""

    metadata: dict[str, str] = Field(default_factory=dict)


class TraceStep(BaseModel):
    """Single connector action trace record."""

    node_id: str
    service: str
    action: str
    parameters: dict
    result: dict | None = None
    status: str
    error: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionTrace(BaseModel):
    """Action trace for one service-layer execution."""

    steps: list[TraceStep] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
