<script lang="ts">
  let {
    taskText = $bindable(""),
    teamName = $bindable("default"),
    busy = false,
    onSubmit,
  }: {
    taskText: string;
    teamName: string;
    busy?: boolean;
    onSubmit?: () => void | Promise<void>;
  } = $props();

  let textareaEl: HTMLTextAreaElement | null = null;

  $effect(() => {
    taskText;
    resizeTextarea();
  });

  function resizeTextarea(): void {
    if (!textareaEl) return;
    textareaEl.style.height = "0px";
    textareaEl.style.height = `${Math.min(220, textareaEl.scrollHeight)}px`;
  }

  function submitRun(event: Event): void {
    event.preventDefault();
    if (busy || !taskText.trim()) return;
    void onSubmit?.();
  }

  function onTextareaKeydown(event: KeyboardEvent): void {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      if (busy || !taskText.trim()) return;
      void onSubmit?.();
    }
  }
</script>

<form class="commission-bar" onsubmit={submitRun}>
  <label class="commission-input-wrap">
    <span class="sr-only">Task prompt</span>
    <textarea
      bind:this={textareaEl}
      bind:value={taskText}
      class="commission-textarea"
      placeholder="Describe a task for the agent..."
      rows="1"
      oninput={resizeTextarea}
      onkeydown={onTextareaKeydown}
    ></textarea>
  </label>

  <label class="team-wrap">
    <span class="team-label">Team</span>
    <input bind:value={teamName} class="team-input" placeholder="default" />
  </label>

  <button
    type="submit"
    class="commission-submit"
    disabled={busy || !taskText.trim()}
  >
    {busy ? "Running..." : "Run"}
  </button>
</form>

<style>
  .commission-bar {
    width: min(1080px, 100% - 24px);
    margin: 0 auto;
    display: grid;
    grid-template-columns: 1fr auto auto;
    gap: 10px;
    align-items: end;
    padding: 12px;
    border-radius: 14px;
    border: 1px solid rgba(232, 175, 71, 0.25);
    background:
      linear-gradient(145deg, rgba(17, 21, 34, 0.95), rgba(9, 12, 20, 0.96));
    box-shadow:
      0 -6px 28px rgba(0, 0, 0, 0.4),
      inset 0 1px 0 rgba(255, 255, 255, 0.05);
  }

  .commission-input-wrap {
    display: block;
  }

  .commission-textarea {
    width: 100%;
    min-height: 44px;
    max-height: 220px;
    resize: none;
    border-radius: 10px;
    border: 1px solid rgba(232, 175, 71, 0.22);
    background: rgba(4, 6, 12, 0.88);
    color: var(--ink-1);
    padding: 11px 12px;
    line-height: 1.4;
    font-size: 0.96rem;
    outline: none;
    font-family: var(--font-body);
  }

  .commission-textarea:focus {
    border-color: rgba(232, 175, 71, 0.66);
    box-shadow: 0 0 0 3px rgba(232, 175, 71, 0.12);
  }

  .team-wrap {
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 110px;
  }

  .team-label {
    font-family: var(--font-heading);
    text-transform: uppercase;
    letter-spacing: 0.14em;
    font-size: 0.52rem;
    color: var(--ink-3);
  }

  .team-input {
    width: 110px;
    height: 40px;
    border-radius: 9px;
    border: 1px solid rgba(232, 175, 71, 0.22);
    background: rgba(4, 6, 12, 0.88);
    color: var(--ink-1);
    padding: 0 10px;
    outline: none;
    font-family: var(--font-mono);
    font-size: 0.78rem;
  }

  .team-input:focus {
    border-color: rgba(232, 175, 71, 0.66);
    box-shadow: 0 0 0 3px rgba(232, 175, 71, 0.12);
  }

  .commission-submit {
    height: 40px;
    border-radius: 10px;
    border: 1px solid rgba(255, 226, 147, 0.26);
    background: linear-gradient(145deg, #d9a24a, #9b712c);
    color: #fff8e6;
    padding: 0 18px;
    font-family: var(--font-heading);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-size: 0.66rem;
    transition: transform 120ms ease, filter 160ms ease;
  }

  .commission-submit:hover:not(:disabled) {
    transform: translateY(-1px);
    filter: brightness(1.06);
  }

  .commission-submit:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  @media (max-width: 960px) {
    .commission-bar {
      grid-template-columns: 1fr auto;
      grid-template-areas:
        "input input"
        "team submit";
      width: min(940px, 100% - 18px);
    }

    .commission-input-wrap { grid-area: input; }
    .team-wrap { grid-area: team; }
    .commission-submit { grid-area: submit; justify-self: end; }
  }

  @media (max-width: 700px) {
    .commission-bar {
      grid-template-columns: 1fr;
      grid-template-areas:
        "input"
        "team"
        "submit";
      border-radius: 12px 12px 0 0;
      border-bottom: none;
      width: 100%;
      padding: 10px;
    }

    .team-wrap,
    .team-input,
    .commission-submit {
      width: 100%;
    }
  }
</style>
