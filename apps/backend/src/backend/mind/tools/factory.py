"""Factory for assembling the current Mind toolset."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from ..memory import MemoryManager
from ...agents.tools import create_flowforge_tools
from .primitives import create_memory_tools, create_runtime_tools, create_spawn_agent_tool
from .registry import ToolRegistry
from .runtime_store import RuntimeToolSpec


def create_mind_tool_registry(
    *,
    team: str,
    workspace_dir: str,
    memory_manager: MemoryManager,
    mind_id: str,
    runtime_specs: list[RuntimeToolSpec],
    spawn_agent_fn: Callable[[str, int], Awaitable[str]],
) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register_many(create_flowforge_tools(team=team, workspace_dir=workspace_dir))
    registry.register_many(create_memory_tools(memory_manager=memory_manager, mind_id=mind_id))
    registry.register_many(create_runtime_tools(runtime_specs))
    registry.register(create_spawn_agent_tool(spawn_agent_fn))
    return registry
