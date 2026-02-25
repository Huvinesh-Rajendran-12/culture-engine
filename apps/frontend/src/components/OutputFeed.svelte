<script lang="ts">
  import type { OutputItem } from "../lib/types";
  import { toolLabel } from "../lib/helpers";

  let {
    items = [] as OutputItem[],
    busy = false,
    liveTypingText = "",
    status = "idle",
  }: {
    items: OutputItem[];
    busy?: boolean;
    liveTypingText?: string;
    status?: string;
  } = $props();
</script>

<div class="output-feed">
  {#if items.length === 0 && !busy}
    <span class="muted">No output yet — run a task to see results.</span>
  {:else}
    {#each items as item, i (i)}
      {#if item.kind === "text"}
        <div class="output-text-block">
          <p class="output-text">{item.content}</p>
        </div>
      {:else if item.kind === "tool"}
        {@const tl = toolLabel(item.name)}
        <div class="activity-pill" data-status={item.status}>
          <span class="activity-glyph">{tl.glyph}</span>
          <span class="activity-label">{tl.label}</span>
          {#if item.status === "error"}
            <span class="activity-err">failed</span>
          {:else if item.status === "pending"}
            <span class="activity-pending">...</span>
          {/if}
        </div>
      {/if}
    {/each}

    {#if busy && liveTypingText}
      <div class="composing-block">
        <div class="composing-header">
          <span class="composing-dot"></span>
          <span class="composing-dot"></span>
          <span class="composing-dot"></span>
          <span class="composing-label">composing</span>
        </div>
        <p class="composing-text">{liveTypingText}</p>
      </div>
    {:else if busy}
      <div class="composing-block composing-idle">
        <div class="composing-header">
          <span class="composing-dot"></span>
          <span class="composing-dot"></span>
          <span class="composing-dot"></span>
          <span class="composing-label">working</span>
        </div>
      </div>
    {/if}
  {/if}
</div>

<style>
  .output-feed {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: 560px;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: rgba(191, 143, 59, 0.25) transparent;
    padding-right: 4px;
  }
  .output-feed::-webkit-scrollbar       { width: 4px; }
  .output-feed::-webkit-scrollbar-thumb { background: rgba(191, 143, 59, 0.25); border-radius: 2px; }

  .muted {
    color: var(--ink-3);
    font-size: 0.88rem;
    font-style: italic;
    padding: 12px;
    text-align: center;
  }

  .output-text-block {
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: var(--radius, 8px);
    background: rgba(8, 10, 20, 0.88);
    padding: 16px 18px;
    animation: event-rise 260ms ease-out;
  }

  .output-text {
    font-family: var(--font-body);
    font-size: 1.02rem;
    line-height: 1.78;
    color: var(--ink-1);
    white-space: pre-wrap;
    word-break: break-word;
  }

  @keyframes event-rise {
    from { opacity: 0; transform: translateY(4px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  .activity-pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 4px 12px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    align-self: flex-start;
    animation: event-rise 200ms ease-out;
    transition: border-color 200ms;
  }
  .activity-pill[data-status="ok"] { border-color: rgba(107, 191, 142, 0.2); }
  .activity-pill[data-status="error"] { border-color: rgba(204, 90, 90, 0.3); background: rgba(204, 90, 90, 0.06); }

  .activity-glyph { font-size: 0.78rem; color: var(--gold-mid); opacity: 0.75; line-height: 1; }
  .activity-label { font-family: var(--font-mono); font-size: 0.68rem; color: var(--ink-3); }
  .activity-err   { font-family: var(--font-mono); font-size: 0.64rem; color: var(--rose); }
  .activity-pending { font-family: var(--font-mono); font-size: 0.7rem; color: var(--gold-mid); animation: dot-pulse 1s ease-in-out infinite; }

  @keyframes dot-pulse {
    0%, 100% { opacity: 1;   transform: scale(1); }
    50%       { opacity: 0.4; transform: scale(0.65); }
  }

  .composing-block {
    border: 1px solid rgba(229, 169, 58, 0.22);
    border-left: 3px solid rgba(229, 169, 58, 0.65);
    border-radius: 6px;
    background: rgba(18, 13, 4, 0.82);
    padding: 9px 10px 9px 12px;
    margin-top: 7px;
  }
  .composing-header { display: flex; align-items: center; gap: 4px; margin-bottom: 6px; }

  .composing-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--gold);
    animation: composing-bounce 1.1s ease-in-out infinite;
  }
  .composing-dot:nth-child(2) { animation-delay: 0.18s; }
  .composing-dot:nth-child(3) { animation-delay: 0.36s; }

  @keyframes composing-bounce {
    0%, 60%, 100% { transform: translateY(0);   opacity: 0.5; }
    30%            { transform: translateY(-4px); opacity: 1; }
  }

  .composing-label {
    font-family: var(--font-heading);
    font-size: 0.6rem;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: var(--gold-mid);
    margin-left: 6px;
  }

  .composing-text {
    font-family: var(--font-mono);
    font-size: 0.73rem;
    color: var(--ink-2);
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.5;
    display: inline;
  }
  .composing-text::after {
    content: "\u258D";
    color: var(--gold);
    animation: cursor-blink 0.9s step-end infinite;
    margin-left: 1px;
  }
  @keyframes cursor-blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0; }
  }

  .composing-idle .composing-label { opacity: 0.7; }
</style>
