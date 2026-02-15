from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from pi_agent_core import AgentTool, AgentToolResult, AgentToolSchema, TextContent

from .api_catalog import search_api_catalog
from .kb_search import search_knowledge_base


def _text_result(value: str) -> AgentToolResult:
    return AgentToolResult(content=[TextContent(text=value)])


def _resolve_path(cwd: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    path = (candidate if candidate.is_absolute() else cwd / candidate).resolve()

    cwd_resolved = cwd.resolve()
    try:
        path.relative_to(cwd_resolved)
    except ValueError as exc:
        raise ValueError(f"Path escapes workspace: {raw_path}") from exc

    return path


def create_flowforge_tools(team: str, workspace_dir: str) -> list[AgentTool]:
    cwd = Path(workspace_dir).resolve()

    async def read_tool_execute(tool_call_id: str, params: dict, **_: object) -> AgentToolResult:
        path = _resolve_path(cwd, params["path"])
        if not path.exists():
            raise ValueError(f"File not found: {path}")
        if path.is_dir():
            raise ValueError(f"Path is a directory: {path}")
        return _text_result(path.read_text())

    async def write_tool_execute(tool_call_id: str, params: dict, **_: object) -> AgentToolResult:
        path = _resolve_path(cwd, params["path"])
        content = params.get("content", "")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return _text_result(f"Wrote {len(content)} chars to {path}")

    async def edit_tool_execute(tool_call_id: str, params: dict, **_: object) -> AgentToolResult:
        path = _resolve_path(cwd, params["path"])
        old_text = params["old_text"]
        new_text = params["new_text"]

        current = path.read_text()
        if old_text not in current:
            raise ValueError("old_text not found in file")

        updated = current.replace(old_text, new_text, 1)
        path.write_text(updated)
        return _text_result(f"Edited file: {path}")

    async def bash_tool_execute(tool_call_id: str, params: dict, **_: object) -> AgentToolResult:
        command = params["command"]
        timeout = int(params.get("timeout", 30))

        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError:
            proc.kill()
            await proc.communicate()
            raise ValueError(f"Command timed out after {timeout}s")

        out = stdout.decode(errors="replace")
        err = stderr.decode(errors="replace")
        payload = {
            "exit_code": proc.returncode,
            "stdout": out,
            "stderr": err,
        }
        return _text_result(json.dumps(payload, indent=2))

    async def glob_tool_execute(tool_call_id: str, params: dict, **_: object) -> AgentToolResult:
        pattern = params["pattern"]
        matches = sorted(str(p.relative_to(cwd)) for p in cwd.glob(pattern))
        return _text_result(json.dumps(matches, indent=2))

    async def grep_tool_execute(tool_call_id: str, params: dict, **_: object) -> AgentToolResult:
        pattern = params["pattern"]
        include = params.get("include", "**/*")
        regex = re.compile(pattern)
        results: list[dict[str, object]] = []

        for file_path in cwd.glob(include):
            if not file_path.is_file():
                continue

            try:
                lines = file_path.read_text().splitlines()
            except UnicodeDecodeError:
                continue

            for idx, line in enumerate(lines, start=1):
                if regex.search(line):
                    results.append(
                        {
                            "file": str(file_path.relative_to(cwd)),
                            "line": idx,
                            "text": line,
                        }
                    )

        return _text_result(json.dumps(results, indent=2))

    async def search_apis_execute(tool_call_id: str, params: dict, **_: object) -> AgentToolResult:
        query = params["query"]
        top_k = int(params.get("top_k", 5))
        results = [entry.to_dict() for entry in search_api_catalog(query, top_k=top_k)]
        return _text_result(json.dumps(results, indent=2))

    async def search_kb_execute(tool_call_id: str, params: dict, **_: object) -> AgentToolResult:
        query = params["query"]
        top_k = int(params.get("top_k", 5))
        results = [section.to_dict() for section in search_knowledge_base(query, team=team, top_k=top_k)]
        return _text_result(json.dumps(results, indent=2))

    return [
        AgentTool(
            name="Read",
            description="Read a text file from the workspace.",
            parameters=AgentToolSchema(
                properties={"path": {"type": "string", "description": "Absolute or workspace-relative file path."}},
                required=["path"],
            ),
            execute=read_tool_execute,
        ),
        AgentTool(
            name="Write",
            description="Write text content to a file, creating parent directories if needed.",
            parameters=AgentToolSchema(
                properties={
                    "path": {"type": "string", "description": "Absolute or workspace-relative file path."},
                    "content": {"type": "string", "description": "File content."},
                },
                required=["path", "content"],
            ),
            execute=write_tool_execute,
        ),
        AgentTool(
            name="Edit",
            description="Replace the first occurrence of old_text with new_text in a file.",
            parameters=AgentToolSchema(
                properties={
                    "path": {"type": "string", "description": "Absolute or workspace-relative file path."},
                    "old_text": {"type": "string", "description": "Exact text to replace."},
                    "new_text": {"type": "string", "description": "Replacement text."},
                },
                required=["path", "old_text", "new_text"],
            ),
            execute=edit_tool_execute,
        ),
        AgentTool(
            name="Bash",
            description="Run a shell command in the workspace.",
            parameters=AgentToolSchema(
                properties={
                    "command": {"type": "string", "description": "Shell command to execute."},
                    "timeout": {"type": "integer", "description": "Timeout in seconds.", "default": 30},
                },
                required=["command"],
            ),
            execute=bash_tool_execute,
        ),
        AgentTool(
            name="Glob",
            description="Find files matching a glob pattern from the workspace root.",
            parameters=AgentToolSchema(
                properties={"pattern": {"type": "string", "description": "Glob pattern (e.g., **/*.py)."}},
                required=["pattern"],
            ),
            execute=glob_tool_execute,
        ),
        AgentTool(
            name="Grep",
            description="Search files for a regular expression pattern.",
            parameters=AgentToolSchema(
                properties={
                    "pattern": {"type": "string", "description": "Regex pattern."},
                    "include": {"type": "string", "description": "Glob include filter.", "default": "**/*"},
                },
                required=["pattern"],
            ),
            execute=grep_tool_execute,
        ),
        AgentTool(
            name="search_apis",
            description=(
                "Search available APIs by intent or keyword. "
                "Returns matching service actions with parameters and auth info."
            ),
            parameters=AgentToolSchema(
                properties={
                    "query": {"type": "string", "description": "Natural language query describing the API capability needed."},
                    "top_k": {"type": "integer", "description": "Maximum results to return.", "default": 5},
                },
                required=["query"],
            ),
            execute=search_apis_execute,
        ),
        AgentTool(
            name="search_knowledge_base",
            description=(
                "Search the organization's knowledge base for policies, roles, systems, and procedures."
            ),
            parameters=AgentToolSchema(
                properties={
                    "query": {"type": "string", "description": "Natural language query describing the information needed."},
                    "top_k": {"type": "integer", "description": "Maximum results to return.", "default": 5},
                },
                required=["query"],
            ),
            execute=search_kb_execute,
        ),
    ]
