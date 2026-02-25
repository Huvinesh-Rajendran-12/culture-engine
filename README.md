# Culture Engine

Culture Engine is a lightweight agent runner powered by the Anthropic SDK, with a spatial observatory frontend for interactive prompt-driven sessions.

---

## Monorepo Structure

| Directory | Stack | Description |
|---|---|---|
| `apps/backend` | Python, FastAPI, Anthropic SDK | Agent runner API with SSE streaming |
| `apps/frontend` | Svelte 5, Vite, TypeScript | Agent Observatory web client |
| `apps/agent_harness` | Elixir, Req, Jason | Experimental Elixir agent harness (side project) |

---

## Quick Start

### Prerequisites
- [uv](https://docs.astral.sh/uv/)
- [Bun](https://bun.sh/) 1.0+

### 1) Run backend

```bash
cd apps/backend
uv sync
cp .env.example .env
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8100
```

### 2) Run frontend

```bash
bun install
bun run dev:frontend

# Or from apps/frontend:
bun run dev
```

- Frontend: `http://localhost:5174`
- Backend: `http://localhost:8100`
- Swagger: `http://localhost:8100/docs`

---

## Backend API

- `GET /health` — health check
- `POST /run` — run an agent session (SSE stream)

The `/run` endpoint accepts:
```json
{
  "prompt": "Your task description",
  "system_prompt": "",
  "team": "default",
  "workspace_dir": null,
  "allowed_tools": null,
  "max_turns": 50
}
```

It returns a Server-Sent Events stream with event types: `text`, `tool_use`, `tool_result`, `result`, `error`.

### Available Agent Tools

The agent has access to workspace-sandboxed tools:
- `read_file` — read a text file
- `write_file` — write content to a file
- `edit_file` — replace text in a file
- `run_command` — run a shell command (30s timeout, sanitized env)

---

## Current Direction

Design principle: **simplify first, extend second**.

The Mind/Drone delegation architecture has been removed in favor of a minimal agent runner.
Future iterations may re-introduce persistence, memory, and multi-agent orchestration
on top of this simplified foundation.

---

## Root scripts

```bash
bun run dev:frontend
bun run dev:backend
bun run build:frontend
```

---

## Documentation

- Agent map: `AGENTS.md`
- Backend details: `apps/backend/README.md`
- Backend quickstart: `apps/backend/QUICKSTART.md`
- Branch protection baseline: `.github/BRANCH_PROTECTION.md`
