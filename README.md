# Culture Engine

Culture Engine is a delegation platform powered by persistent autonomous **Minds** with explicit **Drone** sub-agent traces.

---

## Monorepo Structure

| Directory | Stack | Description |
|---|---|---|
| `apps/backend` | Python, FastAPI, pi-agent-core, SQLite | API for Mind delegation, task traces, and memory |
| `apps/frontend` | Svelte, Vite, TypeScript | Spatial Mind Observatory web client |

---

## Quick Start

### Prerequisites
- [uv](https://docs.astral.sh/uv/)
- [Bun](https://bun.sh/) 1.0+
- Node.js 18+ (optional, only if you prefer npm in local workflows)

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

- Frontend: `http://localhost:5173` (or next available port)
- Backend: `http://localhost:8100`
- Swagger: `http://localhost:8100/docs`

---

## Backend API shape

### Culture Engine (new)
- `POST /api/minds`
- `GET /api/minds`
- `GET /api/minds/{mind_id}`
- `PATCH /api/minds/{mind_id}`
- `POST /api/minds/{mind_id}/feedback`
- `POST /api/minds/{mind_id}/delegate` (SSE)
- `GET /api/minds/{mind_id}/tasks`
- `GET /api/minds/{mind_id}/tasks/{task_id}`
- `GET /api/minds/{mind_id}/tasks/{task_id}/drones`
- `GET /api/minds/{mind_id}/tasks/{task_id}/trace`
- `GET /api/minds/{mind_id}/drones/{drone_id}/trace`
- `GET /api/minds/{mind_id}/memory`

Mind learning supports explicit feedback plus profile-update preference signals.

### Health
- `GET /api/health`

---

## Current Direction

- **Phase 1 complete (simplified):** Mind identity + memory + reasoning + single-path delegation pipeline.
- **Phase 2 (simplified foundation) now in place:**
  - plain per-run tool list assembly,
  - memory primitives (`memory_save`, `memory_search`),
  - explicit sub-agent delegation (`spawn_agent`),
  - SQLite (WAL mode) persistence with FTS5 full-text memory search.
- **Frontend observatory now active:**
  - central Nexus + task constellation,
  - persistent commission bar,
  - Activity Stream (Output/Trace) and overlays for memory/task/profile views.
- Deferred intentionally: runtime tool registration API and persistent dynamic tool store.

Design principle: **simplify first, extend second**.

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
