"""Persistent store for runtime-registered Mind tools."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel


TOOL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

RESERVED_TOOL_NAMES = {
    "read_file",
    "write_file",
    "edit_file",
    "run_command",
    "search_apis",
    "search_knowledge_base",
    "memory_save",
    "memory_search",
    "spawn_agent",
}


class RuntimeToolSpec(BaseModel):
    """Minimal runtime tool definition persisted per Mind."""

    name: str
    description: str
    response: str


class RuntimeToolStore:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _mind_dir(self, mind_id: str, *, create: bool = False) -> Path:
        d = self.base_dir / mind_id
        if create:
            d.mkdir(parents=True, exist_ok=True)
        return d

    def list_tools(self, mind_id: str) -> list[RuntimeToolSpec]:
        mind_dir = self._mind_dir(mind_id)
        if not mind_dir.exists():
            return []

        tools: list[RuntimeToolSpec] = []
        for filepath in sorted(mind_dir.glob("*.json")):
            data = json.loads(filepath.read_text())
            tools.append(RuntimeToolSpec.model_validate(data))
        return tools

    def save_tool(self, mind_id: str, spec: RuntimeToolSpec) -> RuntimeToolSpec:
        if not TOOL_NAME_PATTERN.match(spec.name):
            raise ValueError("Tool name must be snake_case (e.g. summarize_notes)")
        if spec.name in RESERVED_TOOL_NAMES:
            raise ValueError(f"Tool name '{spec.name}' is reserved")

        filepath = self._mind_dir(mind_id, create=True) / f"{spec.name}.json"
        if filepath.exists():
            raise ValueError(f"Tool '{spec.name}' already exists for this Mind")

        filepath.write_text(spec.model_dump_json(indent=2))
        return spec
