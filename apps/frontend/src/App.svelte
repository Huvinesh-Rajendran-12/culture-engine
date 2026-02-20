<script lang="ts">
  import "./App.css";

  // ── Types ──────────────────────────────────────────────
  type Mind = {
    id: string;
    name: string;
    personality: string;
    created_at: string;
  };

  type Task = {
    id: string;
    description: string;
    status: string;
    result: string | null;
    created_at: string;
  };

  type StreamEvent = {
    type: string;
    content: unknown;
  };

  type TaskTrace = {
    task_id: string;
    mind_id: string;
    events: Array<{ type: string; content: unknown; timestamp: string }>;
  };

  // ── API ────────────────────────────────────────────────
  const api = {
    async listMinds(): Promise<Mind[]> {
      const res = await fetch("/api/minds");
      if (!res.ok) throw new Error("Failed to list minds");
      return res.json();
    },
    async createMind(name: string): Promise<Mind> {
      const res = await fetch("/api/minds", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (!res.ok) throw new Error("Failed to create mind");
      return res.json();
    },
    async listTasks(mindId: string): Promise<Task[]> {
      const res = await fetch(`/api/minds/${mindId}/tasks`);
      if (!res.ok) throw new Error("Failed to list tasks");
      return res.json();
    },
    async getTrace(mindId: string, taskId: string): Promise<TaskTrace> {
      const res = await fetch(`/api/minds/${mindId}/tasks/${taskId}/trace`);
      if (!res.ok) throw new Error("Failed to load trace");
      return res.json();
    },
  };

  // ── State (Svelte 5 runes) ─────────────────────────────
  let minds         = $state<Mind[]>([]);
  let selectedMindId = $state("");
  let newMindName   = $state("Orbit");
  let taskText      = $state("Summarize this week's project updates");
  let events        = $state<StreamEvent[]>([]);
  let tasks         = $state<Task[]>([]);
  let selectedTaskId = $state("");
  let trace         = $state<TaskTrace | null>(null);
  let busy          = $state(false);
  let error         = $state("");

  // ── Derived ────────────────────────────────────────────
  let selectedMind = $derived(minds.find((m) => m.id === selectedMindId));

  // ── Effects ────────────────────────────────────────────
  $effect(() => {
    void refreshMinds();
  });

  $effect(() => {
    const id = selectedMindId; // read synchronously so Svelte tracks it
    if (!id) { tasks = []; return; }
    void refreshTasks(id);
  });

  // ── Helpers ────────────────────────────────────────────
  function formatContent(content: unknown): string {
    const raw = typeof content === "string" ? content : JSON.stringify(content);
    return raw.length > 480 ? raw.slice(0, 480) + " …" : raw;
  }

  // ── API calls ──────────────────────────────────────────
  async function refreshMinds() {
    try {
      const data = await api.listMinds();
      minds = data;
      if (!selectedMindId && data.length > 0) selectedMindId = data[0].id;
    } catch (e) { error = (e as Error).message; }
  }

  async function refreshTasks(mindId: string) {
    try { tasks = await api.listTasks(mindId); }
    catch (e) { error = (e as Error).message; }
  }

  async function onCreateMind(e: Event) {
    e.preventDefault();
    error = "";
    if (!newMindName.trim()) return;
    try {
      const mind = await api.createMind(newMindName.trim());
      minds = [mind, ...minds];
      selectedMindId = mind.id;
      newMindName = "";
    } catch (err) { error = (err as Error).message; }
  }

  async function onDelegate(e: Event) {
    e.preventDefault();
    if (!selectedMindId || !taskText.trim()) return;

    busy = true;
    error = "";
    events = [];
    trace = null;

    try {
      const res = await fetch(`/api/minds/${selectedMindId}/delegate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: taskText, team: "default" }),
      });
      if (!res.ok || !res.body) throw new Error("Failed to start delegation stream");

      const reader = res.body.getReader();
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
            const event = JSON.parse(line.slice(6)) as StreamEvent;
            events = [...events, event];
          }
          split = buffer.indexOf("\n\n");
        }
      }

      await refreshTasks(selectedMindId);
    } catch (err) { error = (err as Error).message; }
    finally { busy = false; }
  }

  async function loadTrace(taskId: string) {
    if (!selectedMindId) return;
    try {
      selectedTaskId = taskId;
      trace = await api.getTrace(selectedMindId, taskId);
    } catch (err) { error = (err as Error).message; }
  }
</script>

<div class="app">

  <!-- ── Hero ── -->
  <header class="hero">
    <h1>Culture Engine</h1>
    <svg class="hero-ornament" viewBox="0 0 240 28" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <line x1="0" y1="14" x2="72" y2="14" stroke="currentColor" stroke-width="0.4" opacity="0.4"/>
      <line x1="0" y1="14" x2="45" y2="14" stroke="currentColor" stroke-width="1" opacity="0.7"/>
      <circle cx="82"  cy="14" r="4.5" fill="none" stroke="currentColor" stroke-width="0.8"/>
      <circle cx="97"  cy="14" r="2.5" fill="none" stroke="currentColor" stroke-width="0.8"/>
      <circle cx="108" cy="14" r="1.2" fill="currentColor" opacity="0.6"/>
      <polygon points="120,7 128,14 120,21 112,14" fill="none" stroke="currentColor" stroke-width="0.9"/>
      <circle  cx="120" cy="14" r="2.5" fill="currentColor" opacity="0.85"/>
      <circle cx="132" cy="14" r="1.2" fill="currentColor" opacity="0.6"/>
      <circle cx="143" cy="14" r="2.5" fill="none" stroke="currentColor" stroke-width="0.8"/>
      <circle cx="158" cy="14" r="4.5" fill="none" stroke="currentColor" stroke-width="0.8"/>
      <line x1="168" y1="14" x2="240" y2="14" stroke="currentColor" stroke-width="0.4" opacity="0.4"/>
      <line x1="195" y1="14" x2="240" y2="14" stroke="currentColor" stroke-width="1" opacity="0.7"/>
    </svg>
    <p class="subtitle">A renaissance-inspired atelier for your autonomous Mind and delegated craftwork.</p>
  </header>

  <!-- ── Controls ── -->
  <div class="controls">
    <section class="card">
      <h3>Summon a Mind</h3>
      <form onsubmit={onCreateMind} class="row">
        <input bind:value={newMindName} placeholder="Name the mind…" />
        <button type="submit">Summon</button>
      </form>
    </section>

    <section class="card">
      <h3>Active Mind</h3>
      <div class="row">
        <select bind:value={selectedMindId}>
          <option value="">— choose —</option>
          {#each minds as mind (mind.id)}
            <option value={mind.id}>{mind.name} · {mind.id}</option>
          {/each}
        </select>
      </div>
      {#if selectedMind}
        <div class="mind-trait">{selectedMind.personality || "Personality uncharted"}</div>
      {/if}
    </section>
  </div>

  <!-- ── Commission ── -->
  <section class="card" style="margin-bottom: 16px">
    <h3>Commission a Task</h3>
    <form onsubmit={onDelegate} class="row">
      <input class="wide" bind:value={taskText} placeholder="Describe the commission…" />
      <button type="submit" disabled={!selectedMindId || busy}>
        {#if busy}
          <span class="busy-indicator">
            <span class="busy-dot"></span>
            <span class="busy-dot"></span>
            <span class="busy-dot"></span>
            Transmitting
          </span>
        {:else}
          Commission
        {/if}
      </button>
    </form>
  </section>

  {#if error}
    <div class="error">⚠ {error}</div>
  {/if}

  <!-- ── Chronicle & Ledger ── -->
  <div class="grid">
    <section class="card">
      <h3>Live Event Chronicle</h3>
      <div class="panel">
        {#if events.length === 0}
          <div class="muted">Awaiting transmissions…</div>
        {:else}
          {#each events as evt, idx (idx)}
            <pre style="animation-delay: {Math.min(idx * 25, 300)}ms"><span class="evt-tag" data-type={evt.type}>{evt.type}</span>{formatContent(evt.content)}</pre>
          {/each}
        {/if}
      </div>
    </section>

    <section class="card">
      <h3>Task Ledger</h3>
      <div class="panel">
        {#if tasks.length === 0}
          <div class="muted">The ledger is empty.</div>
        {:else}
          {#each tasks as task (task.id)}
            <div class="task-row">
              <div class="task-meta">
                <span class="badge" data-status={task.status}>{task.status}</span>
                <span class="muted" style="font-size: 0.68rem">{task.id.slice(0, 8)}</span>
              </div>
              <div class="task-desc">{task.description}</div>
              <button class="btn-sm" onclick={() => void loadTrace(task.id)} style="align-self: flex-start">
                Inspect Trace
              </button>
            </div>
          {/each}
        {/if}
      </div>
    </section>
  </div>

  <!-- ── Trace Codex ── -->
  <section class="card" style="margin-top: 16px">
    <h3>Trace Codex{selectedTaskId ? ` · ${selectedTaskId.slice(0, 8)}` : ""}</h3>
    <div class="panel trace-panel">
      {#if !trace}
        <div class="muted">Select a task to reveal its chronicle.</div>
      {:else}
        {#each trace.events as evt, idx (idx)}
          <pre><span class="trace-ts">{evt.timestamp}</span> <span class="evt-tag" data-type={evt.type}>{evt.type}</span>{JSON.stringify(evt.content).slice(0, 320)}</pre>
        {/each}
      {/if}
    </div>
  </section>

</div>
