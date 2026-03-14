# Autonomy Improvements Plan

Addressing 4 bottlenecks that limit Mind/Drone effectiveness for complex analytical tasks.

---

## Phase 1: Higher Defaults + Configurable Limits

**Files:** `agent.ex`, `run_command.ex`, `script_runner.ex`

**Problem:** Hardcoded limits are too restrictive. Drone gets 5 turns (one complex
analysis can exhaust this), commands timeout at 30s, output caps at 50KB.

**Changes:**

| Limit | Current | New Default |
|---|---|---|
| Drone `max_turns` | 5 | 15 |
| Mind `max_turns` | 20 | 50 |
| `RunCommand` timeout | 30s | 120s |
| `ScriptRunner` timeout | 30s | 120s |
| `max_output_bytes` | 50KB | 200KB |

Additionally:
- `run_command` tool gains an optional `timeout` input param (capped at 300s)
- `ScriptRunner.run/2` becomes `run/3` accepting an optional `timeout` keyword

**Complexity:** Low — constant changes + one optional param.

---

## Phase 2: Continuation Protocol (Partial Results on Turn Limit)

**Files:** `agent.ex`, `prompts.ex`

**Problem:** When a drone hits max_turns, it returns `{:error, "Max turns reached"}`.
All intermediate reasoning and partial results are lost. The Mind gets nothing useful.

**Design:** Instead of hard-stopping, the agent makes one final "wrap-up" API call:

```
┌─────────────────────────────────────────────┐
│ Drone hits turn limit                       │
│                                             │
│ Instead of {:error, "Max turns reached"}:   │
│                                             │
│ 1. Inject a user message:                   │
│    "You have reached your turn limit.       │
│     Summarize all findings and progress     │
│     so far. Do NOT use any tools."          │
│                                             │
│ 2. Make one final API call (no tools)       │
│                                             │
│ 3. Return {:ok, summary} with a            │
│    "[partial]" prefix so the Mind knows     │
│    the drone didn't finish                  │
│                                             │
│ 4. Mind can re-dispatch with context        │
│    if needed                                │
└─────────────────────────────────────────────┘
```

**Key detail:** The final API call passes `tools: []` so the model *must* respond
with text only — no risk of infinite loops.

**Complexity:** Low — ~15 lines in `run_loop/3`.

---

## Phase 3: Resource Budget Passthrough

**Files:** `spawn_agent.ex`, `agent.ex`

**Problem:** The Mind can set `max_turns` on a drone, but can't control timeouts
or output limits. Every drone gets identical resource constraints.

**Design:** Extend `spawn_agent` input schema with optional resource fields:

```json
{
  "task": "Analyze all log files in /var/log",
  "max_turns": 25,
  "tool_timeout": 180,
  "max_output_bytes": 500000
}
```

These flow into the drone's agent state as a `resources` map:

```elixir
# In agent.ex struct
defstruct [
  ...
  resources: %{
    tool_timeout: 120_000,    # ms — passed to ScriptRunner/RunCommand
    max_output_bytes: 200_000
  }
]
```

Tools that need these values read them from state (for stateful tools like
`run_command`) or receive them as params (for stateless tools via `execute/2`).

**Key constraint:** The Tool behaviour currently defines `execute(input)` — we need
to extend this to `execute(input, opts \\ [])` so tools can receive resource config
without breaking existing tools.

**Complexity:** Medium — touches the Tool behaviour and several tool implementations.

---

## Phase 4: Drone System Prompt Enhancement

**Files:** `prompts.ex`

**Problem:** Drone prompt doesn't instruct the agent to preserve incremental progress
or manage its turn budget wisely.

**Changes to drone prompt:**
- Instruct the drone to work incrementally and summarize findings as it goes
- Tell it how many turns it has and to prioritize the most important work first
- Tell it that if time runs short, partial results are valuable

**Changes to mind prompt:**
- Tell the Mind about the continuation protocol
- Instruct it to give drones generous turn budgets for analytical tasks
- Remind it that drone partial results can be continued by re-dispatching

**Complexity:** Low — prompt text only.

---

## Implementation Order

```
Phase 1 (Higher Defaults)          — standalone, no dependencies
Phase 2 (Continuation Protocol)    — standalone, no dependencies
Phase 3 (Resource Budget)          — depends on Phase 1 for timeout/output plumbing
Phase 4 (Prompt Enhancement)       — depends on Phase 2 for continuation awareness
```

Phases 1 and 2 can be done in parallel. Phase 3 builds on 1. Phase 4 builds on 2.

---

## What We're NOT Doing

Per the simplification rules in AGENTS.md:
- No persistence/checkpointing system — the continuation protocol is simpler
- No token budget tracking — keep it turn-based
- No auto-retry/auto-continue — the Mind decides whether to re-dispatch
- No priority queues or scheduling — KISS
