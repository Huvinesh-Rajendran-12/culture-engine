# Decision Log

Architectural and design decisions for the culture-engine monorepo.
Each entry uses a Y-statement summary to capture the "why" concisely.

---

## 001 — Remove unused AgentRegistry from Elixir agent harness

**Date:** 2026-02-26
**Status:** Accepted
**Area:** `apps/agent_harness`

> *In the context of* a single-user CLI agent harness, *facing* an OTP Registry
> (`AgentHarness.AgentRegistry`) that is started but never referenced, *we decided*
> to remove it from the supervision tree, *to achieve* alignment with the
> simplification philosophy (no speculative abstractions), *accepting* that
> multi-agent orchestration will need to re-add process registration later.

**Consequences:**
- Supervision tree is empty — fine for a CLI/escript app.
- Re-adding a Registry or DynamicSupervisor later is a one-line child spec
  once real requirements exist.

---

## 002 — Always continue agent loop after tool execution

**Date:** 2026-02-26
**Status:** Accepted
**Area:** `apps/agent_harness`

> *In the context of* the agent loop's tool execution path, *facing* a dead
> `stop_reason == "end_turn"` branch that would execute tools but discard their
> results if it ever fired, *we decided* to always continue the loop after tool
> execution, *to achieve* correct agentic behavior where the model — not the
> harness — decides when it's done (by returning no tool_use blocks), *accepting*
> no tradeoffs since this is purely a bug/dead-code removal.

**Consequences:**
- The agent loop is simpler: tool execution always feeds results back.
- The model controls termination, not the harness.

---

## 003 — Add Phoenix LiveView web REPL to existing agent harness app

**Date:** 2026-02-26
**Status:** Accepted
**Area:** `apps/agent_harness`

> *In the context of* wanting a browser-based REPL for the agent harness, *facing*
> the choice between a separate Phoenix project or embedding into the existing app,
> *we decided* to add Phoenix/LiveView as deps to the existing `agent_harness` app
> with no Ecto, no esbuild, and no asset pipeline, *to achieve* a minimal web REPL
> that reuses the Agent GenServer's `chat_async` + event message pattern directly
> via LiveView's `handle_info`, *accepting* that the endpoint starts alongside the
> CLI app (port 4000) and pre-built JS must be copied from deps.

**Consequences:**
- Each browser tab gets its own Agent GenServer, linked to the LiveView process for clean lifecycle.
- Zero changes to existing agent code — `agent.ex`, `api.ex`, `tool.ex`, `cli.ex` unchanged.
- Supervision tree now includes `Phoenix.PubSub` and `AgentHarnessWeb.Endpoint`.
- CLI escript still works independently.
- `.env` is loaded at application startup for API key resolution.
