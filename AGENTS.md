# AGENTS.md

This is the agent-facing map for the `culture-engine/` monorepo.

The project is a **minimal agent runner** built on Elixir/OTP. When in doubt, keep
changes simple and aligned with this minimal foundation.

---

## 1) Monorepo Overview

- `apps/agent_harness` — Elixir/Phoenix agent runner with LiveView UI and CLI REPL

---

## 2) Product Shape

### Agent Runner
The user submits a prompt and the agent works in a tool loop until done.

Interfaces:
- **Web UI** — Phoenix LiveView REPL at `http://localhost:4000`
- **CLI** — Interactive terminal REPL via `AgentHarness.CLI`

The agent loop runs as a GenServer. Each session gets its own process with
independent conversation history, supervised by OTP.

### LiveView Observatory
The LiveView REPL shows:
- User messages, agent responses, tool calls, and tool results in real-time
- Loading state while the agent is thinking
- `/reset` command to clear conversation

---

## 3) Architecture (`apps/agent_harness/lib`)

| File | Responsibility |
|---|---|
| `agent_harness/application.ex` | OTP supervision tree (PubSub, Endpoint) |
| `agent_harness/agent.ex` | GenServer agent loop — chat, tool execution, turn limits |
| `agent_harness/api.ex` | HTTP client for Anthropic/OpenRouter Messages API |
| `agent_harness/tool.ex` | `@behaviour` for agent tools |
| `agent_harness/tool_registry.ex` | Registry mapping tool names → modules |
| `agent_harness/cli.ex` | Interactive terminal REPL |
| `agent_harness/tools/*.ex` | Tool implementations (read_file, list_files, edit_file) |
| `agent_harness_web/router.ex` | Phoenix router |
| `agent_harness_web/repl_live.ex` | LiveView REPL page |
| `agent_harness_web/endpoint.ex` | Phoenix endpoint |
| `agent_harness_web/layouts.ex` | Layout templates |

---

## 4) Simplification Rules

1. Prefer the smallest vertical slice that works.
2. Avoid speculative abstractions.
3. Keep orchestration explicit; avoid hidden magic.
4. Keep temporary workspace lifecycle automatic and bounded.
5. New tools implement the `AgentHarness.Tool` behaviour.

---

## 5) Tools

Tool modules live in `lib/agent_harness/tools/` and implement `AgentHarness.Tool`:
- `read_file` — read file contents
- `list_files` — list directory entries
- `edit_file` — search-and-replace or create files

Registered in `AgentHarness.ToolRegistry`. Guideline: composition/prompting first,
new tools only when necessary.

---

## 6) Config & Environment

Environment (`apps/agent_harness/.env`):
- `OPENROUTER_API_KEY` or `ANTHROPIC_API_KEY` (OpenRouter takes priority)

Run:
```bash
cd apps/agent_harness
mix deps.get
mix phx.server        # Web UI at http://localhost:4000
```

---

## 7) Contributor Conventions

- Keep tool names in snake_case.
- Tools implement the `AgentHarness.Tool` behaviour.
- Use `jj` (Jujutsu) for version control. The repo is colocated (`.jj` + `.git`),
  so `git` commands still work, but prefer `jj`.

---

## 8) Testing

```bash
cd apps/agent_harness
mix test
```

---

## 9) Near-term Plan

1. Add `run_command` tool (sandboxed shell execution).
2. Improve LiveView UI (styling, markdown rendering).
3. Add focused tests for agent loop and tool execution.
4. Future: persistence, memory, and multi-agent orchestration.
