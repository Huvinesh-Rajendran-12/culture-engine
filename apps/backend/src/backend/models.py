"""API models for FlowForge."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class WorkflowRequest(BaseModel):
    """Request to generate a workflow."""

    description: str = Field(
        ..., description="Natural language description of the desired workflow"
    )
    context: Optional[dict[str, Any]] = Field(
        None,
        description="Additional context (e.g., employee name, department, systems)",
    )


class StreamMessage(BaseModel):
    """A single streamed message from the agent."""

    type: str = Field(..., description="Message type: text, tool_use, result, error")
    content: Any = Field(..., description="Message content")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str = "FlowForge Backend"
