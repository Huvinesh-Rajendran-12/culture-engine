<script lang="ts">
  import "./App.css";

  // ── Types ────────────────────────────────────────────────────────────────────

  type Mind = {
    id: string;
    name: string;
    personality: string;
    preferences: Record<string, unknown>;
    system_prompt: string;
    created_at: string;
  };

  type Task = {
    id: string;
    mind_id?: string;
    description: string;
    status: string;
    result: string | null;
    created_at: string;
    completed_at?: string | null;
  };

  type StreamEvent = {
    type: string;
    content: unknown;
    timestamp?: string;
  };

  type TraceEvent = {
    type: string;
    content: unknown;
    timestamp: string;
  };

  type TaskTrace = {
    task_id: string;
    mind_id: string;
    events: TraceEvent[];
  };

  type MemoryEntry = {
    id: string;
    mind_id: string;
    content: string;
    category: string | null;
    relevance_keywords: string[];
    created_at: string;
  };

  type EventView = {
    id: string;
    type: string;
    title: string;
    detail: string;
    fullDetail: string;
    severity: "info" | "success" | "warn" | "error";
    timestamp: string | null;
  };

  type SpawnRun = {
    callId: string;
    objective: string;
    maxTurns: number;
    result: string;
    isError: boolean;
  };

  type RunStats = {
    total: number;
    text: number;
    toolUse: number;
    toolResult: number;
    errors: number;
    status: string;
    taskId: string;
  };

  type Section = "minds" | "delegate" | "telemetry" | "history" | "memory";

  // ── API ──────────────────────────────────────────────────────────────────────

  const api = {
    async listMinds(): Promise<Mind[]> {
      const res = await fetch("/api/minds");
      if (!res.ok) throw new Error("Failed to list minds");
      return res.json();
    },

    async createMind(payload: {
      name: string;
      personality: string;
      system_prompt: string;
      preferences: Record<string, unknown>;
    }): Promise<Mind> {
      const res = await fetch("/api/minds", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
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

    async listMemory(mindId: string): Promise<MemoryEntry[]> {
      const res = await fetch(`/api/minds/${mindId}/memory`);
      if (!res.ok) throw new Error("Failed to list memory");
      return res.json();
    },
  };

  // ── State ────────────────────────────────────────────────────────────────────

  let minds              = $state<Mind[]>([]);
  let selectedMindId     = $state("");
  let newMindName        = $state("Atlas");
  let newMindPersonality = $state("Calm, pragmatic digital operator");
  let newMindSystemPrompt = $state("");
  let newMindPreferences = $state('{"tone":"direct","depth":"concise"}');

  let teamName    = $state("default");
  let taskText    = $state(
    "Draft an onboarding execution plan for a backend engineer, then break it into communication, access, and documentation workstreams.",
  );

  let runEvents     = $state<StreamEvent[]>([]);
  let tasks         = $state<Task[]>([]);
  let selectedTaskId = $state("");
  let trace         = $state<TaskTrace | null>(null);
  let memories      = $state<MemoryEntry[]>([]);
  let memorySearch  = $state("");
  let memoryCategory = $state("all");
  let busy          = $state(false);
  let error         = $state("");

  // UI-only navigation state
  let activeSection  = $state<Section>("minds");
  let navOpen        = $state(false);
  let expandedEvents = $state<Set<string>>(new Set());

  // ── Derived ──────────────────────────────────────────────────────────────────

  let selectedMind        = $derived(minds.find((m) => m.id === selectedMindId) ?? null);
  let runStats            = $derived(buildRunStats(runEvents));
  let runToolRegistry     = $derived(extractToolRegistry(runEvents));
  let runMemoryContextIds = $derived(extractMemoryContextIds(runEvents));
  let spawnRuns           = $derived(extractSpawnRuns(runEvents));
  // Filter out text_delta chunks — they're accumulated into liveTypingText instead
  let runEventViews       = $derived(
    runEvents.filter((e) => e.type !== "text_delta").map((e, i) => toEventView(e, i))
  );
  let traceEventViews     = $derived(
    (trace?.events ?? []).filter((e) => e.type !== "text_delta").map((e, i) => toEventView(e, i))
  );
  // Accumulate streaming text_delta chunks into a live buffer for the composing indicator
  let liveTypingText      = $derived.by(() => {
    let buffer = "";
    for (const event of runEvents) {
      // Reset on new task or when a completed text block arrives
      if (event.type === "task_started" || event.type === "text") {
        buffer = "";
      }
      if (event.type === "text_delta") {
        const c = event.content;
        if (typeof c === "string") {
          buffer += c;
        } else {
          const obj = asObject(c);
          if (typeof obj.text === "string") buffer += obj.text;
        }
      }
    }
    return buffer;
  });
  let memoryCategories    = $derived(buildMemoryCategories(memories));
  let filteredMemories    = $derived(filterMemories(memories, memorySearch, memoryCategory));

  // ── Effects ──────────────────────────────────────────────────────────────────

  $effect(() => {
    void refreshMinds();
  });

  $effect(() => {
    const id = selectedMindId;
    if (!id) {
      tasks = [];
      trace = null;
      selectedTaskId = "";
      memories = [];
      return;
    }
    void refreshTasks(id);
    void refreshMemories(id);
  });

  // ── Helpers ──────────────────────────────────────────────────────────────────

  function asObject(value: unknown): Record<string, unknown> {
    return value && typeof value === "object" && !Array.isArray(value)
      ? (value as Record<string, unknown>)
      : {};
  }

  function compact(value: unknown, max = 220): string {
    const raw = typeof value === "string" ? value : JSON.stringify(value, null, 0);
    if (!raw) return "";
    return raw.length > max ? `${raw.slice(0, max)}...` : raw;
  }

  function fullString(value: unknown): string {
    if (typeof value === "string") return value;
    return JSON.stringify(value, null, 2);
  }

  function prettyDate(value: string | null | undefined): string {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
  }

  function parsePreferencesInput(raw: string): Record<string, unknown> {
    const value = raw.trim();
    if (!value) return {};
    const parsed = JSON.parse(value);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("Preferences must be a JSON object");
    }
    return parsed as Record<string, unknown>;
  }

  function sortMinds(list: Mind[]): Mind[] {
    return [...list].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
  }

  function getTaskIdFromEvent(event: StreamEvent): string {
    if (event.type !== "task_started") return "";
    const payload = asObject(event.content);
    return typeof payload.task_id === "string" ? payload.task_id : "";
  }

  function buildRunStats(events: StreamEvent[]): RunStats {
    let text = 0, toolUse = 0, toolResult = 0, errors = 0;
    let status = events.length > 0 ? "running" : "idle";
    let taskId = "";

    for (const event of events) {
      if (event.type === "text")        text       += 1;
      if (event.type === "tool_use")    toolUse    += 1;
      if (event.type === "tool_result") toolResult += 1;
      if (event.type === "error")       errors     += 1;
      if (event.type === "task_started") {
        taskId = getTaskIdFromEvent(event);
        status = "running";
      }
      if (event.type === "task_finished") {
        const payload = asObject(event.content);
        if (typeof payload.status === "string") status = payload.status;
      }
    }

    return { total: events.length, text, toolUse, toolResult, errors, status, taskId };
  }

  function extractToolRegistry(events: StreamEvent[]): string[] {
    for (let i = events.length - 1; i >= 0; i--) {
      const event = events[i];
      if (event.type !== "tool_registry") continue;
      const payload = asObject(event.content);
      const tools = payload.tools;
      if (!Array.isArray(tools)) return [];
      return tools.filter((t): t is string => typeof t === "string");
    }
    return [];
  }

  function extractMemoryContextIds(events: StreamEvent[]): string[] {
    for (let i = events.length - 1; i >= 0; i--) {
      const event = events[i];
      if (event.type !== "memory_context") continue;
      const payload = asObject(event.content);
      const ids = payload.memory_ids;
      if (!Array.isArray(ids)) return [];
      return ids.filter((id): id is string => typeof id === "string");
    }
    return [];
  }

  function extractSpawnRuns(events: StreamEvent[]): SpawnRun[] {
    const runs = new Map<string, SpawnRun>();

    for (const event of events) {
      if (event.type === "tool_use") {
        const payload = asObject(event.content);
        if (payload.tool !== "spawn_agent") continue;
        const callId = typeof payload.id === "string" ? payload.id : `spawn-${runs.size + 1}`;
        const input = asObject(payload.input);
        const objective = typeof input.objective === "string" ? input.objective : "No objective provided";
        const maxTurns = typeof input.max_turns === "number" ? input.max_turns : 12;
        runs.set(callId, { callId, objective, maxTurns, result: "pending", isError: false });
      }

      if (event.type === "tool_result") {
        const payload = asObject(event.content);
        const callId = typeof payload.tool_use_id === "string" ? payload.tool_use_id : "";
        if (!callId || !runs.has(callId)) continue;
        const run = runs.get(callId)!;
        run.result = compact(payload.result, 320) || "completed";
        run.isError = Boolean(payload.is_error);
      }
    }

    return Array.from(runs.values());
  }

  function getTimestamp(event: StreamEvent | TraceEvent): string | null {
    return typeof event.timestamp === "string" ? event.timestamp : null;
  }

  function toEventView(event: StreamEvent | TraceEvent, index: number): EventView {
    const payload = asObject(event.content);
    const view: EventView = {
      id:         `${index}-${event.type}`,
      type:       event.type,
      title:      event.type,
      detail:     compact(event.content, 400),
      fullDetail: fullString(event.content),
      severity:   "info",
      timestamp:  getTimestamp(event),
    };

    switch (event.type) {
      case "task_started": {
        const taskId = typeof payload.task_id === "string" ? payload.task_id : "unknown";
        view.title  = "Task started";
        view.detail = `Task ${taskId} started`;
        view.fullDetail = view.detail;
        break;
      }
      case "memory_context": {
        const count = typeof payload.count === "number" ? payload.count : 0;
        const ids = Array.isArray(payload.memory_ids)
          ? payload.memory_ids.filter((x): x is string => typeof x === "string")
          : [];
        view.title  = "Memory loaded";
        view.detail = `${count} memories injected (${ids.join(", ") || "none"})`;
        view.fullDetail = view.detail;
        break;
      }
      case "tool_registry": {
        const tools = Array.isArray(payload.tools)
          ? payload.tools.filter((t): t is string => typeof t === "string")
          : [];
        view.title      = "Tool registry";
        view.detail     = tools.join(", ");
        view.fullDetail = view.detail;
        break;
      }
      case "tool_use": {
        const toolName  = typeof payload.tool === "string" ? payload.tool : "unknown";
        view.title      = `Tool call: ${toolName}`;
        view.detail     = compact(payload.input, 320);
        view.fullDetail = fullString(payload.input);
        break;
      }
      case "tool_result": {
        const isError  = Boolean(payload.is_error);
        view.title     = `Tool result${isError ? " (error)" : ""}`;
        view.detail    = compact(payload.result, 320);
        view.fullDetail = fullString(payload.result);
        view.severity  = isError ? "warn" : "success";
        break;
      }
      case "text": {
        view.title     = "Mind output";
        view.detail    = typeof event.content === "string" ? event.content : compact(event.content, 400);
        view.fullDetail = typeof event.content === "string" ? event.content : fullString(event.content);
        break;
      }
      case "result": {
        const subtype  = typeof payload.subtype === "string" ? payload.subtype : "completed";
        view.title     = "Run result";
        view.detail    = `Subtype: ${subtype}`;
        view.fullDetail = view.detail;
        view.severity  = "success";
        break;
      }
      case "task_finished": {
        const status   = typeof payload.status === "string" ? payload.status : "unknown";
        view.title     = "Task finished";
        view.detail    = `Status: ${status}`;
        view.fullDetail = view.detail;
        view.severity  = status === "completed" ? "success" : "warn";
        break;
      }
      case "error": {
        view.title     = "Error";
        view.detail    = typeof event.content === "string" ? event.content : compact(event.content, 400);
        view.fullDetail = typeof event.content === "string" ? event.content : fullString(event.content);
        view.severity  = "error";
        break;
      }
      default:
        break;
    }

    return view;
  }

  function buildMemoryCategories(items: MemoryEntry[]): string[] {
    const cats = new Set<string>();
    for (const item of items) cats.add(item.category || "uncategorized");
    return ["all", ...Array.from(cats).sort((a, b) => a.localeCompare(b))];
  }

  function filterMemories(items: MemoryEntry[], query: string, category: string): MemoryEntry[] {
    const q = query.trim().toLowerCase();
    return items.filter((item) => {
      const cat = item.category || "uncategorized";
      if (category !== "all" && cat !== category) return false;
      if (!q) return true;
      const hay = [item.content, item.category || "", item.relevance_keywords.join(" ")]
        .join(" ").toLowerCase();
      return hay.includes(q);
    });
  }

  // ── Navigation helpers ────────────────────────────────────────────────────────

  function navigateTo(section: Section) {
    activeSection = section;
    navOpen = false;
  }

  function toggleExpand(id: string) {
    const next = new Set(expandedEvents);
    if (next.has(id)) next.delete(id); else next.add(id);
    expandedEvents = next;
  }

  function statValueClass(key: string, value: string | number): string {
    if (key === "errors" && Number(value) > 0) return "v-error";
    if (key === "status") {
      if (value === "running" || value === "in_progress") return "v-running";
      if (value === "completed") return "v-complete";
      if (value === "failed" || value === "error") return "v-failed";
    }
    return "";
  }

  // ── Data refresh ──────────────────────────────────────────────────────────────

  async function refreshMinds() {
    try {
      const data = sortMinds(await api.listMinds());
      minds = data;
      if (selectedMindId && data.some((m) => m.id === selectedMindId)) return;
      selectedMindId = data[0]?.id ?? "";
    } catch (err) {
      error = (err as Error).message;
    }
  }

  async function refreshTasks(mindId: string) {
    try {
      tasks = await api.listTasks(mindId);
      if (selectedTaskId && !tasks.some((t) => t.id === selectedTaskId)) selectedTaskId = "";
    } catch (err) {
      error = (err as Error).message;
    }
  }

  async function refreshMemories(mindId: string) {
    try {
      memories = await api.listMemory(mindId);
    } catch (err) {
      error = (err as Error).message;
    }
  }

  // ── Event handlers ────────────────────────────────────────────────────────────

  async function onCreateMind(event: Event) {
    event.preventDefault();
    error = "";
    if (!newMindName.trim()) return;

    try {
      const preferences = parsePreferencesInput(newMindPreferences);
      const mind = await api.createMind({
        name:         newMindName.trim(),
        personality:  newMindPersonality.trim(),
        system_prompt: newMindSystemPrompt.trim(),
        preferences,
      });
      minds          = sortMinds([mind, ...minds.filter((m) => m.id !== mind.id)]);
      selectedMindId = mind.id;
      newMindName         = "Atlas";
      newMindPersonality  = "Calm, pragmatic digital operator";
      newMindSystemPrompt = "";
      newMindPreferences  = '{"tone":"direct","depth":"concise"}';
    } catch (err) {
      error = (err as Error).message;
    }
  }

  async function onDelegate(event: Event) {
    event.preventDefault();
    if (!selectedMindId || !taskText.trim()) return;

    busy = true;
    error = "";
    runEvents = [];
    trace = null;
    selectedTaskId = "";
    let taskIdFromRun = "";

    try {
      const res = await fetch(`/api/minds/${selectedMindId}/delegate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: taskText, team: teamName || "default" }),
      });

      if (!res.ok || !res.body) throw new Error("Failed to start delegation stream");

      const reader  = res.body.getReader();
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
            let evt: StreamEvent;
            try { evt = JSON.parse(line.slice(6)) as StreamEvent; }
            catch { continue; }
            const maybeId = getTaskIdFromEvent(evt);
            if (maybeId) taskIdFromRun = maybeId;
            runEvents = [...runEvents, evt].slice(-1500);
          }
          split = buffer.indexOf("\n\n");
        }
      }

      await refreshTasks(selectedMindId);
      await refreshMemories(selectedMindId);
      if (taskIdFromRun) await loadTrace(taskIdFromRun);
    } catch (err) {
      error = (err as Error).message;
    } finally {
      busy = false;
    }
  }

  async function loadTrace(taskId: string) {
    if (!selectedMindId) return;
    try {
      selectedTaskId = taskId;
      trace = await api.getTrace(selectedMindId, taskId);
    } catch (err) {
      error = (err as Error).message;
    }
  }

  function taskPreview(task: Task): string {
    if (task.result) return compact(task.result, 130);
    return "No result captured yet";
  }

  function formatPreferences(mind: Mind): string {
    return JSON.stringify(mind.preferences, null, 2);
  }
</script>

<!-- ============================================================
     Shell: sidebar + main
     ============================================================ -->
<div class="shell">

  <!-- Mobile sidebar backdrop -->
  {#if navOpen}
    <div
      class="sidebar-backdrop"
      role="button"
      tabindex="-1"
      aria-label="Close navigation"
      onclick={() => (navOpen = false)}
      onkeydown={(e) => e.key === "Escape" && (navOpen = false)}
    ></div>
  {/if}

  <!-- ── Sidebar ── -->
  <nav class="sidebar" class:open={navOpen} aria-label="Main navigation">

    <div class="sidebar-header">
      <span class="sidebar-glyph" aria-hidden="true">⬡</span>
      <div class="sidebar-title">
        <span class="sidebar-brand">Culture</span>
        <span class="sidebar-brand-sub">Engine</span>
      </div>
    </div>

    <ul class="nav-list" role="list">
      <li>
        <button
          class="nav-item"
          class:active={activeSection === "minds"}
          onclick={() => navigateTo("minds")}
          aria-current={activeSection === "minds" ? "page" : undefined}
        >
          <span class="nav-icon" aria-hidden="true">◉</span>
          <span class="nav-label">Minds</span>
          {#if minds.length > 0}
            <span class="nav-badge">{minds.length}</span>
          {/if}
        </button>
      </li>
      <li>
        <button
          class="nav-item"
          class:active={activeSection === "delegate"}
          onclick={() => navigateTo("delegate")}
          aria-current={activeSection === "delegate" ? "page" : undefined}
        >
          <span class="nav-icon" aria-hidden="true">⊕</span>
          <span class="nav-label">Delegate</span>
          {#if busy}
            <span class="nav-live-dot" aria-label="Mind is running"></span>
          {/if}
        </button>
      </li>
      <li>
        <button
          class="nav-item"
          class:active={activeSection === "telemetry"}
          onclick={() => navigateTo("telemetry")}
          aria-current={activeSection === "telemetry" ? "page" : undefined}
        >
          <span class="nav-icon" aria-hidden="true">◬</span>
          <span class="nav-label">Telemetry</span>
          {#if runStats.total > 0}
            <span class="nav-badge">{runStats.total}</span>
          {/if}
        </button>
      </li>
      <li>
        <button
          class="nav-item"
          class:active={activeSection === "history"}
          onclick={() => navigateTo("history")}
          aria-current={activeSection === "history" ? "page" : undefined}
        >
          <span class="nav-icon" aria-hidden="true">◷</span>
          <span class="nav-label">History</span>
          {#if tasks.length > 0}
            <span class="nav-badge">{tasks.length}</span>
          {/if}
        </button>
      </li>
      <li>
        <button
          class="nav-item"
          class:active={activeSection === "memory"}
          onclick={() => navigateTo("memory")}
          aria-current={activeSection === "memory" ? "page" : undefined}
        >
          <span class="nav-icon" aria-hidden="true">⬡</span>
          <span class="nav-label">Memory</span>
          {#if memories.length > 0}
            <span class="nav-badge">{memories.length}</span>
          {/if}
        </button>
      </li>
    </ul>

    {#if selectedMind}
      <div class="sidebar-mind-info">
        <span class="sidebar-mind-label">Active Mind</span>
        <span class="sidebar-mind-name">{selectedMind.name}</span>
      </div>
    {/if}

    {#if busy}
      <div class="sidebar-live" aria-live="polite">
        <span class="live-orb"></span>
        <span class="live-text">Mind running</span>
      </div>
    {/if}

    <div class="sidebar-footer">
      <span class="sidebar-version">FlowForge v0.1</span>
    </div>
  </nav>

  <!-- Mobile hamburger -->
  <button
    class="mobile-nav-toggle"
    onclick={() => (navOpen = !navOpen)}
    aria-label="Toggle navigation"
    aria-expanded={navOpen}
  >
    <span class="toggle-bar"></span>
    <span class="toggle-bar"></span>
    <span class="toggle-bar"></span>
  </button>

  <!-- ── Main content ── -->
  <main class="main-content">

    {#if error}
      <div class="error-banner" role="alert">
        <span class="error-icon" aria-hidden="true">⚠</span>
        <span>{error}</span>
        <button type="button" class="error-dismiss" onclick={() => (error = "")}>×</button>
      </div>
    {/if}

    <!-- ════════════════════════════════════════
         Section: Minds
         ════════════════════════════════════════ -->
    <div class="section" class:section-hidden={activeSection !== "minds"} aria-hidden={activeSection !== "minds"}>
      <div class="section-header">
        <h1 class="section-title">Minds</h1>
        <p class="section-desc">Create and configure persistent AI minds with distinct personalities and memory.</p>
      </div>

      <div class="two-col">

        <!-- Create Mind -->
        <section class="card">
          <h2 class="card-heading">
            <span class="heading-glyph">⊕</span> Create Mind
          </h2>
          <form class="field-grid" onsubmit={onCreateMind}>
            <label class="field">
              <span class="field-label">Name</span>
              <input bind:value={newMindName} placeholder="Mind name" />
            </label>

            <label class="field">
              <span class="field-label">Personality</span>
              <input bind:value={newMindPersonality} placeholder="How this Mind behaves" />
            </label>

            <label class="field full">
              <span class="field-label">System prompt override</span>
              <textarea rows="3" bind:value={newMindSystemPrompt} placeholder="Optional operating rules"></textarea>
            </label>

            <label class="field full">
              <span class="field-label">Preferences (JSON object)</span>
              <textarea rows="3" bind:value={newMindPreferences} placeholder="Example: tone=direct, depth=concise"></textarea>
            </label>

            <div class="actions full">
              <button type="submit" class="btn-primary">Create Mind</button>
            </div>
          </form>
        </section>

        <!-- Mind Profile -->
        <section class="card">
          <h2 class="card-heading">
            <span class="heading-glyph">◉</span> Mind Profile
          </h2>

          <div class="mind-selector-row">
            <select bind:value={selectedMindId}>
              <option value="">Select a Mind</option>
              {#each minds as mind (mind.id)}
                <option value={mind.id}>{mind.name} ({mind.id})</option>
              {/each}
            </select>
            <button type="button" class="btn-ghost" onclick={() => void refreshMinds()}>Refresh</button>
          </div>

          {#if selectedMind}
            <div class="mind-meta">
              <div class="meta-block">
                <span class="meta-label">Created</span>
                <span class="meta-value">{prettyDate(selectedMind.created_at)}</span>
              </div>
              <div class="meta-block">
                <span class="meta-label">Personality</span>
                <span class="meta-value">{selectedMind.personality || "Not set"}</span>
              </div>
              <div class="meta-block full">
                <span class="meta-label">Preferences</span>
                <pre class="meta-pre">{formatPreferences(selectedMind)}</pre>
              </div>
              <div class="meta-block full">
                <span class="meta-label">System prompt</span>
                <p class="meta-value">{selectedMind.system_prompt || "No custom system prompt"}</p>
              </div>
            </div>
          {:else}
            <span class="muted">Create or select a Mind to begin.</span>
          {/if}
        </section>

      </div>
    </div>

    <!-- ════════════════════════════════════════
         Section: Delegate
         ════════════════════════════════════════ -->
    <div class="section" class:section-hidden={activeSection !== "delegate"} aria-hidden={activeSection !== "delegate"}>
      <div class="section-header">
        <h1 class="section-title">Delegate Task</h1>
        <p class="section-desc">Send a task brief to the selected Mind and watch it execute in real time.</p>
      </div>

      <section class="card">
        <h2 class="card-heading">
          <span class="heading-glyph">⊕</span> Task Brief
          {#if busy}
            <span style="margin-left: auto; display: flex; align-items: center; gap: 8px;">
              <span class="live-orb" style="width: 8px; height: 8px;"></span>
              <span style="font-family: var(--font-heading); font-size: 0.62rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--gold);">Running…</span>
            </span>
          {/if}
        </h2>

        <form class="field-grid" onsubmit={onDelegate}>
          <label class="field">
            <span class="field-label">Mind</span>
            <select bind:value={selectedMindId}>
              <option value="">Select a Mind</option>
              {#each minds as mind (mind.id)}
                <option value={mind.id}>{mind.name}</option>
              {/each}
            </select>
          </label>

          <label class="field">
            <span class="field-label">Team</span>
            <input bind:value={teamName} placeholder="default" />
          </label>

          <label class="field full">
            <span class="field-label">Task description</span>
            <textarea rows="5" bind:value={taskText} placeholder="Describe what the Mind should do"></textarea>
          </label>

          <div class="actions full">
            <button type="submit" class="btn-primary" disabled={!selectedMindId || busy}>
              {busy ? "Mind is running…" : "Run Delegation"}
            </button>
            {#if runStats.total > 0}
              <button type="button" class="btn-ghost" onclick={() => navigateTo("telemetry")}>
                View Telemetry →
              </button>
            {/if}
          </div>
        </form>

        <p class="delegate-hint">
          The stream below shows real-time tool calls, sub-agent delegation, and completion status.
          Navigate to Telemetry to inspect the live event feed.
        </p>
      </section>
    </div>

    <!-- ════════════════════════════════════════
         Section: Telemetry
         ════════════════════════════════════════ -->
    <div class="section" class:section-hidden={activeSection !== "telemetry"} aria-hidden={activeSection !== "telemetry"}>
      <div class="section-header">
        <h1 class="section-title">Run Telemetry</h1>
        <p class="section-desc">Live event stream, tool registry, and sub-agent delegation tree from the last run.</p>
      </div>

      <div class="two-col">

        <!-- Event feed + stats -->
        <section class="card">
          <h2 class="card-heading">
            <span class="heading-glyph">◬</span> Event Feed
          </h2>

          <!-- Stats -->
          <div class="stats-grid">
            <div class="stat-card">
              <span class="stat-label">Events</span>
              <span class="stat-value">{runStats.total}</span>
            </div>
            <div class="stat-card">
              <span class="stat-label">Text</span>
              <span class="stat-value">{runStats.text}</span>
            </div>
            <div class="stat-card">
              <span class="stat-label">Tool calls</span>
              <span class="stat-value">{runStats.toolUse}</span>
            </div>
            <div class="stat-card">
              <span class="stat-label">Results</span>
              <span class="stat-value">{runStats.toolResult}</span>
            </div>
            <div class="stat-card">
              <span class="stat-label">Errors</span>
              <span class="stat-value {statValueClass('errors', runStats.errors)}">{runStats.errors}</span>
            </div>
            <div class="stat-card">
              <span class="stat-label">Status</span>
              <span class="stat-value {statValueClass('status', runStats.status)}" style="font-size: 1rem; padding-top: 6px;">{runStats.status}</span>
            </div>
          </div>

          <!-- Tool registry chips -->
          {#if runToolRegistry.length > 0}
            <div class="chip-row" style="margin-bottom: 10px;">
              {#each runToolRegistry as tool (tool)}
                <span class="chip">{tool}</span>
              {/each}
            </div>
          {/if}

          <!-- Live event panel -->
          <div class="panel panel-tall">
            {#if runEventViews.length === 0}
              <span class="muted">No run events yet — delegate a task to see the stream.</span>
            {:else}
              {#each runEventViews as item (item.id)}
                {@const isLong = item.fullDetail.length > 260}
                {@const isExpanded = expandedEvents.has(item.id)}
                <article class="event-row" data-severity={item.severity}>
                  <div class="event-header">
                    <span class="event-type-tag">{item.type}</span>
                    {#if item.timestamp}
                      <span class="event-time">{prettyDate(item.timestamp)}</span>
                    {/if}
                  </div>
                  <strong class="event-title">{item.title}</strong>
                  <p class="event-detail" class:clamped={isLong && !isExpanded}>
                    {isExpanded ? item.fullDetail : item.detail}
                  </p>
                  {#if isLong}
                    <button type="button" class="event-expand" onclick={() => toggleExpand(item.id)}>
                      {isExpanded ? "▲ collapse" : "▼ show more"}
                    </button>
                  {/if}
                </article>
              {/each}

              <!-- Live composing indicator: replaces text_delta flood -->
              {#if busy && liveTypingText}
                <div class="composing-block">
                  <div class="composing-header">
                    <span class="composing-dot"></span>
                    <span class="composing-dot"></span>
                    <span class="composing-dot"></span>
                    <span class="composing-label">Mind composing</span>
                  </div>
                  <p class="composing-text">{liveTypingText}</p>
                </div>
              {:else if busy}
                <div class="composing-block composing-idle">
                  <div class="composing-header">
                    <span class="composing-dot"></span>
                    <span class="composing-dot"></span>
                    <span class="composing-dot"></span>
                    <span class="composing-label">Mind is working</span>
                  </div>
                </div>
              {/if}
            {/if}
          </div>
        </section>

        <!-- Delegation tree + memory context -->
        <section class="card">
          <h2 class="card-heading">
            <span class="heading-glyph">⊕</span> Delegation Tree
          </h2>

          <div class="panel">
            {#if spawnRuns.length === 0}
              <span class="muted">No sub-agent delegation detected in this run.</span>
            {:else}
              {#each spawnRuns as run (run.callId)}
                <article class="spawn-card" data-error={run.isError}>
                  <div class="spawn-head">
                    <span class="spawn-id">{run.callId}</span>
                    <span class="spawn-turns">max_turns={run.maxTurns}</span>
                  </div>
                  <p><strong>Objective:</strong> {run.objective}</p>
                  <p><strong>Result:</strong> {run.result}</p>
                </article>
              {/each}
            {/if}
          </div>

          <p class="subheading">Memory context used</p>
          <div class="chip-row">
            {#if runMemoryContextIds.length === 0}
              <span class="muted" style="padding: 0; text-align: left;">No memory_context event captured.</span>
            {:else}
              {#each runMemoryContextIds as memId (memId)}
                <span class="chip">{memId}</span>
              {/each}
            {/if}
          </div>
        </section>

      </div>
    </div>

    <!-- ════════════════════════════════════════
         Section: History
         ════════════════════════════════════════ -->
    <div class="section" class:section-hidden={activeSection !== "history"} aria-hidden={activeSection !== "history"}>
      <div class="section-header">
        <h1 class="section-title">Task History</h1>
        <p class="section-desc">Browse persisted tasks and replay their full event traces.</p>
      </div>

      <div class="two-col">

        <!-- Task list -->
        <section class="card">
          <h2 class="card-heading">
            <span class="heading-glyph">◷</span> Tasks
          </h2>

          <div class="row">
            <button
              type="button"
              class="btn-ghost"
              disabled={!selectedMindId}
              onclick={() => selectedMindId && void refreshTasks(selectedMindId)}
            >
              Refresh tasks
            </button>
          </div>

          <div class="panel task-panel">
            {#if tasks.length === 0}
              <span class="muted">No tasks recorded for this Mind yet.</span>
            {:else}
              {#each tasks as task (task.id)}
                <button
                  type="button"
                  class="task-item"
                  class:selected={task.id === selectedTaskId}
                  onclick={() => void loadTrace(task.id)}
                >
                  <div class="task-top">
                    <span class="status-pill" data-status={task.status}>{task.status}</span>
                    <span class="task-id">{task.id}</span>
                  </div>
                  <span class="task-description">{task.description}</span>
                  <p class="task-preview">{taskPreview(task)}</p>
                  <div class="task-times">
                    <span>Created: {prettyDate(task.created_at)}</span>
                    <span>Completed: {prettyDate(task.completed_at)}</span>
                  </div>
                </button>
              {/each}
            {/if}
          </div>
        </section>

        <!-- Trace replay -->
        <section class="card">
          <h2 class="card-heading">
            <span class="heading-glyph">◬</span> Trace Replay
            {#if selectedTaskId}
              <span style="font-family: var(--font-mono); font-size: 0.62rem; color: var(--ink-3); margin-left: 4px; font-weight: normal; letter-spacing: 0;">({selectedTaskId})</span>
            {/if}
          </h2>

          <div class="panel panel-tall">
            {#if !trace}
              <span class="muted">Select a task to inspect its persisted event trace.</span>
            {:else}
              {#each traceEventViews as item (item.id)}
                {@const traceId = `t-${item.id}`}
                {@const isLong = item.fullDetail.length > 260}
                {@const isExpanded = expandedEvents.has(traceId)}
                <article class="event-row" data-severity={item.severity}>
                  <div class="event-header">
                    <span class="event-type-tag">{item.type}</span>
                    {#if item.timestamp}
                      <span class="event-time">{prettyDate(item.timestamp)}</span>
                    {/if}
                  </div>
                  <strong class="event-title">{item.title}</strong>
                  <p class="event-detail" class:clamped={isLong && !isExpanded}>
                    {isExpanded ? item.fullDetail : item.detail}
                  </p>
                  {#if isLong}
                    <button type="button" class="event-expand" onclick={() => toggleExpand(traceId)}>
                      {isExpanded ? "▲ collapse" : "▼ show more"}
                    </button>
                  {/if}
                </article>
              {/each}
            {/if}
          </div>
        </section>

      </div>
    </div>

    <!-- ════════════════════════════════════════
         Section: Memory
         ════════════════════════════════════════ -->
    <div class="section" class:section-hidden={activeSection !== "memory"} aria-hidden={activeSection !== "memory"}>
      <div class="section-header">
        <h1 class="section-title">Memory Vault</h1>
        <p class="section-desc">Persistent memory entries stored by this Mind, searchable by content, category, and keyword.</p>
      </div>

      <section class="card">
        <h2 class="card-heading">
          <span class="heading-glyph">⬡</span> Entries
          {#if filteredMemories.length !== memories.length}
            <span style="font-family: var(--font-mono); font-size: 0.62rem; color: var(--ink-3); margin-left: 4px; font-weight: normal; letter-spacing: 0;">{filteredMemories.length} / {memories.length}</span>
          {/if}
        </h2>

        <div class="memory-search-row">
          <label class="field field-compact">
            <span class="field-label">Category</span>
            <select bind:value={memoryCategory}>
              {#each memoryCategories as cat (cat)}
                <option value={cat}>{cat}</option>
              {/each}
            </select>
          </label>

          <label class="field field-grow">
            <span class="field-label">Search</span>
            <input bind:value={memorySearch} placeholder="Filter by content or keyword" />
          </label>

          <div class="actions" style="align-self: flex-end;">
            <button
              type="button"
              class="btn-ghost"
              disabled={!selectedMindId}
              onclick={() => selectedMindId && void refreshMemories(selectedMindId)}
            >
              Refresh
            </button>
          </div>
        </div>

        <div class="panel memory-panel">
          {#if filteredMemories.length === 0}
            <span class="muted">No memories match the current filters.</span>
          {:else}
            {#each filteredMemories as memory (memory.id)}
              <article class="memory-card" data-context-hit={runMemoryContextIds.includes(memory.id)}>
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
      </section>
    </div>

  </main>
</div>
