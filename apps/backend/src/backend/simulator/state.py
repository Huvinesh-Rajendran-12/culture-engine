"""Shared execution state and trace models for the simulator."""

from datetime import datetime

from pydantic import BaseModel, Field


class SimulatorState(BaseModel):
    """Mutable state shared across all simulated services."""

    employees: dict[str, dict] = Field(default_factory=dict)
    google_accounts: dict[str, dict] = Field(default_factory=dict)
    slack_channels: dict[str, list[str]] = Field(default_factory=dict)
    slack_users: set[str] = Field(default_factory=set)
    github_members: dict[str, dict] = Field(default_factory=dict)
    jira_issues: dict[str, dict] = Field(default_factory=dict)


class TraceStep(BaseModel):
    """A single step recorded during workflow execution."""

    node_id: str
    service: str
    action: str
    parameters: dict
    result: dict | None = None
    status: str  # "success" | "failed" | "skipped"
    error: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ExecutionTrace(BaseModel):
    """Full trace of a workflow execution."""

    steps: list[TraceStep] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
