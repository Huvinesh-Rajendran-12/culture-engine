# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend

```bash
cd apps/backend

uv sync                                                    # Install/update dependencies
uv run uvicorn backend.main:app --reload --port 8100       # Start dev server
uv run python -m pytest tests/test_agent_base.py           # Run agent tests
```

### Frontend

```bash
bun run dev:frontend      # Start Vite dev server (from repo root)
bun run build:frontend    # Production build (from repo root)
# Or from apps/frontend/:
bun run dev
bun run build
```

### Version Control

This repo uses **jj (Jujutsu)** colocated with Git. Prefer `jj` commands over `git`:

```bash
jj log                       # View commit history
jj describe -m "message"     # Set description on current commit
jj new                       # Start a new change
jj diff                      # Show changes in current commit
jj git push                  # Push to remote
jj git fetch                 # Fetch from remote
```

### Environment Setup

```bash
cd apps/backend
cp .env.example .env
# Set OPENROUTER_API_KEY or ANTHROPIC_API_KEY in .env
```

## Architecture

Culture Engine is a monorepo with a FastAPI backend and a Svelte frontend. The backend is a minimal agent runner that streams SSE events to the frontend.

### Request Flow

```
POST /run (SSE stream)
  └─ main.py handler
       └─ run_agent(prompt, system_prompt, workspace_dir, team, ...)
            ├─ build tool list (read_file, write_file, edit_file, run_command)
            ├─ create Anthropic client (direct or OpenRouter)
            ├─ agent loop: request → tool execution → continue
            └─ yield normalized SSE dict events
```

`main.py` exposes two endpoints:
- `GET /health` — health check
- `POST /run` — SSE agent stream

SSE events are plain dicts: `{"type": ..., "content": ...}`. Common event types: `tool_use`, `tool_result`, `text`, `result`, `error`.

### Key Files (`src/backend/`)

| File | Responsibility |
|---|---|
| `main.py` | FastAPI app with `/health` and `/run` endpoints |
| `config.py` | Pydantic `BaseSettings` for env-based configuration |
| `agents/base.py` | `run_agent()` — Anthropic/OpenRouter agent loop, yields SSE events |
| `agents/tools.py` | `DEFAULT_TOOL_NAMES` — workspace tools: read_file, write_file, edit_file, run_command |
| `agents/types.py` | `AgentTool`, `AgentToolResult`, `AgentToolSchema`, `TextContent` dataclasses |

### Agent Tool Safety

- All file tools resolve paths through `_resolve_path()` to prevent workspace escape
- `run_command` runs in an isolated environment with a 30s timeout and 50 KB output cap
- For filesystem search, prefer `rg` for content and `fd` for file/path discovery

### Configuration

`src/backend/config.py` uses Pydantic `BaseSettings` (reads from `.env`):

| Setting | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Direct Anthropic access |
| `OPENROUTER_API_KEY` | OpenRouter proxy (recommended) |
| `ANTHROPIC_BASE_URL` | Override base URL (e.g., `https://openrouter.ai/api`) |
| `ANTHROPIC_AUTH_TOKEN` | Auth token for proxy |
| `DEFAULT_MODEL` | `haiku` (default), `sonnet`, or `opus` |

### Testing

- `tests/test_agent_base.py` — model resolution and agent base tests

```bash
cd apps/backend
uv run python -m pytest tests/test_agent_base.py
```

### Frontend

Frontend ships as an Agent Observatory at `apps/frontend/`:
- Prompt input bar for submitting agent tasks
- Activity Stream with Output / Trace views for SSE events
- Central Nexus status indicator
