# FlowForge Backend

FastAPI backend for FlowForge's unified workflow agent.

The agent can:
- chat and clarify requirements,
- generate or modify `workflow.json`,
- validate and execute workflows in a simulator,
- self-correct when parsing/execution fails,
- stream progress via Server-Sent Events (SSE).

## Tech Stack

- Python 3.13
- FastAPI
- pi-agent-core
- Anthropic/OpenRouter (Anthropic-compatible API)

## Setup

```bash
uv sync
cp .env.example .env
```

Set one of these auth options in `.env`:

- `OPENROUTER_API_KEY=...` (recommended)
- or `ANTHROPIC_API_KEY=...`

Optional:

- `ANTHROPIC_BASE_URL=https://openrouter.ai/api`
- `ANTHROPIC_AUTH_TOKEN=...`
- `DEFAULT_MODEL=haiku`

## Run API

```bash
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

## Endpoints

### `GET /api/health`
Health check.

### `POST /api/workflows/generate`
Generate or modify a workflow from natural language.

Request body:

```json
{
  "description": "Create an onboarding workflow for engineering hires",
  "context": {
    "department": "Engineering",
    "manager": "Jane Doe"
  },
  "team": "default",
  "workflow_id": null
}
```

Response is an SSE stream of JSON events.
Common event types:
- `text`
- `tool_use`
- `tool_result`
- `workflow`
- `execution_report`
- `workflow_saved`
- `result`
- `error`
- `workspace`

### Workflow storage endpoints

- `GET /api/workflows?team=default`
- `GET /api/workflows/{workflow_id}?team=default`
- `DELETE /api/workflows/{workflow_id}?team=default`

## Agent Architecture (Current)

Core files:

- `src/backend/agents/workflow_agent.py`
  - unified agent orchestration for generate/modify/fix
- `src/backend/agents/base.py`
  - pi-agent-core runner + SSE event translation
- `src/backend/agents/tools.py`
  - tool definitions and execution
- `src/backend/workflow/`
  - schema, executor, report, and file store
- `src/backend/simulator/`
  - simulated services and failure injection

## Minimal Toolset Philosophy

FlowForge intentionally uses a small composable default toolset:

- `read_file`
- `write_file`
- `edit_file`
- `search_apis`
- `search_knowledge_base`

Source of truth: `src/backend/agents/tools.py` (`DEFAULT_TOOL_NAMES`).

## Examples

- `examples/workflow_example.py` — SSE client call to backend endpoint
- `examples/interactive_workflow_generator.py` — interactive CLI using pi-agent-core style

## Tests

Current tests include both legacy and newer suites:

- `test_workflow_agent.py`
- `test_workflow_e2e.py`
- `tests/test_workflow_engine_core.py`
- `tests/test_workflow_generation.py`
- `tests/test_integration_openrouter.py`

Run (if test deps are installed):

```bash
uv run pytest
```
