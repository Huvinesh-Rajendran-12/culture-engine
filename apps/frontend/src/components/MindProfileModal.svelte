<script lang="ts">
  import type { Mind } from "../lib/types";
  import { api } from "../lib/api";
  import {
    linesToList,
    listToLines,
    parsePreferencesInput,
    sortMinds,
  } from "../lib/helpers";

  let {
    mind,
    minds = $bindable([] as Mind[]),
    selectedMindId = $bindable(""),
    onClose,
    mode = "edit" as "edit" | "create",
  }: {
    mind: Mind | null;
    minds: Mind[];
    selectedMindId: string;
    onClose: () => void;
    mode?: "edit" | "create";
  } = $props();

  // Create mode fields
  let newName = $state("Atlas");
  let newPersonality = $state("Calm, pragmatic digital operator");
  let newSystemPrompt = $state("");
  let newPreferences = $state('{"tone":"direct","depth":"concise"}');

  // Edit mode fields
  let editName = $state("");
  let editPersonality = $state("");
  let editSystemPrompt = $state("");
  let editPreferences = $state("{}");
  let editMission = $state("");
  let editReasonForExistence = $state("");
  let editOperatingPrinciples = $state("");
  let editNonGoals = $state("");
  let editReflectionFocus = $state("");
  let saving = $state(false);
  let error = $state("");

  $effect(() => {
    if (mode === "edit" && mind) {
      editName = mind.name;
      editPersonality = mind.personality || "";
      editSystemPrompt = mind.system_prompt || "";
      editPreferences = JSON.stringify(mind.preferences ?? {}, null, 2);
      editMission = mind.charter?.mission || "";
      editReasonForExistence = mind.charter?.reason_for_existence || "";
      editOperatingPrinciples = listToLines(mind.charter?.operating_principles);
      editNonGoals = listToLines(mind.charter?.non_goals);
      editReflectionFocus = listToLines(mind.charter?.reflection_focus);
    }
  });

  async function onCreate(e: Event) {
    e.preventDefault();
    error = "";
    if (!newName.trim()) return;
    saving = true;
    try {
      const preferences = parsePreferencesInput(newPreferences);
      const created = await api.createMind({
        name: newName.trim(),
        personality: newPersonality.trim(),
        system_prompt: newSystemPrompt.trim(),
        preferences,
      });
      minds = sortMinds([created, ...minds.filter((m) => m.id !== created.id)]);
      selectedMindId = created.id;
      onClose();
    } catch (err) {
      error = (err as Error).message;
    } finally {
      saving = false;
    }
  }

  async function onUpdate(e: Event) {
    e.preventDefault();
    error = "";
    if (!mind) return;
    saving = true;
    try {
      const preferences = parsePreferencesInput(editPreferences);
      const updated = await api.updateMind(mind.id, {
        name: editName.trim(),
        personality: editPersonality.trim(),
        system_prompt: editSystemPrompt.trim(),
        preferences,
        charter: {
          mission: editMission.trim(),
          reason_for_existence: editReasonForExistence.trim(),
          operating_principles: linesToList(editOperatingPrinciples),
          non_goals: linesToList(editNonGoals),
          reflection_focus: linesToList(editReflectionFocus),
        },
      });
      minds = sortMinds(minds.map((m) => (m.id === updated.id ? updated : m)));
      selectedMindId = updated.id;
      onClose();
    } catch (err) {
      error = (err as Error).message;
    } finally {
      saving = false;
    }
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
      <h2 class="modal-title">
        {mode === "create" ? "Create Mind" : "Mind Profile"}
      </h2>
      <button type="button" class="modal-close" onclick={onClose}>\u00D7</button>
    </div>

    {#if error}
      <div class="modal-error">{error}</div>
    {/if}

    {#if mode === "create"}
      <form class="field-grid" onsubmit={onCreate}>
        <label class="field">
          <span class="field-label">Name</span>
          <input bind:value={newName} placeholder="Mind name" />
        </label>
        <label class="field">
          <span class="field-label">Personality</span>
          <input bind:value={newPersonality} placeholder="How this Mind behaves" />
        </label>
        <label class="field full">
          <span class="field-label">System prompt override</span>
          <textarea rows="3" bind:value={newSystemPrompt} placeholder="Optional operating rules"></textarea>
        </label>
        <label class="field full">
          <span class="field-label">Preferences (JSON object)</span>
          <textarea rows="3" bind:value={newPreferences}></textarea>
        </label>
        <div class="actions full">
          <button type="submit" class="btn-primary" disabled={saving}>
            {saving ? "Creating..." : "Create Mind"}
          </button>
          <button type="button" class="btn-ghost" onclick={onClose}>Cancel</button>
        </div>
      </form>
    {:else if mind}
      <form class="field-grid" onsubmit={onUpdate}>
        <label class="field">
          <span class="field-label">Name</span>
          <input bind:value={editName} placeholder="Mind name" />
        </label>
        <label class="field">
          <span class="field-label">Personality</span>
          <input bind:value={editPersonality} placeholder="How this Mind behaves" />
        </label>
        <label class="field full">
          <span class="field-label">System prompt override</span>
          <textarea rows="3" bind:value={editSystemPrompt} placeholder="Optional operating rules"></textarea>
        </label>
        <label class="field full">
          <span class="field-label">Preferences (JSON object)</span>
          <textarea rows="3" bind:value={editPreferences}></textarea>
        </label>
        <label class="field full">
          <span class="field-label">Mission</span>
          <textarea rows="2" bind:value={editMission} placeholder="What this Mind is meant to accomplish"></textarea>
        </label>
        <label class="field full">
          <span class="field-label">Reason for existence</span>
          <textarea rows="2" bind:value={editReasonForExistence} placeholder="Why this Mind exists"></textarea>
        </label>
        <label class="field full">
          <span class="field-label">Operating principles (one per line)</span>
          <textarea rows="3" bind:value={editOperatingPrinciples} placeholder="Ground decisions in evidence"></textarea>
        </label>
        <label class="field full">
          <span class="field-label">Non-goals (one per line)</span>
          <textarea rows="3" bind:value={editNonGoals} placeholder="Do not pretend unsupported capabilities"></textarea>
        </label>
        <label class="field full">
          <span class="field-label">Reflection focus (one per line)</span>
          <textarea rows="3" bind:value={editReflectionFocus} placeholder="Identify the next missing capability"></textarea>
        </label>
        <div class="actions full">
          <button type="submit" class="btn-primary" disabled={saving}>
            {saving ? "Saving..." : "Save Changes"}
          </button>
          <button type="button" class="btn-ghost" onclick={onClose}>Cancel</button>
        </div>
      </form>
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
    max-width: 620px;
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
    align-items: center;
    margin-bottom: 20px;
  }

  .modal-title {
    font-family: var(--font-heading);
    font-size: 0.78rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--gold);
  }

  .modal-close {
    font-size: 1.4rem;
    color: var(--ink-3);
    padding: 4px 8px;
    line-height: 1;
    transition: color 150ms;
  }
  .modal-close:hover { color: var(--ink-1); }

  .modal-error {
    padding: 8px 12px;
    margin-bottom: 14px;
    border-radius: var(--radius, 8px);
    border: 1px solid rgba(204, 90, 90, 0.4);
    background: rgba(80, 16, 16, 0.5);
    color: #ffb8b8;
    font-family: var(--font-mono);
    font-size: 0.8rem;
  }

  .field-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }
  .field.full { grid-column: 1 / -1; }

  .field-label {
    font-family: var(--font-heading);
    font-size: 0.6rem;
    letter-spacing: 0.11em;
    text-transform: uppercase;
    color: var(--ink-2);
  }

  input, textarea {
    border: 1px solid rgba(191, 143, 59, 0.22);
    border-radius: var(--radius, 8px);
    color: var(--ink-1);
    background: rgba(5, 6, 12, 0.9);
    padding: 9px 11px;
    outline: none;
    transition: border-color 150ms, box-shadow 150ms;
    width: 100%;
    font: inherit;
  }
  textarea { resize: vertical; line-height: 1.48; }
  input:focus, textarea:focus {
    border-color: rgba(229, 169, 58, 0.6);
    box-shadow: 0 0 0 3px rgba(229, 169, 58, 0.11);
  }

  .actions {
    display: flex;
    gap: 10px;
    align-items: center;
  }

  .btn-primary {
    background: linear-gradient(148deg, var(--gold-mid) 0%, var(--gold-dim) 100%);
    color: #fef5db;
    border: 1px solid rgba(255, 230, 140, 0.18);
    padding: 10px 18px;
    border-radius: var(--radius, 8px);
    font-family: var(--font-heading);
    font-size: 0.72rem;
    letter-spacing: 0.11em;
    text-transform: uppercase;
    transition: transform 120ms ease;
  }
  .btn-primary:hover:not(:disabled) { transform: translateY(-1px); }

  .btn-ghost {
    border: 1px solid rgba(191, 143, 59, 0.28);
    color: #d9ba83;
    background: rgba(191, 143, 59, 0.08);
    padding: 8px 14px;
    border-radius: var(--radius, 8px);
    font-size: 0.78rem;
    transition: background 140ms;
  }
  .btn-ghost:hover:not(:disabled) { background: rgba(191, 143, 59, 0.16); }

  button:disabled { opacity: 0.42; cursor: not-allowed; }

  @media (max-width: 700px) {
    .field-grid { grid-template-columns: 1fr; }
    .modal-content { max-height: 90vh; }
  }
</style>
