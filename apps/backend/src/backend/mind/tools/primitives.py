"""Mind-specific tool primitives (memory-focused for Phase 2 foundation)."""

from __future__ import annotations

import json
from typing import Any

from pi_agent_core import AgentTool, AgentToolResult, AgentToolSchema, TextContent

from ..memory import MemoryManager
from ..schema import MemoryEntry


def _text_result(value: str) -> AgentToolResult:
    return AgentToolResult(content=[TextContent(text=value)])


def create_memory_tools(memory_manager: MemoryManager, mind_id: str) -> list[AgentTool]:
    async def memory_save_execute(tool_call_id: str, params: dict[str, Any], **_: object) -> AgentToolResult:
        entry = MemoryEntry(
            mind_id=mind_id,
            content=params["content"],
            category=params.get("category"),
            relevance_keywords=params.get("relevance_keywords", []),
        )
        memory_manager.save(entry)
        return _text_result(f"Saved memory: {entry.id}")

    async def memory_search_execute(tool_call_id: str, params: dict[str, Any], **_: object) -> AgentToolResult:
        query = params["query"]
        top_k = int(params.get("top_k", 5))
        results = memory_manager.search(mind_id, query, top_k=top_k)
        payload = [item.model_dump(mode="json") for item in results]
        return _text_result(json.dumps(payload, indent=2))

    return [
        AgentTool(
            name="memory_save",
            description="Save a persistent memory for this Mind.",
            parameters=AgentToolSchema(
                properties={
                    "content": {"type": "string", "description": "Memory content to save."},
                    "category": {"type": "string", "description": "Optional category tag."},
                    "relevance_keywords": {
                        "type": "array",
                        "description": "Optional keywords used to improve retrieval.",
                        "items": {"type": "string"},
                    },
                },
                required=["content"],
            ),
            execute=memory_save_execute,
        ),
        AgentTool(
            name="memory_search",
            description="Search persistent memories for this Mind by query.",
            parameters=AgentToolSchema(
                properties={
                    "query": {"type": "string", "description": "Search query text."},
                    "top_k": {
                        "type": "integer",
                        "description": "Maximum number of results.",
                        "default": 5,
                    },
                },
                required=["query"],
            ),
            execute=memory_search_execute,
        ),
    ]
