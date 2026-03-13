# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Agent Harness (Elixir/OTP)

```bash
cd apps/agent_harness

mix deps.get                 # Install dependencies
mix phx.server               # Start web UI at http://localhost:4000
mix test                     # Run all tests
mix escript.build            # Build CLI executable
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

### Document Update

Once a crucial decision is made, log it at `docs/decisions.md`. If a new decision
updates, improves or conflicts upon an older one, report that as well.

### Environment Setup

```bash
cd apps/agent_harness
cp .env.example .env
# Set OPENROUTER_API_KEY or ANTHROPIC_API_KEY in .env
# OpenRouter takes priority if both are set
```

## Architecture

Culture Engine is an Elixir/OTP agent runner with a Phoenix LiveView web UI and a CLI REPL. Each agent session is a GenServer with independent conversation history, supervised by OTP.

### Interfaces

- **Web UI** — Phoenix LiveView REPL at `http://localhost:4000`
- **Observatory** — Agent monitoring at `http://localhost:4000/observatory`
- **CLI** — Interactive terminal REPL via `AgentHarness.CLI`

### Agent Loop

```
chat(pid, message)
  └─ run_loop(state, turn, caller)
       ├─ build tool list (filtered by depth + tier)
       ├─ API.chat(messages, tools, opts)  →  Anthropic/OpenRouter
       ├─ handle response:
       │    ├─ tool_use blocks  →  execute tools, append results, loop
       │    └─ text only        →  emit result, done
       └─ special tool handling:
            ├─ spawn_agent  →  create drone GenServer (sync or async)
            └─ create_tool  →  register in agent's ToolSet
```

### Supervision Tree

```
AgentHarness.Supervisor
├─ Registry (AgentHarness.AgentRegistry)       — agent discovery by ID
├─ DynamicSupervisor (AgentHarness.AgentSupervisor) — manages agent processes
├─ AgentHarness.ToolRegistry                   — singleton built-in tool registry
├─ Phoenix.PubSub (AgentHarness.PubSub)        — event broadcasting
└─ AgentHarnessWeb.Endpoint                    — Phoenix HTTP (port 4000)
```

### Key Files (`lib/agent_harness/`)

| File | Responsibility |
|---|---|
| `agent.ex` | GenServer agent loop — chat, tool execution, drone spawning, turn limits |
| `api.ex` | HTTP client for Anthropic/OpenRouter Messages API |
| `tool.ex` | `@behaviour` definition: `name/0`, `description/0`, `input_schema/0`, `execute/1` |
| `tool_registry.ex` | Singleton GenServer + ETS for built-in tool definitions |
| `tool_set.ex` | Per-agent ETS table for dynamic tools (isolation between agents) |
| `names.ex` | Culture-style ship name generator for agents |
| `script_runner.ex` | Executes shebang scripts for dynamic tools (30s timeout, 50KB cap) |
| `cli.ex` | Interactive terminal REPL |

### Tools (9 built-in)

| Tool | Available To | Purpose |
|---|---|---|
| `read_file` | All | Read file contents |
| `list_files` | All | List directory entries |
| `edit_file` | All | Search-and-replace or create files |
| `run_command` | All | Shell commands (30s timeout, 50KB cap) |
| `search_files` | All | Regex content search |
| `list_agents` | All | Discover all running agents |
| `spawn_agent` | Depth < 3 | Spawn drone for subtask (sync or async) |
| `check_drones` | Depth < 3 | Check status of async drones |
| `create_tool` | Mind only | Define new tools at runtime |

### Multi-Agent System

- **Tiers:** `:mind` (top-level) and `:drone` (spawned subtask agent)
- **Depth-limited nesting:** Drones can spawn sub-drones up to `@max_depth` (3). Agents at max depth lose `spawn_agent`.
- **Sync spawning:** Parent blocks while drone runs, receives result as tool output (default)
- **Async spawning:** Drone dispatched in background, reports back via `{:drone_complete, ...}` message
- **Identity:** Each agent gets a short UUID, Culture-style ship name, and registers in `AgentHarness.AgentRegistry`
- **Tool isolation:** Each agent has its own ETS table for dynamic tools via `ToolSet`

### Agent Tool Safety

- `run_command` runs in an isolated environment with a 30s timeout and 50KB output cap
- Dynamic tools are shebang scripts with the same sandbox constraints (max 10 per agent)
- For filesystem search, prefer `rg` for content and `fd` for file/path discovery

### Configuration

Environment variables (loaded from `.env` at startup):

| Setting | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | OpenRouter proxy (takes priority) |
| `ANTHROPIC_API_KEY` | Direct Anthropic access |

Default model: `claude-sonnet-4-20250514`. Max tokens: 8096. API timeout: 120s.
