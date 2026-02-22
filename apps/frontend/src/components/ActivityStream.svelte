<script lang="ts">
  import EventRow from "./EventRow.svelte";
  import OutputFeed from "./OutputFeed.svelte";
  import type { EventView, OutputItem } from "../lib/types";

  let {
    outputItems = [] as OutputItem[],
    events = [] as EventView[],
    busy = false,
    liveTypingText = "",
    status = "idle",
  }: {
    outputItems?: OutputItem[];
    events?: EventView[];
    busy?: boolean;
    liveTypingText?: string;
    status?: string;
  } = $props();

  let mode = $state<"output" | "events">("output");
  let expandedEvents = $state<Set<string>>(new Set());

  let hasActivity = $derived(outputItems.length > 0 || events.length > 0 || busy);

  function toggleExpand(id: string): void {
    const next = new Set(expandedEvents);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    expandedEvents = next;
  }
</script>

<section class="activity-stream" data-open={hasActivity}>
  <div class="stream-header">
    <span class="stream-title">Activity Stream</span>
    <div class="stream-controls">
      <button
        type="button"
        class="stream-mode"
        class:active={mode === "output"}
        onclick={() => (mode = "output")}
      >
        Output
      </button>
      <button
        type="button"
        class="stream-mode"
        class:active={mode === "events"}
        onclick={() => (mode = "events")}
      >
        Trace
      </button>
      <span class="stream-status" data-status={status}>{status}</span>
    </div>
  </div>

  {#if mode === "output"}
    <OutputFeed items={outputItems} {busy} {liveTypingText} {status} />
  {:else}
    <div class="events-pane">
      {#if events.length === 0}
        <span class="events-empty">No telemetry yet.</span>
      {:else}
        {#each events as event (event.id)}
          <EventRow
            {event}
            expanded={expandedEvents.has(event.id)}
            onToggleExpand={toggleExpand}
          />
        {/each}
      {/if}
    </div>
  {/if}
</section>

<style>
  .activity-stream {
    width: min(760px, 94vw);
    margin-top: 16px;
    border-radius: 14px;
    border: 1px solid rgba(232, 175, 71, 0.2);
    background:
      linear-gradient(160deg, rgba(13, 17, 30, 0.92), rgba(7, 9, 18, 0.94));
    box-shadow:
      0 20px 60px rgba(0, 0, 0, 0.48),
      inset 0 1px 0 rgba(255, 255, 255, 0.03);
    overflow: hidden;
    transition: opacity 180ms ease, transform 180ms ease;
  }

  .activity-stream[data-open="false"] {
    opacity: 0.88;
  }

  .stream-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    border-bottom: 1px solid rgba(232, 175, 71, 0.13);
    background: rgba(232, 175, 71, 0.05);
  }

  .stream-title {
    font-family: var(--font-heading);
    font-size: 0.6rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--gold);
  }

  .stream-controls {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .stream-mode {
    border-radius: 999px;
    border: 1px solid rgba(232, 175, 71, 0.2);
    background: rgba(232, 175, 71, 0.07);
    color: var(--ink-2);
    padding: 3px 10px;
    font-family: var(--font-mono);
    font-size: 0.64rem;
    letter-spacing: 0.04em;
    transition: background 140ms, color 140ms;
  }

  .stream-mode.active {
    color: #fef2d2;
    background: rgba(232, 175, 71, 0.22);
  }

  .stream-status {
    font-family: var(--font-mono);
    text-transform: uppercase;
    font-size: 0.58rem;
    letter-spacing: 0.08em;
    color: var(--ink-3);
    margin-left: 4px;
  }

  .stream-status[data-status="completed"] { color: #7fc8a1; }
  .stream-status[data-status="failed"],
  .stream-status[data-status="error"] { color: #d97d7d; }
  .stream-status[data-status="running"] { color: #87b6e6; }

  .events-pane {
    max-height: 360px;
    overflow-y: auto;
    padding: 10px;
    scrollbar-width: thin;
    scrollbar-color: rgba(191, 143, 59, 0.28) transparent;
  }

  .events-empty {
    color: var(--ink-3);
    font-size: 0.84rem;
    font-style: italic;
    display: block;
    text-align: center;
    padding: 20px 10px;
  }

  @media (max-width: 960px) {
    .activity-stream {
      width: min(680px, 94vw);
    }
  }

  @media (max-width: 700px) {
    .activity-stream {
      width: 100%;
      margin-top: 10px;
    }

    .stream-header {
      flex-direction: column;
      align-items: flex-start;
    }
  }
</style>
