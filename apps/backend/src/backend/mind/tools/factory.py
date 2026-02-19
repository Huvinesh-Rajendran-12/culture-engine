"""Factory for assembling the current Mind toolset."""

from __future__ import annotations

from ..memory import MemoryManager
from ...agents.tools import create_flowforge_tools
from .primitives import create_memory_tools
from .registry import ToolRegistry


def create_mind_tool_registry(
    *,
    team: str,
    workspace_dir: str,
    memory_manager: MemoryManager,
    mind_id: str,
) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register_many(create_flowforge_tools(team=team, workspace_dir=workspace_dir))
    registry.register_many(create_memory_tools(memory_manager=memory_manager, mind_id=mind_id))
    return registry
