"""Pydantic models defining the workflow DAG structure."""

from typing import Any

from pydantic import BaseModel, Field


class NodeParameter(BaseModel):
    """A single parameter for a workflow node."""

    name: str
    value: Any
    description: str
    required: bool = True


class WorkflowNode(BaseModel):
    """A single step in the workflow DAG."""

    id: str
    name: str
    description: str
    service: str  # "slack" | "jira" | "google" | "hr" | "github"
    action: str  # "create_channel" | "send_message" | etc.
    actor: str  # "hr_manager" | "it_admin" | "team_lead"
    parameters: list[NodeParameter] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    outputs: dict[str, str] = Field(default_factory=dict)


class WorkflowEdge(BaseModel):
    """An explicit edge between two workflow nodes."""

    source: str
    target: str


class Workflow(BaseModel):
    """A complete workflow DAG."""

    id: str
    name: str
    description: str
    team: str
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    version: int = 1
