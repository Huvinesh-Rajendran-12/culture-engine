<script lang="ts">
  import type { EventView } from "../lib/types";
  import { prettyDate } from "../lib/helpers";

  let {
    event,
    expanded = false,
    onToggleExpand,
  }: {
    event: EventView;
    expanded?: boolean;
    onToggleExpand?: (id: string) => void;
  } = $props();

  let isLong = $derived(event.fullDetail.length > 260);
</script>

<article class="event-row" data-severity={event.severity}>
  <div class="event-header">
    <span class="event-type-tag">{event.type}</span>
    {#if event.timestamp}
      <span class="event-time">{prettyDate(event.timestamp)}</span>
    {/if}
  </div>
  <strong class="event-title">{event.title}</strong>
  <p class="event-detail" class:clamped={isLong && !expanded}>
    {expanded ? event.fullDetail : event.detail}
  </p>
  {#if isLong && onToggleExpand}
    <button type="button" class="event-expand" onclick={() => onToggleExpand?.(event.id)}>
      {expanded ? "\u25B2 collapse" : "\u25BC show more"}
    </button>
  {/if}
</article>

<style>
  .event-row {
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-left: 3px solid rgba(110, 169, 216, 0.35);
    border-radius: 6px;
    background: rgba(9, 11, 20, 0.82);
    padding: 9px 10px 9px 12px;
    margin-bottom: 7px;
    animation: event-rise 200ms ease-out;
  }
  .event-row:last-child { margin-bottom: 0; }

  @keyframes event-rise {
    from { opacity: 0; transform: translateY(4px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  .event-row[data-severity="info"]    { border-left-color: rgba(110, 169, 216, 0.55); }
  .event-row[data-severity="success"] { border-left-color: rgba(107, 191, 142, 0.8); background: rgba(6, 18, 12, 0.78); }
  .event-row[data-severity="warn"]    { border-left-color: rgba(229, 169, 58, 0.8); background: rgba(18, 12, 4, 0.78); }
  .event-row[data-severity="error"]   { border-left-color: rgba(204, 90, 90, 0.9); background: rgba(20, 6, 6, 0.82); }

  .event-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    margin-bottom: 3px;
  }

  .event-type-tag {
    font-family: var(--font-mono);
    font-size: 0.62rem;
    color: var(--ink-3);
    background: rgba(255, 255, 255, 0.05);
    padding: 1px 6px;
    border-radius: 4px;
  }

  .event-time {
    font-family: var(--font-mono);
    font-size: 0.6rem;
    color: var(--ink-3);
    flex-shrink: 0;
  }

  .event-title {
    display: block;
    color: var(--ink-1);
    font-size: 0.9rem;
    margin-bottom: 3px;
  }

  .event-detail {
    color: var(--ink-2);
    font-family: var(--font-mono);
    font-size: 0.72rem;
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.45;
  }

  .event-detail.clamped {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .event-expand {
    font-family: var(--font-mono);
    font-size: 0.6rem;
    color: var(--gold-mid);
    margin-top: 4px;
    padding: 0;
    opacity: 0.75;
    text-decoration: underline;
    display: block;
  }
  .event-expand:hover { opacity: 1; }
</style>
