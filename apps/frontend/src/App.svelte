<script lang="ts">
  import "./App.css";
  import ActivityStream from "./components/ActivityStream.svelte";
  import CommissionBar from "./components/CommissionBar.svelte";
  import Nexus from "./components/Nexus.svelte";
  import { api, consumeSSEStream } from "./lib/api";
  import {
    buildLiveTypingText,
    buildOutputItems,
    buildRunStats,
    toEventView,
  } from "./lib/helpers";
  import type { StreamEvent } from "./lib/types";

  let teamName = $state("default");
  let taskText = $state("");

  let runEvents = $state<StreamEvent[]>([]);
  let busy = $state(false);
  let error = $state("");

  let runStats = $derived(buildRunStats(runEvents));
  let runOutputItems = $derived(buildOutputItems(runEvents));
  let liveTypingText = $derived(buildLiveTypingText(runEvents));
  let runEventViews = $derived(
    runEvents
      .filter((event) => event.type !== "text_delta")
      .map((event, index) => toEventView(event, index))
  );
  let recentEventViews = $derived(runEventViews.slice(-8));

  async function onRun(): Promise<void> {
    if (!taskText.trim()) return;

    busy = true;
    error = "";
    runEvents = [];

    try {
      const body = await api.run({
        prompt: taskText.trim(),
        team: teamName || "default",
      });

      await consumeSSEStream(body, (event) => {
        runEvents = [...runEvents, event].slice(-2000);
      });
    } catch (err) {
      error = (err as Error).message;
    } finally {
      busy = false;
    }
  }
</script>

<div class="observatory-shell">
  <header class="observatory-header">
    <div class="header-brand">
      <span class="brand-glyph" aria-hidden="true">{"\u2B21"}</span>
      <span class="brand-text">Culture Engine</span>
    </div>

    <div class="header-actions">
      <span class="status-chip" data-status={runStats.status}>{runStats.status}</span>
    </div>
  </header>

  <main class="observatory-canvas">
    <div class="nexus-stack">
      <Nexus
        {busy}
        status={runStats.status}
      />

      <ActivityStream
        outputItems={runOutputItems}
        events={recentEventViews}
        {busy}
        {liveTypingText}
        status={runStats.status}
      />
    </div>
  </main>

  <footer class="observatory-footer">
    <CommissionBar
      bind:taskText
      bind:teamName
      {busy}
      onSubmit={onRun}
    />
  </footer>

  {#if error}
    <div class="error-toast" role="alert">
      <span>{error}</span>
      <button type="button" onclick={() => (error = "")}>dismiss</button>
    </div>
  {/if}
</div>
