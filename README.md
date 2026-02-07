# FlowForge

AI agents that turn natural language ideas into working, executable workflows.

## Monorepo Structure

| Directory | Stack | Description |
|---|---|---|
| `apps/backend` | Python, FastAPI, Claude Agent SDK | Workflow generation API (SSE streaming) |
| `apps/frontend` | React, Vite | Web interface |

## Quick Start

### Backend

```bash
cd apps/backend
cp .env.example .env   # add your ANTHROPIC_API_KEY
uv sync
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd apps/frontend
npm install
npm run dev
```

## License

MIT
