# FlowForge Backend - Quick Start Guide

## Setup

### 1. Get an Anthropic API Key

Obtain your API key from: https://console.anthropic.com/

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set your API key:

```
ANTHROPIC_API_KEY=your_actual_api_key_here
```

### 3. Start the Server

```bash
uv sync
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The server will start at `http://localhost:8000`.

## API Documentation

Once the server is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Test the API

### Health Check

```bash
curl http://localhost:8000/api/health
```

### Generate a Workflow (SSE stream)

```bash
curl -N -X POST http://localhost:8000/api/workflows/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Onboard a new employee named Jane Doe to the Engineering team",
    "context": {
      "department": "Engineering",
      "manager": "John Smith",
      "start_date": "2026-03-01"
    }
  }'
```

The response is a Server-Sent Events stream. Each event contains a JSON object with `type` and `content` fields:

- `text` — Agent reasoning and explanations
- `tool_use` — Tools being invoked (Write, Bash, Read, etc.)
- `result` — Final result with cost and usage data
- `error` — Any errors encountered

## Architecture

```
User Input (Natural Language)
    |
    v
Knowledge Base Discovery (Read org systems, roles, policies)
    |
    v
Workflow Design (Structured plan with steps and dependencies)
    |
    v
Code Generation (Executable Python workflow)
    |
    v
Automated Testing (Run, validate, fix, re-run)
    |
    v
Final Output (Working workflow + summary)
```

## Configuration

Edit `.env` to customize:

```bash
# Required
ANTHROPIC_API_KEY=your_key_here

# Optional
DEFAULT_MODEL=sonnet
```

## Troubleshooting

**Import errors:**

```bash
uv sync
```

**API key not working:**

- Verify `.env` exists and contains your key
- Ensure the key has no surrounding quotes
- Confirm the key is valid at https://console.anthropic.com/

**Port already in use:**

```bash
uv run uvicorn backend.main:app --reload --port 8001
```

## References

- [Claude Agent SDK Documentation](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Anthropic API Documentation](https://docs.anthropic.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
