"""Minimal local agent contracts used by the Mind runtime.

These types intentionally cover only what Culture Engine needs today.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TextContent:
    """Simple text content block used in tool results."""

    text: str = ""
    type: str = "text"


@dataclass
class AgentToolResult:
    """Tool execution result payload."""

    content: list[TextContent] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentToolSchema:
    """JSON-schema-like description of tool input parameters."""

    properties: dict[str, Any]
    required: list[str]
    type: str = "object"


ToolExecute = Callable[..., Awaitable[AgentToolResult]]


@dataclass
class AgentTool:
    """Executable tool specification exposed to the model."""

    name: str
    description: str
    parameters: AgentToolSchema
    execute: ToolExecute
