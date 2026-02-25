# AGENTS.md

This is the agent-facing map for the `culture-engine/` monorepo.

The project has been simplified to a **minimal agent runner**. The previous Mind/Drone
architecture has been removed. When in doubt, keep changes simple and aligned with this
minimal foundation.

---

## 1) Monorepo Overview

- `apps/backend` — Python FastAPI agent runner with SSE streaming
- `apps/frontend` — Svelte 5 + Vite Agent Observatory UI
- `apps/agent_harness` — Elixir experimental agent harness (side project)

Root scripts (`package.json`):
- `dev:frontend`
- `dev:backend`
- `build:frontend`

---

## 2) Product Shape (Current)

### Backend: Agent Runner
The backend is a minimal agent runner. The user submits a prompt and receives an SSE
stream of events as the agent works.

Current backend endpoints:
- `GET /health`
- `POST /run` (SSE stream)

The `/run` endpoint accepts a `RunRequest`:
- `prompt` (required) — the task description
- `system_prompt` — optional system prompt override
- `team` — team name (default: `"default"`)
- `workspace_dir` — optional workspace path
- `allowed_tools` — optional tool allowlist
- `max_turns` — max agent loop iterations (default: 50)

SSE event types: `text`, `tool_use`, `tool_result`, `result`, `error`.

### Frontend: Agent Observatory
The frontend is a single-view observatory experience:
- top bar: brand header + status chip
- center canvas: Nexus status indicator + Activity Stream (Output / Trace)
- bottom rail: persistent prompt bar for task submission

---

## 3) Backend Architecture (`apps/backend/src/backend`)

| File | Responsibility |
|---|---|
| `main.py` | FastAPI app — `/health` and `/run` endpoints |
| `config.py` | Pydantic `BaseSettings` (env-based config) |
| `agents/base.py` | `run_agent()` — Anthropic/OpenRouter agent loop, yields SSE events |
| `agents/tools.py` | Workspace tools: `read_file`, `write_file`, `edit_file`, `run_command` |
| `agents/types.py` | `AgentTool`, `AgentToolResult`, `AgentToolSchema`, `TextContent` |

### Agent Tool Safety

- All file tools resolve paths through `_resolve_path()` to prevent workspace escape
- `run_command` runs in an isolated environment with a 30s timeout and 50 KB output cap
- For filesystem search, prefer `rg` (content) and `fd` (file paths)

---

## 4) Simplification Rules

1. Prefer the smallest vertical slice that works.
2. Avoid speculative abstractions.
3. Keep orchestration explicit; avoid hidden magic.
4. Keep temporary workspace lifecycle automatic and bounded.
5. SSE event contract: `type` + `content` required; additional fields are additive only.

---

## 5) Tooling Philosophy

Tool allowlist in `agents/tools.py` → `DEFAULT_TOOL_NAMES`:
- `read_file`, `write_file`, `edit_file`, `run_command`

Guideline: composition/prompting first, new tools only when necessary.

---

## 6) Config & Environment

Backend env (`apps/backend/.env`):
- `OPENROUTER_API_KEY` or `ANTHROPIC_API_KEY`
- optional `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`
- `DEFAULT_MODEL` (`haiku`, `sonnet`, or `opus`)

Run backend:
```bash
cd apps/backend
uv sync
uv run uvicorn backend.main:app --reload --port 8100
```

Run frontend:
```bash
bun install
bun run dev:frontend
```

---

## 7) Contributor Conventions

- Keep tool names in snake_case.
- Maintain workspace path safety for file tools.
- Preserve SSE message compatibility (`type` + `content` required).
- Keep docs aligned with implementation in `src/backend/`.
- For filesystem discovery via `run_command`, prefer `rg` (content) and `fd` (file paths).

---

## 8) Testing

```bash
cd apps/backend
uv run python -m pytest tests/test_agent_base.py
```

---

## 9) Near-term Plan

1. Keep the minimal agent runner stable.
2. Add focused tests for agent loop and tool execution.
3. Future: re-introduce persistence, memory, and multi-agent orchestration on this foundation.
