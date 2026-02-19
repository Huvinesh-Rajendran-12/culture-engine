"""Runtime tool registry for Mind executions."""

from __future__ import annotations

from pi_agent_core import AgentTool


class ToolRegistry:
    """Minimal in-memory registry keyed by tool name."""

    def __init__(self):
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        self._tools[tool.name] = tool

    def register_many(self, tools: list[AgentTool]) -> None:
        for tool in tools:
            self.register(tool)

    def names(self) -> list[str]:
        return sorted(self._tools.keys())

    def tools(self) -> list[AgentTool]:
        return [self._tools[name] for name in self.names()]
