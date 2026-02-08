# FlowForge

AI agents that turn natural language ideas into working, executable workflows.

## Monorepo Structure

| Directory | Stack | Description |
|---|---|---|
| `apps/backend` | Python, FastAPI, Claude Agent SDK | Workflow generation API (SSE streaming) |
| `apps/frontend` | React, Vite | Web interface |

## Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Bun](https://bun.sh/) (JavaScript runtime & package manager)

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
bun install
bun run dev
```

## Testing

```bash
cd apps/backend
uv sync
uv run python test_workflow_agent.py
```

Tests 1–8 are deterministic and run without an API key:

| Test | What it covers |
|---|---|
| 1 | Workflow schema round-trip |
| 2a–c | Simulator services, ordering, failure injection |
| 3 | DAG executor topological ordering |
| 4 | Failure cascade (downstream skip) |
| 5 | API catalog keyword search |
| 6 | KB section search |
| 7 | MCP server creation |
| 8 | Workflow store save/load/delete |

Test 9 is an end-to-end agent test that requires `ANTHROPIC_API_KEY` in your `.env`. It generates a full onboarding workflow, executes it against the simulator, and saves the result.

## License

MIT
