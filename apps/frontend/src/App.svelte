<script lang="ts">
  import "./App.css";
  import ActivityStream from "./components/ActivityStream.svelte";
  import CommissionBar from "./components/CommissionBar.svelte";
  import Constellation from "./components/Constellation.svelte";
  import MemoryVault from "./components/MemoryVault.svelte";
  import MindProfileModal from "./components/MindProfileModal.svelte";
  import MindSelector from "./components/MindSelector.svelte";
  import Nexus from "./components/Nexus.svelte";
  import TaskDetail from "./components/TaskDetail.svelte";
  import { api } from "./lib/api";
  import {
    buildLiveTypingText,
    buildOutputItems,
    buildRunStats,
    extractMemoryContextIds,
    getTaskIdFromEvent,
    sortMinds,
    toEventView,
  } from "./lib/helpers";
  import type { MemoryEntry, Mind, Overlay, StreamEvent, Task } from "./lib/types";

  let minds = $state<Mind[]>([]);
  let selectedMindId = $state("");
  let tasks = $state<Task[]>([]);
  let memories = $state<MemoryEntry[]>([]);

  let teamName = $state("default");
  let taskText = $state(
    "Draft an onboarding execution plan for a backend engineer, then break it into communication, access, and documentation workstreams."
  );

  let runEvents = $state<StreamEvent[]>([]);
  let busy = $state(false);
  let error = $state("");

  let activeOverlay = $state<Overlay>("none");
  let selectedTaskId = $state("");

  let selectedMind = $derived(minds.find((mind) => mind.id === selectedMindId) ?? null);
  let selectedTask = $derived(tasks.find((task) => task.id === selectedTaskId) ?? null);

  let runStats = $derived(buildRunStats(runEvents));
  let runOutputItems = $derived(buildOutputItems(runEvents));
  let liveTypingText = $derived(buildLiveTypingText(runEvents));
  let runMemoryContextIds = $derived(extractMemoryContextIds(runEvents));
  let runEventViews = $derived(
    runEvents
      .filter((event) => event.type !== "text_delta")
      .map((event, index) => toEventView(event, index))
  );
  let recentEventViews = $derived(runEventViews.slice(-8));

  $effect(() => {
    void refreshMinds();
  });

  $effect(() => {
    const mindId = selectedMindId;
    if (!mindId) {
      tasks = [];
      memories = [];
      selectedTaskId = "";
      return;
    }
    void refreshTasks(mindId);
    void refreshMemories(mindId);
  });

  async function refreshMinds(): Promise<void> {
    try {
      const data = sortMinds(await api.listMinds());
      minds = data;
      if (selectedMindId && data.some((mind) => mind.id === selectedMindId)) return;
      selectedMindId = data[0]?.id ?? "";
    } catch (err) {
      error = (err as Error).message;
    }
  }

  async function refreshTasks(mindId: string): Promise<void> {
    try {
      tasks = await api.listTasks(mindId);
      if (selectedTaskId && !tasks.some((task) => task.id === selectedTaskId)) {
        selectedTaskId = "";
      }
    } catch (err) {
      error = (err as Error).message;
    }
  }

  async function refreshMemories(mindId: string): Promise<void> {
    try {
      memories = await api.listMemory(mindId);
    } catch (err) {
      error = (err as Error).message;
    }
  }

  async function onDelegate(): Promise<void> {
    if (!selectedMindId || !taskText.trim()) return;

    busy = true;
    error = "";
    runEvents = [];
    selectedTaskId = "";
    let taskIdFromRun = "";

    try {
      const response = await fetch(`/api/minds/${selectedMindId}/delegate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: taskText, team: teamName || "default" }),
      });

      if (!response.ok || !response.body) {
        throw new Error("Failed to start delegation stream");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let split = buffer.indexOf("\n\n");
        while (split !== -1) {
          const chunk = buffer.slice(0, split);
          buffer = buffer.slice(split + 2);

          for (const line of chunk.split("\n")) {
            if (!line.startsWith("data: ")) continue;
            let event: StreamEvent;
            try {
              event = JSON.parse(line.slice(6)) as StreamEvent;
            } catch {
              continue;
            }

            const maybeTaskId = getTaskIdFromEvent(event);
            if (maybeTaskId) {
              taskIdFromRun = maybeTaskId;
            }

            runEvents = [...runEvents, event].slice(-2000);
          }

          split = buffer.indexOf("\n\n");
        }
      }

      await refreshTasks(selectedMindId);
      await refreshMemories(selectedMindId);
      if (taskIdFromRun) {
        selectedTaskId = taskIdFromRun;
      }
    } catch (err) {
      error = (err as Error).message;
    } finally {
      busy = false;
    }
  }

  function openTaskDetail(taskId: string): void {
    selectedTaskId = taskId;
    activeOverlay = "task-detail";
  }

  function closeOverlay(): void {
    activeOverlay = "none";
  }

  function onWindowKeydown(event: KeyboardEvent): void {
    if (event.key === "Escape" && activeOverlay !== "none") {
      activeOverlay = "none";
    }
  }
</script>

<svelte:window on:keydown={onWindowKeydown} />

<div class="observatory-shell">
  <header class="observatory-header">
    <MindSelector
      bind:minds
      bind:selectedMindId
      {busy}
      onOpenProfile={() => (activeOverlay = "mind-profile")}
      onOpenCreate={() => (activeOverlay = "mind-create")}
    />

    <div class="header-actions">
      <button
        type="button"
        class="memory-button"
        disabled={!selectedMindId}
        onclick={() => (activeOverlay = "memory-vault")}
      >
        Memory Vault
      </button>
      <span class="status-chip" data-status={runStats.status}>{runStats.status}</span>
    </div>
  </header>

  <main class="observatory-canvas">
    <Constellation
      {tasks}
      selectedTaskId={selectedTaskId}
      {busy}
      onSelectTask={openTaskDetail}
    />

    <div class="nexus-stack">
      <Nexus
        mindName={selectedMind?.name ?? "No Mind Selected"}
        mindId={selectedMindId}
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
      selectedMindId={selectedMindId}
      bind:taskText
      bind:teamName
      {busy}
      onSubmit={onDelegate}
    />
  </footer>

  {#if error}
    <div class="error-toast" role="alert">
      <span>{error}</span>
      <button type="button" onclick={() => (error = "")}>dismiss</button>
    </div>
  {/if}
</div>

{#if activeOverlay === "task-detail" && selectedTask && selectedMindId}
  <TaskDetail task={selectedTask} mindId={selectedMindId} onClose={closeOverlay} />
{/if}

{#if activeOverlay === "memory-vault" && selectedMindId}
  <MemoryVault
    mindId={selectedMindId}
    bind:memories
    contextMemoryIds={runMemoryContextIds}
    onClose={closeOverlay}
  />
{/if}

{#if activeOverlay === "mind-profile" && selectedMind}
  <MindProfileModal
    mind={selectedMind}
    bind:minds
    bind:selectedMindId
    mode="edit"
    onClose={closeOverlay}
  />
{/if}

{#if activeOverlay === "mind-create"}
  <MindProfileModal
    mind={null}
    bind:minds
    bind:selectedMindId
    mode="create"
    onClose={closeOverlay}
  />
{/if}
