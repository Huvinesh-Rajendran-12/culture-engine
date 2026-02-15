# FlowForge Backend Quickstart

## 1) Install + Configure

```bash
uv sync
cp .env.example .env
```

Edit `.env` with one key option:

```bash
# Option A: OpenRouter (Anthropic-compatible)
OPENROUTER_API_KEY=your_key
ANTHROPIC_BASE_URL=https://openrouter.ai/api

# Option B: Direct Anthropic
# ANTHROPIC_API_KEY=your_key
```

Optional:

```bash
DEFAULT_MODEL=haiku
```

---

## 2) Start Backend

```bash
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open docs:
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 3) Quick API Smoke Test

### Health

```bash
curl http://localhost:8000/api/health
```

### Generate workflow (SSE)

```bash
curl -N -X POST http://localhost:8000/api/workflows/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create an onboarding workflow for a new engineering hire",
    "context": {
      "employee_name": "Jane Doe",
      "role": "Software Engineer",
      "department": "Engineering"
    },
    "team": "default"
  }'
```

You will receive streamed events such as:
- `text`
- `tool_use`
- `tool_result`
- `workflow`
- `execution_report`
- `result`
- `error`
- `workspace`

---

## 4) Interactive CLI Example

From `apps/backend`:

```bash
OPENROUTER_API_KEY=... ANTHROPIC_BASE_URL=https://openrouter.ai/api \
uv run python examples/interactive_workflow_generator.py
```

---

## 5) Mental Model

FlowForge uses a **unified agent** that can:
1. understand request/context,
2. write/modify `workflow.json`,
3. validate against schema,
4. execute in simulator,
5. self-correct on failures.

Default tools are intentionally minimal and composable:
- `read_file`, `write_file`, `edit_file`, `search_apis`, `search_knowledge_base`

---

## 6) Troubleshooting

- **Auth errors**: verify `.env` keys and endpoint settings
- **No workflow produced**: inspect streamed `error` + `tool_result` events
- **Port conflict**: run with `--port 8001`
- **Dependency issues**: rerun `uv sync`
