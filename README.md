# Culture Engine

Culture Engine is a lightweight agent runner built on Elixir/OTP, with a Phoenix LiveView observatory for interactive prompt-driven sessions.

---

## Structure

| Directory | Stack | Description |
|---|---|---|
| `apps/agent_harness` | Elixir, Phoenix, LiveView | Agent runner with OTP supervision, CLI REPL, and web UI |

---

## Quick Start

### Prerequisites
- [Elixir](https://elixir-lang.org/install.html) ~> 1.19
- OTP 27+

### 1) Configure

```bash
cd apps/agent_harness
cp .env.example .env
# Set ANTHROPIC_API_KEY or OPENROUTER_API_KEY in .env
```

### 2) Run the web UI

```bash
cd apps/agent_harness
mix deps.get
mix phx.server
```

Open `http://localhost:4000` for the LiveView REPL.

### 3) Run the CLI REPL

```bash
cd apps/agent_harness
mix run --no-halt -e "AgentHarness.CLI.main()"
```

---

## Agent Tools

The agent has access to workspace tools:
- `read_file` — read a text file
- `list_files` — list directory contents
- `edit_file` — replace text in a file or create new files

---

## Current Direction

Design principle: **simplify first, extend second**.

The Python/Svelte stack has been retired in favor of a unified Elixir/OTP architecture.
Future iterations will add `run_command`, persistence, memory, and multi-agent
orchestration on top of this foundation.

---

## Documentation

- Agent map: `AGENTS.md`
- Branch protection baseline: `.github/BRANCH_PROTECTION.md`
