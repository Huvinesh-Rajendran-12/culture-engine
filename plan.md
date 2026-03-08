# Drone UI Improvements Plan

## Current State

The REPL (`repl_live.ex`) is a flat linear chat stream. When a Mind spawns a drone, it appears as generic `tool_use` / `tool_result` messages — no different from `read_file` or `run_command`. There's **zero visibility** into what drones are doing while they work, and no visual hierarchy showing the Mind→Drone relationship. The Observatory exists on a separate page but also has a flat agent list with no tree structure.

## Goals

1. Make drone activity **visible inline** in the Mind's REPL conversation
2. Show clear **visual hierarchy** — Mind vs Drone(s) with nesting
3. Stream drone events **in real-time** so the user sees what drones are doing
4. Support **multiple concurrent async drones** with distinct visual panels
5. Keep the design consistent with the existing dark theme (GitHub Dark aesthetic)

---

## Plan

### Phase 1: Backend — Subscribe to Drone Events in ReplLive

**File:** `repl_live.ex`

- When we receive a `tool_use` event for `spawn_agent`, extract the drone ID from the subsequent `tool_result` or from PubSub lifecycle events
- Subscribe ReplLive to the `"agents"` global topic to catch `{:agent_started, %{id, name, tier, parent}}` events
- When a drone starts whose parent matches our Mind's PID, subscribe to `"agent:#{drone_id}"` to stream its events
- Track active drones in socket assigns: `drones: %{drone_id => %{name, status, events, collapsed}}`
- Handle drone events (`{:agent_event, event}`) and append them to the drone's event list
- Handle `{:agent_stopped, ...}` to mark drone as completed
- On drone `:done`, mark status as `:complete`

### Phase 2: Frontend — Drone Panel Component

**File:** `repl_live.ex` (render function) + `layouts.ex` (CSS)

Replace the flat `tool_use`/`tool_result` for `spawn_agent` with an **inline collapsible drone panel**:

```
┌─────────────────────────────────────────────────────┐
│ ◆ DRONE  "Quietly Considering Ambiguity"   [▼]     │
│   Task: "Search for all config files"               │
│ ┌─────────────────────────────────────────────────┐ │
│ │ [tool] search_files: %{pattern: "*.config"}     │ │
│ │ [result] search_files: Found 3 files...         │ │
│ │ [tool] read_file: %{path: "config/prod.exs"}   │ │
│ │ [result] read_file: use Config\nconfig :app...  │ │
│ │ thinking...                                     │ │
│ └─────────────────────────────────────────────────┘ │
│   ● Running                                         │
└─────────────────────────────────────────────────────┘
```

Key elements:
- **Purple accent** border/header (matching existing `.tier-badge.drone` color `#d2a8ff`)
- **Collapsible** — click header to expand/collapse drone event stream
- **Status indicator** — spinning/pulsing dot while running, checkmark when done, X on error
- **Drone name** prominently displayed (Culture-style ship name)
- **Task description** shown below the header
- **Nested event stream** — same formatting as main REPL but indented/contained
- **Auto-collapse on completion** — once done, collapse to single summary line

### Phase 3: CSS Additions

**File:** `layouts.ex` (inline `<style>` block)

New CSS classes:
- `.drone-panel` — container with purple left border, dark background
- `.drone-header` — clickable header row with name, status, collapse toggle
- `.drone-events` — scrollable inner container for drone's event stream
- `.drone-status` — status badge (running/complete/error)
- `.drone-panel.collapsed` — collapsed state showing only header + final result summary
- Animations: slide-open for expand, fade-in for new drone events

### Phase 4: Multiple Drone Support

- Each drone gets its own panel, rendered inline at the position where `spawn_agent` was called
- For async drones, show panels in a sidebar/bottom dock area since they run in parallel
- Track drone ordering to maintain visual consistency
- Message list entries gain a new role: `:drone_spawn` with metadata `%{drone_id, name, task}`
- The render function checks if a message is `:drone_spawn` and renders the drone panel component instead of a text message

### Phase 5: Header Enhancement

**File:** `repl_live.ex` (render function)

Enhance the Mind header to show active drone count:
```
┌──────────────────────────────────────────┐
│ ◈ Sleeper Service           MIND         │
│   2 drones active                        │
└──────────────────────────────────────────┘
```

### Phase 6: Observatory Upgrade (Stretch)

- Convert flat agent list to a **tree view** showing Mind→Drone hierarchy
- Group drones under their parent Mind
- Show connecting lines for parent-child relationships

---

## Implementation Order

1. **Phase 1** — Backend subscriptions + drone state tracking in assigns
2. **Phase 3** — CSS classes (needed before rendering)
3. **Phase 2** — Drone panel rendering
4. **Phase 4** — Multiple drone + message integration
5. **Phase 5** — Header enhancement
6. **Phase 6** — Observatory tree (stretch goal)

## Files Modified

| File | Changes |
|------|---------|
| `repl_live.ex` | PubSub subscriptions, drone state tracking, drone panel rendering, header update |
| `layouts.ex` | New CSS classes for drone panels, animations, status indicators |
| `observatory_live.ex` | Tree view hierarchy (Phase 6 / stretch) |
