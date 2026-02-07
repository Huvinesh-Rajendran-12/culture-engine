# FlowForge Backend

FastAPI backend powered by the Claude Agent SDK. It takes a natural language description of a workflow, designs it, writes executable Python code, runs it, self-corrects on failure, and returns working automation -- all streamed over SSE.

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- Anthropic API key

## Setup

1. Install dependencies:

```bash
uv sync
```

2. Create a `.env` file from the example:

```bash
cp .env.example .env
```

3. Add your Anthropic API key to `.env`:

```
ANTHROPIC_API_KEY=your_api_key_here
```

## Running the Server

```bash
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

Swagger UI docs are at `http://localhost:8000/docs`.

## API

### Health Check

```http
GET /api/health
```

### Generate Workflow

```http
POST /api/workflows/generate
Content-Type: application/json

{
  "description": "Create an employee onboarding workflow that sends welcome emails, creates accounts, and assigns training tasks",
  "context": {
    "company": "TechCorp",
    "systems": ["Slack", "JIRA", "HR Portal"]
  }
}
```

The response is an SSE stream. Each event is a JSON object representing a step in the agent's process (discovery, design, code generation, execution results, error correction, final report).

## Architecture

The agent follows a five-phase pipeline:

1. **Discover** -- Reads the knowledge base (`kb/` directory) to understand organizational context: systems, roles, policies.
2. **Design** -- Produces a structured workflow specification from the user's description and the discovered context.
3. **Build** -- Writes executable Python code that implements the workflow.
4. **Test** -- Runs the generated code, captures output and errors.
5. **Report** -- If execution fails, the agent self-corrects and retries. On success, it returns the working code and a summary.

All phases stream progress to the client as SSE events.

## Project Structure

```
apps/backend/
├── src/backend/
│   ├── __init__.py
│   ├── main.py                # FastAPI app and endpoints
│   ├── config.py              # Configuration management
│   ├── models.py              # Pydantic models for API
│   └── agents/
│       ├── __init__.py
│       ├── base.py            # Claude Agent SDK wrapper
│       └── workflow_agent.py  # Workflow generation agent
├── kb/                        # Knowledge base (org context)
│   ├── onboarding_policy.md
│   ├── roles.md
│   └── systems.md
├── examples/
│   └── workflow_example.py    # Example client usage
├── .env.example
├── pyproject.toml
└── README.md
```

## Configuration

Environment variables (set in `.env`):

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | -- | Your Anthropic API key |
| `DEFAULT_MODEL` | No | `sonnet` | Claude model to use |

## Running Tests

```bash
uv run pytest
```

## License

MIT
