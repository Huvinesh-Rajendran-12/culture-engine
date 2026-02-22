<script lang="ts">
  import type { Mind } from "../lib/types";

  let {
    minds = $bindable([] as Mind[]),
    selectedMindId = $bindable(""),
    busy = false,
    onOpenProfile,
    onOpenCreate,
  }: {
    minds: Mind[];
    selectedMindId: string;
    busy?: boolean;
    onOpenProfile?: () => void;
    onOpenCreate?: () => void;
  } = $props();

  let selectedMind = $derived(minds.find((m) => m.id === selectedMindId) ?? null);
</script>

<div class="mind-selector">
  <div class="selector-row">
    <div class="brand">
      <span class="brand-glyph" aria-hidden="true">{"\u2B21"}</span>
      <span class="brand-text">Culture Engine</span>
    </div>

    <div class="selector-controls">
      <select bind:value={selectedMindId} class="mind-select">
        <option value="">Select a Mind</option>
        {#each minds as mind (mind.id)}
          <option value={mind.id}>{mind.name}</option>
        {/each}
      </select>

      {#if selectedMind && onOpenProfile}
        <button type="button" class="selector-btn" onclick={onOpenProfile} title="Edit Mind profile">
          {"\u25C9"}
        </button>
      {/if}

      {#if onOpenCreate}
        <button type="button" class="selector-btn selector-btn-create" onclick={onOpenCreate} title="Create new Mind">
          +
        </button>
      {/if}
    </div>
  </div>

  {#if busy}
    <div class="selector-live">
      <span class="live-orb"></span>
      <span class="live-text">Mind running</span>
    </div>
  {/if}
</div>

<style>
  .mind-selector {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 12px 20px;
  }

  .selector-row {
    display: flex;
    align-items: center;
    gap: 20px;
    flex: 1;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .brand-glyph {
    font-size: 1.3rem;
    color: var(--gold);
    filter: drop-shadow(0 0 10px rgba(229, 169, 58, 0.55));
    line-height: 1;
  }

  .brand-text {
    font-family: var(--font-display);
    font-size: 0.68rem;
    letter-spacing: 0.15em;
    color: var(--gold);
    text-transform: uppercase;
  }

  .selector-controls {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .mind-select {
    min-width: 160px;
    padding: 6px 10px;
    border: 1px solid rgba(191, 143, 59, 0.22);
    border-radius: var(--radius, 8px);
    color: var(--ink-1);
    background: rgba(5, 6, 12, 0.9);
    font-size: 0.85rem;
    cursor: pointer;
  }
  .mind-select:focus {
    border-color: rgba(229, 169, 58, 0.6);
    box-shadow: 0 0 0 3px rgba(229, 169, 58, 0.11);
    outline: none;
  }

  .selector-btn {
    width: 32px;
    height: 32px;
    border-radius: var(--radius, 8px);
    border: 1px solid rgba(191, 143, 59, 0.22);
    background: rgba(191, 143, 59, 0.08);
    color: var(--gold-mid);
    font-size: 0.9rem;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 140ms, border-color 140ms;
  }
  .selector-btn:hover {
    background: rgba(191, 143, 59, 0.16);
    border-color: rgba(191, 143, 59, 0.5);
  }

  .selector-btn-create {
    font-size: 1.2rem;
    font-weight: 600;
  }

  .selector-live {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .live-orb {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--gold);
    box-shadow: 0 0 6px var(--gold);
    animation: orb-pulse 1.6s ease-in-out infinite;
  }

  @keyframes orb-pulse {
    0%, 100% { transform: scale(1); }
    50%      { transform: scale(1.4); box-shadow: 0 0 16px var(--gold); }
  }

  .live-text {
    font-family: var(--font-heading);
    font-size: 0.62rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--gold);
  }
</style>
