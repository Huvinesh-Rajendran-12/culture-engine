<script lang="ts">
  import type { MemoryEntry } from "../lib/types";
  import { api } from "../lib/api";
  import {
    prettyDate,
    buildMemoryCategories,
    filterMemories,
  } from "../lib/helpers";

  let {
    mindId = "",
    memories = $bindable([] as MemoryEntry[]),
    contextMemoryIds = [] as string[],
    onClose,
  }: {
    mindId: string;
    memories: MemoryEntry[];
    contextMemoryIds?: string[];
    onClose: () => void;
  } = $props();

  let search = $state("");
  let category = $state("all");

  let categories = $derived(buildMemoryCategories(memories));
  let filtered = $derived(filterMemories(memories, search, category));

  async function refresh() {
    if (!mindId) return;
    try {
      memories = await api.listMemory(mindId);
    } catch { /* silent */ }
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") onClose();
  }

  function onBackdropClick(event: MouseEvent) {
    if (event.target === event.currentTarget) {
      onClose();
    }
  }

  function onBackdropKeydown(event: KeyboardEvent) {
    if (event.target !== event.currentTarget) return;
    if (event.key === "Escape" || event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onClose();
    }
  }
</script>

<svelte:window on:keydown={onKeydown} />

<div
  class="vault-backdrop"
  role="button"
  tabindex="0"
  onclick={onBackdropClick}
  onkeydown={onBackdropKeydown}
>
  <aside class="vault-drawer">
    <div class="vault-header">
      <h2 class="vault-title">
        <span class="vault-glyph">{"\u2B21"}</span> Memory Vault
      </h2>
      <button type="button" class="vault-close" onclick={onClose}>{"\u00D7"}</button>
    </div>

    <div class="vault-search">
      <label class="field field-compact">
        <span class="field-label">Category</span>
        <select bind:value={category}>
          {#each categories as cat (cat)}
            <option value={cat}>{cat}</option>
          {/each}
        </select>
      </label>

      <label class="field field-grow">
        <span class="field-label">Search</span>
        <input bind:value={search} placeholder="Filter by content or keyword" />
      </label>

      <button type="button" class="btn-ghost" onclick={refresh}>Refresh</button>
    </div>

    <div class="vault-count">
      {#if filtered.length !== memories.length}
        <span>{filtered.length} / {memories.length} entries</span>
      {:else}
        <span>{memories.length} entries</span>
      {/if}
    </div>

    <div class="vault-list">
      {#if filtered.length === 0}
        <span class="muted">No memories match the current filters.</span>
      {:else}
        {#each filtered as memory (memory.id)}
          <article class="memory-card" data-context-hit={contextMemoryIds.includes(memory.id)}>
            <div class="memory-head">
              <span class="memory-id">{memory.id}</span>
              <span class="memory-time">{prettyDate(memory.created_at)}</span>
            </div>
            <p class="memory-content">{memory.content}</p>
            <div class="chip-row">
              <span class="chip">{memory.category || "uncategorized"}</span>
              {#each memory.relevance_keywords as kw (kw)}
                <span class="chip keyword">{kw}</span>
              {/each}
            </div>
          </article>
        {/each}
      {/if}
    </div>
  </aside>
</div>

<style>
  .vault-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(2px);
    z-index: 500;
    display: flex;
    justify-content: flex-end;
    animation: fade-in 200ms ease-out;
  }

  @keyframes fade-in {
    from { opacity: 0; }
    to   { opacity: 1; }
  }

  .vault-drawer {
    width: 420px;
    max-width: 90vw;
    height: 100%;
    background: var(--bg-panel, #131522);
    border-left: 1px solid var(--gold-border, rgba(191, 143, 59, 0.3));
    box-shadow: -12px 0 60px rgba(0, 0, 0, 0.6);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    animation: drawer-slide 280ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  @keyframes drawer-slide {
    from { transform: translateX(100%); }
    to   { transform: translateX(0); }
  }

  .vault-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 18px 20px;
    border-bottom: 1px solid rgba(191, 143, 59, 0.14);
    flex-shrink: 0;
  }

  .vault-title {
    font-family: var(--font-heading);
    font-size: 0.76rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--gold);
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .vault-glyph { opacity: 0.65; }

  .vault-close {
    font-size: 1.4rem;
    color: var(--ink-3);
    padding: 4px 8px;
    line-height: 1;
    transition: color 150ms;
  }
  .vault-close:hover { color: var(--ink-1); }

  .vault-search {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: flex-end;
    padding: 14px 20px 0;
    flex-shrink: 0;
  }

  .field { display: flex; flex-direction: column; gap: 5px; }
  .field-compact { min-width: 120px; flex-shrink: 0; }
  .field-grow { flex: 1; min-width: 140px; }

  .field-label {
    font-family: var(--font-heading);
    font-size: 0.58rem;
    letter-spacing: 0.11em;
    text-transform: uppercase;
    color: var(--ink-2);
  }

  input, select {
    border: 1px solid rgba(191, 143, 59, 0.22);
    border-radius: var(--radius, 8px);
    color: var(--ink-1);
    background: rgba(5, 6, 12, 0.9);
    padding: 7px 9px;
    outline: none;
    font: inherit;
    font-size: 0.85rem;
    width: 100%;
  }
  input:focus, select:focus {
    border-color: rgba(229, 169, 58, 0.6);
    box-shadow: 0 0 0 3px rgba(229, 169, 58, 0.11);
  }

  .btn-ghost {
    border: 1px solid rgba(191, 143, 59, 0.28);
    color: #d9ba83;
    background: rgba(191, 143, 59, 0.08);
    padding: 7px 12px;
    border-radius: var(--radius, 8px);
    font-size: 0.74rem;
    align-self: flex-end;
    transition: background 140ms;
  }
  .btn-ghost:hover { background: rgba(191, 143, 59, 0.16); }

  .vault-count {
    padding: 8px 20px 0;
    font-family: var(--font-mono);
    font-size: 0.64rem;
    color: var(--ink-3);
    flex-shrink: 0;
  }

  .vault-list {
    flex: 1;
    overflow-y: auto;
    padding: 12px 20px 20px;
    scrollbar-width: thin;
    scrollbar-color: rgba(191, 143, 59, 0.28) transparent;
  }

  .muted {
    color: var(--ink-3);
    font-size: 0.88rem;
    font-style: italic;
    padding: 12px;
    text-align: center;
    display: block;
  }

  .memory-card {
    border: 1px solid rgba(191, 143, 59, 0.17);
    border-radius: var(--radius, 8px);
    padding: 12px;
    margin-bottom: 8px;
    background: rgba(7, 9, 17, 0.82);
    transition: border-color 200ms;
  }
  .memory-card:last-child { margin-bottom: 0; }

  @keyframes context-hit-glow {
    0%   { box-shadow: none; border-color: rgba(191, 143, 59, 0.17); }
    20%  { box-shadow: 0 0 30px 6px rgba(107, 191, 142, 0.42); border-color: rgba(107, 191, 142, 0.82); }
    100% { box-shadow: 0 0 10px 2px rgba(107, 191, 142, 0.16); border-color: rgba(107, 191, 142, 0.4); }
  }
  .memory-card[data-context-hit="true"] {
    animation: context-hit-glow 2.2s ease-out forwards;
  }

  .memory-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }
  .memory-id { font-family: var(--font-mono); font-size: 0.66rem; color: var(--gold-mid); }
  .memory-time { font-family: var(--font-mono); font-size: 0.61rem; color: var(--ink-3); }

  .memory-content {
    color: var(--ink-2);
    font-size: 0.94rem;
    white-space: pre-wrap;
    margin-bottom: 8px;
  }

  .chip-row { display: flex; flex-wrap: wrap; gap: 6px; }
  .chip {
    font-family: var(--font-mono);
    font-size: 0.66rem;
    padding: 2px 8px;
    border-radius: 999px;
    border: 1px solid rgba(191, 143, 59, 0.3);
    background: rgba(191, 143, 59, 0.1);
    color: #dfb971;
    line-height: 1.45;
  }
  .chip.keyword {
    color: #9ac3e5;
    border-color: rgba(110, 169, 216, 0.32);
    background: rgba(110, 169, 216, 0.1);
  }
</style>
