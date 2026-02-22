<script lang="ts">
  import type { Task, TaskTrace, EventView, Drone } from "../lib/types";
  import { api } from "../lib/api";
  import { prettyDate, toEventView, compact } from "../lib/helpers";
  import EventRow from "./EventRow.svelte";

  let {
    task,
    mindId = "",
    onClose,
  }: {
    task: Task;
    mindId: string;
    onClose: () => void;
  } = $props();

  let trace = $state<TaskTrace | null>(null);
  let drones = $state<Drone[]>([]);
  let loading = $state(true);
  let expandedEvents = $state<Set<string>>(new Set());
  let viewMode = $state<"output" | "debug">("output");

  let traceEventViews = $derived(
    (trace?.events ?? []).filter((e) => e.type !== "text_delta").map((e, i) => toEventView(e, i))
  );

  $effect(() => {
    void loadData();
  });

  async function loadData() {
    loading = true;
    try {
      const [t, d] = await Promise.all([
        api.getTrace(mindId, task.id),
        fetch(`/api/minds/${mindId}/tasks/${task.id}/drones`).then((r) =>
          r.ok ? r.json() : []
        ),
      ]);
      trace = t;
      drones = d;
    } catch { /* silent */ } finally {
      loading = false;
    }
  }

  function toggleExpand(id: string) {
    const next = new Set(expandedEvents);
    if (next.has(id)) next.delete(id); else next.add(id);
    expandedEvents = next;
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") onClose();
  }
</script>

<svelte:window on:keydown={onKeydown} />

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="modal-backdrop" onclick={onClose} onkeydown={onKeydown}>
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="modal-content"
    onclick={(event) => event.stopPropagation()}
    onkeydown={(event) => event.stopPropagation()}
  >
    <div class="modal-header">
      <div>
        <h2 class="modal-title">Task Detail</h2>
        <span class="modal-task-id">{task.id}</span>
      </div>
      <button type="button" class="modal-close" onclick={onClose}>\u00D7</button>
    </div>

    <div class="task-info">
      <div class="task-status" data-status={task.status}>{task.status}</div>
      <p class="task-desc">{task.description}</p>
      <div class="task-times">
        <span>Created: {prettyDate(task.created_at)}</span>
        <span>Completed: {prettyDate(task.completed_at)}</span>
      </div>
    </div>

    {#if task.result}
      <div class="result-section">
        <h3 class="section-label">Result</h3>
        <div class="result-block">
          <p class="result-text">{task.result}</p>
        </div>
      </div>
    {/if}

    {#if drones.length > 0}
      <div class="drones-section">
        <h3 class="section-label">Drones ({drones.length})</h3>
        {#each drones as drone (drone.id)}
          <div class="drone-card" data-status={drone.status}>
            <div class="drone-head">
              <span class="drone-status">{drone.status}</span>
              <span class="drone-id">{drone.id}</span>
            </div>
            <p class="drone-objective">{drone.objective}</p>
            {#if drone.result}
              <p class="drone-result">{compact(drone.result, 200)}</p>
            {/if}
          </div>
        {/each}
      </div>
    {/if}

    {#if loading}
      <div class="loading">Loading trace...</div>
    {:else if trace}
      <div class="trace-section">
        <div class="trace-header">
          <h3 class="section-label">Trace ({traceEventViews.length} events)</h3>
          <button
            type="button"
            class="toggle-btn"
            onclick={() => (viewMode = viewMode === "output" ? "debug" : "output")}
          >
            {viewMode === "output" ? "Show raw" : "Show output"}
          </button>
        </div>

        <div class="trace-list">
          {#if viewMode === "output"}
            {@const textEvents = traceEventViews.filter((e) => e.type === "text")}
            {#if textEvents.length > 0}
              {#each textEvents as item (item.id)}
                <div class="output-text-block">
                  <p class="output-text">{item.fullDetail}</p>
                </div>
              {/each}
            {:else}
              <span class="muted">No text output captured.</span>
            {/if}
          {:else}
            {#each traceEventViews as item (item.id)}
              <EventRow
                event={item}
                expanded={expandedEvents.has(`t-${item.id}`)}
                onToggleExpand={(id) => toggleExpand(`t-${id}`)}
              />
            {/each}
          {/if}
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(4px);
    z-index: 500;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    animation: fade-in 200ms ease-out;
  }

  @keyframes fade-in {
    from { opacity: 0; }
    to   { opacity: 1; }
  }

  .modal-content {
    background: var(--bg-panel, #131522);
    border: 1px solid var(--gold-border, rgba(191, 143, 59, 0.3));
    border-radius: var(--radius-lg, 12px);
    padding: 24px;
    max-width: 720px;
    width: 100%;
    max-height: 85vh;
    overflow-y: auto;
    box-shadow: 0 24px 80px rgba(0, 0, 0, 0.7);
    animation: modal-enter 250ms ease-out;
    scrollbar-width: thin;
    scrollbar-color: rgba(191, 143, 59, 0.28) transparent;
  }

  @keyframes modal-enter {
    from { opacity: 0; transform: scale(0.95) translateY(10px); }
    to   { opacity: 1; transform: scale(1) translateY(0); }
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;
  }

  .modal-title {
    font-family: var(--font-heading);
    font-size: 0.78rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--gold);
    margin-bottom: 4px;
  }

  .modal-task-id {
    font-family: var(--font-mono);
    font-size: 0.62rem;
    color: var(--ink-3);
  }

  .modal-close {
    font-size: 1.4rem;
    color: var(--ink-3);
    padding: 4px 8px;
    line-height: 1;
    transition: color 150ms;
  }
  .modal-close:hover { color: var(--ink-1); }

  .task-info { margin-bottom: 16px; }

  .task-status {
    font-family: var(--font-heading);
    font-size: 0.56rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 2px 8px;
    border-radius: 999px;
    border: 1px solid rgba(191, 143, 59, 0.38);
    color: #f4cb7d;
    background: rgba(191, 143, 59, 0.13);
    display: inline-block;
    margin-bottom: 8px;
  }
  .task-status[data-status="completed"] { border-color: rgba(107, 191, 142, 0.48); color: #8de2b0; background: rgba(107, 191, 142, 0.11); }
  .task-status[data-status="running"], .task-status[data-status="in_progress"] { border-color: rgba(110, 169, 216, 0.48); color: #9ac7eb; background: rgba(110, 169, 216, 0.12); }
  .task-status[data-status="failed"], .task-status[data-status="error"] { border-color: rgba(204, 90, 90, 0.52); color: #ffafaf; background: rgba(204, 90, 90, 0.12); }

  .task-desc { color: var(--ink-1); font-size: 1rem; margin-bottom: 8px; }

  .task-times {
    font-family: var(--font-mono);
    font-size: 0.62rem;
    color: var(--ink-3);
    display: flex;
    gap: 16px;
  }

  .section-label {
    font-family: var(--font-heading);
    font-size: 0.66rem;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: var(--gold-mid);
    margin-bottom: 10px;
  }

  .result-section { margin-bottom: 16px; }
  .result-block {
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: var(--radius, 8px);
    background: rgba(8, 10, 20, 0.88);
    padding: 14px 16px;
  }
  .result-text {
    font-family: var(--font-body);
    font-size: 0.98rem;
    line-height: 1.7;
    color: var(--ink-1);
    white-space: pre-wrap;
    word-break: break-word;
  }

  .drones-section { margin-bottom: 16px; }
  .drone-card {
    border: 1px solid rgba(110, 169, 216, 0.2);
    border-left: 3px solid rgba(110, 169, 216, 0.5);
    border-radius: var(--radius, 8px);
    background: rgba(5, 12, 22, 0.84);
    padding: 10px 12px;
    margin-bottom: 8px;
  }
  .drone-card[data-status="failed"] { border-left-color: rgba(204, 90, 90, 0.7); }
  .drone-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
  .drone-status {
    font-family: var(--font-heading);
    font-size: 0.56rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--sky, #6ea9d8);
  }
  .drone-id { font-family: var(--font-mono); font-size: 0.6rem; color: var(--ink-3); }
  .drone-objective { color: var(--ink-2); font-size: 0.9rem; margin-bottom: 4px; }
  .drone-result {
    font-family: var(--font-mono);
    font-size: 0.71rem;
    color: var(--ink-3);
    background: rgba(0, 0, 0, 0.3);
    border-radius: 4px;
    padding: 6px 8px;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .trace-section { margin-top: 8px; }
  .trace-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
  .toggle-btn {
    font-family: var(--font-mono);
    font-size: 0.64rem;
    color: var(--gold-mid);
    border: 1px solid rgba(191, 143, 59, 0.22);
    background: rgba(191, 143, 59, 0.08);
    padding: 4px 10px;
    border-radius: var(--radius, 8px);
    transition: background 140ms;
  }
  .toggle-btn:hover { background: rgba(191, 143, 59, 0.16); }

  .trace-list {
    max-height: 320px;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: rgba(191, 143, 59, 0.28) transparent;
  }

  .output-text-block {
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: var(--radius, 8px);
    background: rgba(8, 10, 20, 0.88);
    padding: 14px 16px;
    margin-bottom: 8px;
  }
  .output-text {
    font-family: var(--font-body);
    font-size: 0.98rem;
    line-height: 1.7;
    color: var(--ink-1);
    white-space: pre-wrap;
    word-break: break-word;
  }

  .loading {
    font-family: var(--font-heading);
    font-size: 0.68rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--gold-dim);
    text-align: center;
    padding: 24px;
  }

  .muted {
    color: var(--ink-3);
    font-size: 0.88rem;
    font-style: italic;
    padding: 12px;
    text-align: center;
    display: block;
  }
</style>
