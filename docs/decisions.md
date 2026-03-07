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

---

## 004 — Dynamic self-tooling via ETS-backed ToolRegistry and create_tool meta-tool

**Date:** 2026-03-02
**Status:** Accepted
**Area:** `apps/agent_harness`

> *In the context of* wanting the agent to adapt to novel tasks by creating its own
> tools at runtime, *facing* a compile-time `@tools` list that prevented dynamic
> registration, *we decided* to make `ToolRegistry` a GenServer backed by ETS (seeded
> with built-in modules on init) and add a `create_tool` meta-tool that accepts a
> name, description, input_schema, and a shebang script, *to achieve* runtime tool
> creation where script-based tools receive JSON input via stdin/TOOL_INPUT env var
> and write output to stdout, *accepting* per-session scope (ETS dies with process),
> a 10-tool cap to avoid tool-list bloat, and the same 30s/50KB sandbox as run_command.

**Consequences:**
- The agent loop (`agent.ex`) required zero changes — it already calls `ToolRegistry.all_definitions()` each turn, so new tools are visible immediately.
- Built-in tools cannot be overridden or removed (enforced by registry).
- Scripts are written to temp files with `0o755` permissions, cleaned up on unregister.
- Shell/Python scripts are natural for the model to write; Elixir runtime compilation was rejected as harder to sandbox with no additional benefit.
- `ToolRegistry` is now a supervised GenServer in the application tree.

---

## 005 — Agent identity via struct fields and Elixir Registry

**Date:** 2026-03-05
**Status:** Accepted
**Area:** `apps/agent_harness`

> *In the context of* wanting Culture-inspired multi-agent orchestration, *facing*
> agents with no identity, no supervision, and no discoverability, *we decided*
> to add `id` (short UUID), `name` (Culture-style ship name), `tier` (:mind/:drone),
> and `parent` (PID) to the Agent struct, with process lookup via Elixir's built-in
> Registry (`AgentHarness.AgentRegistry`), *to achieve* named, discoverable agents
> that can be supervised and observed, *accepting* that the Registry is in-memory
> only and agent names are randomly generated (not persisted).

**Consequences:**
- Each agent registers with `{:via, Registry, {AgentHarness.AgentRegistry, id}}` on start.
- `Agent.list_agents/0` queries the Registry for all running agents.
- Events changed from 2-tuple `{:agent_event, event}` to 3-tuple `{:agent_event, agent_id, event}`.
- Agent lifecycle events broadcast on PubSub topics `"agent:<id>"` and `"agents"`.
- `DynamicSupervisor` owns all agent processes; LiveView uses `Process.monitor` instead of `Process.link`.

---

## 006 — Synchronous drone pattern for multi-agent spawning

**Date:** 2026-03-05
**Status:** Accepted
**Area:** `apps/agent_harness`

> *In the context of* wanting Mind-level agents to delegate subtasks, *facing*
> the complexity of async inter-agent messaging, *we decided* to implement drones
> as synchronous tool calls — the parent blocks while the drone runs `chat/2`,
> then receives the drone's final text as the tool result, *to achieve* multi-agent
> delegation with zero async coordination, *accepting* that the parent is blocked
> during drone execution and async messaging is deferred to a future phase.

**Consequences:**
- `spawn_agent` is a tool like any other — the model calls it, waits, gets a result.
- Drones are filtered from `spawn_agent` and `create_tool` tools to prevent recursive spawning.
- Drones terminate after their task completes.
- `max_turns` defaults to 5 for drones (vs 20 for minds) to bound subtask scope.

---

## 007 — Per-agent tool isolation via ToolSet with separate ETS tables

**Date:** 2026-03-05
**Status:** Accepted (supersedes dynamic tool aspects of D004)
**Area:** `apps/agent_harness`

> *In the context of* agents creating dynamic tools at runtime, *facing* a global
> singleton ToolRegistry where one agent's dynamic tools leak to all others, *we
> decided* to introduce `ToolSet` — each agent gets its own ETS table for dynamic
> tools, while built-in tool definitions stay in the singleton ToolRegistry, *to
> achieve* per-agent tool isolation where a drone's custom tools don't pollute
> the parent's namespace, *accepting* that built-in tools remain global (which is
> correct — they're stateless) and `create_tool` is now intercepted in the agent
> loop rather than dispatched through ToolRegistry.

**Consequences:**
- `ToolSet.new(agent_id)` creates a per-agent ETS table, destroyed in `terminate/2`.
- Agent loop calls `ToolSet.all_definitions(table)` which merges built-in + agent-local tools.
- `ToolRegistry` becomes effectively read-only at runtime — only serves built-in definitions.
- Dynamic tool script cleanup happens per-agent in `ToolSet.destroy/1`.

---

## 008 — Drone subagent spawning with depth-limited recursion

**Date:** 2026-03-07
**Status:** Accepted (updates D006)
**Area:** `apps/agent_harness`

> *In the context of* wanting drones to decompose their own subtasks via further
> delegation, *facing* a blanket restriction that prevented drones from spawning
> any subagents, *we decided* to replace the tier-based tool filter with a
> depth-based limit (`@max_depth 3`), where each spawned drone inherits
> `depth: parent.depth + 1` and loses `spawn_agent` only when it reaches max
> depth, *to achieve* recursive divide-and-conquer without infinite nesting,
> *accepting* that deep chains increase latency and token cost, and `create_tool`
> remains restricted to minds only.

**Consequences:**
- Minds start at depth 0; drones at depth 1, sub-drones at depth 2, etc.
- `spawn_agent` is available to any agent whose depth < `@max_depth` (3).
- `create_tool` remains mind-only — drones at any depth cannot create tools.
- The `tools_for_tier/2` function is replaced by `tools_for_agent/2` which checks both tier and depth.
- Max depth is a module attribute (`@max_depth`) for easy tuning.
