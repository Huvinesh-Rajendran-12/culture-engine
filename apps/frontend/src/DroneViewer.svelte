<script lang="ts">
  // ── Types ──────────────────────────────────────────────────────────────────
  type Drone = {
    id: string;
    mind_id: string;
    task_id: string;
    objective: string;
    status: "pending" | "running" | "completed" | "failed";
    result: string | null;
    created_at: string;
    completed_at: string | null;
  };

  type DroneTraceEvent = {
    id?: string;
    type: string;
    seq?: number;
    ts?: string;
    trace_id?: string;
    content: unknown;
    timestamp?: string;
  };

  type DroneTrace = {
    drone_id: string;
    mind_id: string;
    events: DroneTraceEvent[];
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

  // ── Props ──────────────────────────────────────────────────────────────────
  let {
    mindId = "",
    tasks = [] as Task[],
  }: {
    mindId: string;
    tasks: Task[];
  } = $props();

  // ── State ──────────────────────────────────────────────────────────────────
  let selectedTaskId = $state("");
  let drones = $state<Drone[]>([]);
  let selectedDroneId = $state("");
  let droneTrace = $state<DroneTrace | null>(null);
  let loading = $state(false);
  let traceLoading = $state(false);
  let error = $state("");
  let expandedTraceEvents = $state<Set<string>>(new Set());

  // ── Derived ────────────────────────────────────────────────────────────────
  let selectedDrone = $derived(drones.find((d) => d.id === selectedDroneId) ?? null);
  let traceEventsByPhase = $derived(groupEventsByPhase(droneTrace?.events ?? []));

  // ── Effects ────────────────────────────────────────────────────────────────
  $effect(() => {
    if (selectedTaskId && mindId) {
      void loadDrones(mindId, selectedTaskId);
    } else {
      drones = [];
      selectedDroneId = "";
      droneTrace = null;
    }
  });

  // ── API ────────────────────────────────────────────────────────────────────
  async function loadDrones(mId: string, tId: string) {
    loading = true;
    error = "";
    try {
      const res = await fetch(`/api/minds/${mId}/tasks/${tId}/drones`);
      if (!res.ok) throw new Error("Failed to load drones");
      drones = await res.json();
      selectedDroneId = "";
      droneTrace = null;
    } catch (err) {
      error = (err as Error).message;
      drones = [];
    } finally {
      loading = false;
    }
  }

  async function loadDroneTrace(droneId: string) {
    if (!mindId) return;
    traceLoading = true;
    error = "";
    expandedTraceEvents = new Set();
    try {
      const res = await fetch(`/api/minds/${mindId}/drones/${droneId}/trace`);
      if (!res.ok) throw new Error("Failed to load drone trace");
      droneTrace = await res.json();
      selectedDroneId = droneId;
    } catch (err) {
      error = (err as Error).message;
      droneTrace = null;
    } finally {
      traceLoading = false;
    }
  }

  function onSelectDrone(droneId: string) {
    if (selectedDroneId === droneId) {
      // Toggle off
      selectedDroneId = "";
      droneTrace = null;
      return;
    }
    void loadDroneTrace(droneId);
  }

  function goBackToGallery() {
    selectedDroneId = "";
    droneTrace = null;
    expandedTraceEvents = new Set();
  }

  // ── Helpers ────────────────────────────────────────────────────────────────
  function prettyDate(value: string | null | undefined): string {
    if (!value) return "\u2014";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
  }

  function prettyTime(value: string | null | undefined): string {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  function duration(start: string, end: string | null): string {
    if (!end) return "in progress";
    const ms = new Date(end).getTime() - new Date(start).getTime();
    if (ms < 1000) return `${ms}ms`;
    const secs = Math.floor(ms / 1000);
    if (secs < 60) return `${secs}s`;
    const mins = Math.floor(secs / 60);
    const remSecs = secs % 60;
    return `${mins}m ${remSecs}s`;
  }

  function statusMeta(status: string): { label: string; cssClass: string; icon: string } {
    switch (status) {
      case "pending":   return { label: "Awaiting", cssClass: "status-pending", icon: "\u29D7" };
      case "running":   return { label: "In Motion", cssClass: "status-running", icon: "\u2742" };
      case "completed": return { label: "Fulfilled", cssClass: "status-completed", icon: "\u2726" };
      case "failed":    return { label: "Fallen", cssClass: "status-failed", icon: "\u2620" };
      default:          return { label: status, cssClass: "", icon: "\u25C7" };
    }
  }

  function eventIcon(type: string): string {
    const map: Record<string, string> = {
      task_started:   "\u2600",  // sun
      tool_registry:  "\u2692",  // hammer and pick
      tool_use:       "\u2699",  // gear
      tool_result:    "\u2727",  // sparkle
      text:           "\u270D",  // writing hand
      result:         "\u2736",  // six-pointed star
      task_finished:  "\u2605",  // star
      error:          "\u26A0",  // warning
      memory_context: "\u29D6",  // hourglass
      text_delta:     "\u2026",  // ellipsis
    };
    return map[type] ?? "\u25C6";
  }

  function eventPhaseLabel(type: string): string {
    const map: Record<string, string> = {
      task_started:   "Genesis",
      tool_registry:  "Armament",
      tool_use:       "Invocation",
      tool_result:    "Revelation",
      text:           "Utterance",
      text_delta:     "Utterance",
      result:         "Resolution",
      task_finished:  "Culmination",
      error:          "Tribulation",
      memory_context: "Remembrance",
    };
    return map[type] ?? "Act";
  }

  function eventSeverity(type: string, content: unknown): "neutral" | "warm" | "success" | "error" {
    if (type === "error") return "error";
    if (type === "task_finished" || type === "result") return "success";
    if (type === "tool_result") {
      const obj = content && typeof content === "object" ? content as Record<string, unknown> : {};
      return obj.is_error ? "error" : "warm";
    }
    if (type === "tool_use") return "warm";
    return "neutral";
  }

  function asObject(value: unknown): Record<string, unknown> {
    return value && typeof value === "object" && !Array.isArray(value)
      ? (value as Record<string, unknown>)
      : {};
  }

  function compact(value: unknown, max = 300): string {
    const raw = typeof value === "string" ? value : JSON.stringify(value, null, 0);
    if (!raw) return "";
    return raw.length > max ? `${raw.slice(0, max)}\u2026` : raw;
  }

  function fullString(value: unknown): string {
    if (typeof value === "string") return value;
    return JSON.stringify(value, null, 2);
  }

  function formatEventContent(event: DroneTraceEvent): { title: string; detail: string; full: string } {
    const payload = asObject(event.content);
    switch (event.type) {
      case "task_started": {
        const taskId = typeof payload.task_id === "string" ? payload.task_id : "unknown";
        return { title: "The work begins", detail: `Task ${taskId} initiated`, full: `Task ${taskId} initiated` };
      }
      case "tool_registry": {
        const tools = Array.isArray(payload.tools)
          ? payload.tools.filter((t): t is string => typeof t === "string")
          : [];
        return { title: "Tools bestowed", detail: tools.join(", "), full: tools.join(", ") };
      }
      case "tool_use": {
        const toolName = typeof payload.tool === "string" ? payload.tool : "unknown";
        return { title: `Wielding ${toolName}`, detail: compact(payload.input, 200), full: fullString(payload.input) };
      }
      case "tool_result": {
        const isError = Boolean(payload.is_error);
        return {
          title: isError ? "The tool falters" : "The tool speaks",
          detail: compact(payload.result, 200),
          full: fullString(payload.result),
        };
      }
      case "text":
        return {
          title: "The drone speaks",
          detail: typeof event.content === "string" ? event.content : compact(event.content, 300),
          full: typeof event.content === "string" ? event.content : fullString(event.content),
        };
      case "result": {
        const subtype = typeof payload.subtype === "string" ? payload.subtype : "completed";
        return { title: "Final word", detail: `Outcome: ${subtype}`, full: `Outcome: ${subtype}` };
      }
      case "task_finished": {
        const status = typeof payload.status === "string" ? payload.status : "unknown";
        return { title: "The work concludes", detail: `Status: ${status}`, full: `Status: ${status}` };
      }
      case "error":
        return {
          title: "A shadow falls",
          detail: typeof event.content === "string" ? event.content : compact(event.content, 300),
          full: typeof event.content === "string" ? event.content : fullString(event.content),
        };
      default:
        return { title: event.type, detail: compact(event.content, 200), full: fullString(event.content) };
    }
  }

  type PhaseGroup = {
    phase: string;
    events: Array<{ event: DroneTraceEvent; index: number; formatted: ReturnType<typeof formatEventContent>; severity: string }>;
  };

  function groupEventsByPhase(events: DroneTraceEvent[]): PhaseGroup[] {
    const groups: PhaseGroup[] = [];
    let currentPhase = "";
    let currentGroup: PhaseGroup | null = null;

    for (let i = 0; i < events.length; i++) {
      const event = events[i];
      const phase = eventPhaseLabel(event.type);
      if (phase !== currentPhase) {
        currentPhase = phase;
        currentGroup = { phase, events: [] };
        groups.push(currentGroup);
      }
      currentGroup!.events.push({
        event,
        index: i,
        formatted: formatEventContent(event),
        severity: eventSeverity(event.type, event.content),
      });
    }
    return groups;
  }

  function toggleTraceExpand(id: string) {
    const next = new Set(expandedTraceEvents);
    if (next.has(id)) next.delete(id); else next.add(id);
    expandedTraceEvents = next;
  }

  function droneNumber(drone: Drone, list: Drone[]): number {
    return list.indexOf(drone) + 1;
  }

  function romanNumeral(n: number): string {
    const values = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1];
    const numerals = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"];
    let result = "";
    let remaining = n;
    for (let i = 0; i < values.length; i++) {
      while (remaining >= values[i]) {
        result += numerals[i];
        remaining -= values[i];
      }
    }
    return result;
  }
</script>

<div class="dv-root">
  {#if error}
    <div class="dv-error" role="alert">
      <span class="dv-error-icon">{"\u26A0"}</span>
      <span>{error}</span>
      <button type="button" class="dv-error-dismiss" onclick={() => (error = "")}>{"\u00D7"}</button>
    </div>
  {/if}

  <!-- ═══════════════════════════════════════════
       Task Selector — The Patron's Commission
       ═══════════════════════════════════════════ -->
  <div class="dv-commission">
    <div class="dv-commission-header">
      <div class="dv-ornament-left"></div>
      <h2 class="dv-commission-title">Select a Commission</h2>
      <div class="dv-ornament-right"></div>
    </div>
    <p class="dv-commission-subtitle">Choose a task to reveal the drones that served its purpose</p>

    <div class="dv-task-selector">
      <select
        class="dv-task-select"
        bind:value={selectedTaskId}
      >
        <option value="">Choose a task...</option>
        {#each tasks as task (task.id)}
          <option value={task.id}>
            {task.description.length > 70 ? task.description.slice(0, 70) + "\u2026" : task.description}
            ({task.status})
          </option>
        {/each}
      </select>
    </div>
  </div>

  <!-- ═══════════════════════════════════════════
       Drone Gallery — The Hall of Agents
       ═══════════════════════════════════════════ -->
  {#if selectedTaskId && !selectedDroneId}
    <div class="dv-gallery" class:dv-gallery-enter={!loading}>

      {#if loading}
        <div class="dv-loading">
          <div class="dv-loading-orb"></div>
          <span class="dv-loading-text">Summoning the drones...</span>
        </div>
      {:else if drones.length === 0}
        <div class="dv-empty">
          <div class="dv-empty-icon">{"\u2727"}</div>
          <p class="dv-empty-text">No drones were summoned for this commission.</p>
          <p class="dv-empty-hint">The Mind completed this task without delegation.</p>
        </div>
      {:else}
        <div class="dv-gallery-header">
          <div class="dv-flourish-line"></div>
          <h3 class="dv-gallery-title">The Agents of Creation</h3>
          <p class="dv-gallery-count">{drones.length} {drones.length === 1 ? "drone" : "drones"} dispatched</p>
          <div class="dv-flourish-line"></div>
        </div>

        <div class="dv-gallery-grid">
          {#each drones as drone, i (drone.id)}
            {@const meta = statusMeta(drone.status)}
            {@const num = droneNumber(drone, drones)}
            <button
              type="button"
              class="dv-card {meta.cssClass}"
              onclick={() => onSelectDrone(drone.id)}
              style="animation-delay: {i * 120}ms"
            >
              <!-- Card inner glow layer -->
              <div class="dv-card-glow"></div>

              <!-- Numeral -->
              <div class="dv-card-numeral">{romanNumeral(num)}</div>

              <!-- Status orb -->
              <div class="dv-card-orb-wrap">
                <div class="dv-card-orb {meta.cssClass}">
                  <span class="dv-card-orb-icon">{meta.icon}</span>
                </div>
                <span class="dv-card-status-label">{meta.label}</span>
              </div>

              <!-- Objective -->
              <p class="dv-card-objective">{drone.objective}</p>

              <!-- Result preview -->
              {#if drone.result}
                <p class="dv-card-result">{compact(drone.result, 120)}</p>
              {/if}

              <!-- Timestamps -->
              <div class="dv-card-times">
                <span class="dv-card-time">Summoned: {prettyDate(drone.created_at)}</span>
                {#if drone.completed_at}
                  <span class="dv-card-time">Concluded: {prettyDate(drone.completed_at)}</span>
                  <span class="dv-card-duration">{duration(drone.created_at, drone.completed_at)}</span>
                {/if}
              </div>

              <!-- Hover invite -->
              <div class="dv-card-cta">
                <span class="dv-card-cta-text">View Trace</span>
                <span class="dv-card-cta-arrow">{"\u2192"}</span>
              </div>
            </button>
          {/each}
        </div>
      {/if}
    </div>
  {/if}

  <!-- ═══════════════════════════════════════════
       Drone Trace Detail — The Illuminated Scroll
       ═══════════════════════════════════════════ -->
  {#if selectedDroneId}
    <div class="dv-trace-view">

      <!-- Back navigation -->
      <button type="button" class="dv-back" onclick={goBackToGallery}>
        <span class="dv-back-arrow">{"\u2190"}</span>
        <span class="dv-back-text">Return to Gallery</span>
      </button>

      {#if selectedDrone}
        <!-- Drone identity header — the "portrait" -->
        <div class="dv-portrait">
          <div class="dv-portrait-frame">
            <div class="dv-portrait-inner">
              <div class="dv-portrait-glow {statusMeta(selectedDrone.status).cssClass}"></div>
              <div class="dv-portrait-orb {statusMeta(selectedDrone.status).cssClass}">
                <span class="dv-portrait-icon">{statusMeta(selectedDrone.status).icon}</span>
              </div>
            </div>
          </div>

          <div class="dv-portrait-info">
            <span class="dv-portrait-numeral">Drone {romanNumeral(droneNumber(selectedDrone, drones))}</span>
            <h3 class="dv-portrait-objective">{selectedDrone.objective}</h3>
            <div class="dv-portrait-meta">
              <span class="dv-portrait-status {statusMeta(selectedDrone.status).cssClass}">
                {statusMeta(selectedDrone.status).label}
              </span>
              <span class="dv-portrait-sep">{"\u2022"}</span>
              <span class="dv-portrait-time">{duration(selectedDrone.created_at, selectedDrone.completed_at)}</span>
              <span class="dv-portrait-sep">{"\u2022"}</span>
              <span class="dv-portrait-time">{droneTrace?.events.length ?? 0} events</span>
            </div>

            {#if selectedDrone.result}
              <div class="dv-portrait-result">
                <span class="dv-portrait-result-label">Final Word</span>
                <p class="dv-portrait-result-text">{selectedDrone.result}</p>
              </div>
            {/if}
          </div>
        </div>
      {/if}

      <!-- The Scroll — event trace timeline -->
      {#if traceLoading}
        <div class="dv-loading">
          <div class="dv-loading-orb"></div>
          <span class="dv-loading-text">Unrolling the scroll...</span>
        </div>
      {:else if droneTrace}
        <div class="dv-scroll">
          <div class="dv-scroll-header">
            <div class="dv-scroll-ornament"></div>
            <h4 class="dv-scroll-title">The Chronicle</h4>
            <div class="dv-scroll-ornament"></div>
          </div>

          <div class="dv-timeline">
            <div class="dv-timeline-line"></div>

            {#each traceEventsByPhase as group, gi (gi)}
              <!-- Phase divider -->
              <div class="dv-phase-divider" style="animation-delay: {gi * 80}ms">
                <div class="dv-phase-gem"></div>
                <span class="dv-phase-label">{group.phase}</span>
              </div>

              {#each group.events as entry (entry.index)}
                {@const evtId = `te-${entry.index}`}
                {@const isLong = entry.formatted.full.length > 260}
                {@const isExpanded = expandedTraceEvents.has(evtId)}
                <div
                  class="dv-timeline-event dv-severity-{entry.severity}"
                  style="animation-delay: {(gi * 80) + (entry.index * 40)}ms"
                >
                  <!-- Timeline node -->
                  <div class="dv-timeline-node">
                    <span class="dv-timeline-icon">{eventIcon(entry.event.type)}</span>
                  </div>

                  <!-- Event content -->
                  <div class="dv-timeline-content">
                    <div class="dv-timeline-head">
                      <span class="dv-timeline-type">{entry.event.type}</span>
                      {#if entry.event.ts || entry.event.timestamp}
                        <span class="dv-timeline-time">{prettyTime(entry.event.ts || entry.event.timestamp)}</span>
                      {/if}
                    </div>
                    <strong class="dv-timeline-title">{entry.formatted.title}</strong>
                    <p class="dv-timeline-detail" class:dv-clamped={isLong && !isExpanded}>
                      {isExpanded ? entry.formatted.full : entry.formatted.detail}
                    </p>
                    {#if isLong}
                      <button type="button" class="dv-timeline-expand" onclick={() => toggleTraceExpand(evtId)}>
                        {isExpanded ? "\u25B2 conceal" : "\u25BC reveal more"}
                      </button>
                    {/if}
                  </div>
                </div>
              {/each}
            {/each}

            <!-- Terminal flourish -->
            <div class="dv-timeline-end">
              <div class="dv-timeline-end-gem"></div>
              <span class="dv-timeline-end-text">Finis</span>
            </div>
          </div>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Empty state when no task selected -->
  {#if !selectedTaskId}
    <div class="dv-empty-state">
      <div class="dv-empty-state-artwork">
        <div class="dv-empty-ring dv-ring-1"></div>
        <div class="dv-empty-ring dv-ring-2"></div>
        <div class="dv-empty-ring dv-ring-3"></div>
        <div class="dv-empty-core">{"\u2742"}</div>
      </div>
      <p class="dv-empty-state-text">Select a commission above to reveal its agents</p>
    </div>
  {/if}
</div>

<style>
  /* ═══════════════════════════════════════════════════════════════════
     THE DRONE VIEWER — A Renaissance Vision
     ═══════════════════════════════════════════════════════════════════ */

  /* ── Extended palette for the Renaissance aesthetic ── */
  .dv-root {
    --dv-parchment: #f2ead6;
    --dv-sepia: #cac2a6;
    --dv-umber: #7d7464;
    --dv-gold: #e5a93a;
    --dv-gold-bright: #f4cb7d;
    --dv-gold-dim: #8c6624;
    --dv-burgundy: #8b2942;
    --dv-burgundy-light: #cc5a6a;
    --dv-ultramarine: #1a3a6e;
    --dv-ultramarine-light: #4a7ec2;
    --dv-sienna: #a0522d;
    --dv-sienna-light: #cd8c60;
    --dv-verdaccio: #6a7a3a;
    --dv-verdaccio-light: #9ab05a;
    --dv-ivory: #fef5db;
    --dv-obsidian: #0a0c14;
    --dv-panel: #111320;
    --dv-panel-lift: #181a2c;

    font-family: var(--font-body, "EB Garamond", Georgia, serif);
    color: var(--dv-parchment);
  }

  /* ── Commission / Task Selector ── */
  .dv-commission {
    text-align: center;
    margin-bottom: 32px;
    position: relative;
  }

  .dv-commission-header {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 16px;
    margin-bottom: 8px;
  }

  .dv-ornament-left,
  .dv-ornament-right {
    width: 60px;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--dv-gold-dim), transparent);
    position: relative;
  }

  .dv-ornament-left::after,
  .dv-ornament-right::after {
    content: "\u2726";
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    font-size: 0.6rem;
    color: var(--dv-gold-dim);
  }

  .dv-ornament-left::after { right: -4px; }
  .dv-ornament-right::after { left: -4px; }

  .dv-commission-title {
    font-family: var(--font-display, "Cinzel Decorative", serif);
    font-size: 0.85rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--dv-gold);
    filter: drop-shadow(0 0 8px rgba(229, 169, 58, 0.3));
  }

  .dv-commission-subtitle {
    font-size: 0.92rem;
    color: var(--dv-sepia);
    font-style: italic;
    margin-bottom: 16px;
  }

  .dv-task-selector {
    max-width: 520px;
    margin: 0 auto;
  }

  .dv-task-select {
    width: 100%;
    padding: 12px 16px;
    border-radius: 8px;
    border: 1px solid rgba(229, 169, 58, 0.3);
    background: linear-gradient(135deg, rgba(17, 19, 32, 0.95), rgba(10, 12, 20, 0.98));
    color: var(--dv-parchment);
    font-family: var(--font-body, "EB Garamond", Georgia, serif);
    font-size: 0.95rem;
    cursor: pointer;
    transition: border-color 200ms, box-shadow 200ms;
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath d='M2 4l4 4 4-4' stroke='%23e5a93a' stroke-width='1.5' fill='none'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 14px center;
  }

  .dv-task-select:focus {
    border-color: rgba(229, 169, 58, 0.65);
    box-shadow: 0 0 0 3px rgba(229, 169, 58, 0.12), 0 0 20px rgba(229, 169, 58, 0.08);
    outline: none;
  }

  .dv-task-select option {
    background: #111320;
    color: var(--dv-parchment);
  }

  /* ── Error Banner ── */
  .dv-error {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    margin-bottom: 18px;
    border-radius: 8px;
    border: 1px solid rgba(139, 41, 66, 0.5);
    background: rgba(139, 41, 66, 0.15);
    color: var(--dv-burgundy-light);
    font-size: 0.88rem;
  }

  .dv-error-icon { font-size: 1rem; }
  .dv-error-dismiss {
    margin-left: auto;
    opacity: 0.6;
    font-size: 1.15rem;
    line-height: 1;
    padding: 2px 5px;
    color: inherit;
  }
  .dv-error-dismiss:hover { opacity: 1; }

  /* ── Loading State ── */
  .dv-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 48px 0;
  }

  .dv-loading-orb {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 35%, var(--dv-gold-bright), var(--dv-gold-dim));
    box-shadow:
      0 0 20px rgba(229, 169, 58, 0.5),
      0 0 60px rgba(229, 169, 58, 0.2);
    animation: dv-orb-breathe 2s ease-in-out infinite;
  }

  @keyframes dv-orb-breathe {
    0%, 100% { transform: scale(1); box-shadow: 0 0 20px rgba(229, 169, 58, 0.5), 0 0 60px rgba(229, 169, 58, 0.2); }
    50% { transform: scale(1.15); box-shadow: 0 0 30px rgba(229, 169, 58, 0.65), 0 0 80px rgba(229, 169, 58, 0.3); }
  }

  .dv-loading-text {
    font-family: var(--font-heading, "Cinzel", serif);
    font-size: 0.72rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--dv-gold-dim);
    animation: dv-text-pulse 2s ease-in-out infinite;
  }

  @keyframes dv-text-pulse {
    0%, 100% { opacity: 0.5; }
    50% { opacity: 1; }
  }

  /* ── Empty State ── */
  .dv-empty {
    text-align: center;
    padding: 48px 24px;
  }

  .dv-empty-icon {
    font-size: 2.2rem;
    color: var(--dv-gold-dim);
    opacity: 0.5;
    margin-bottom: 12px;
    filter: drop-shadow(0 0 14px rgba(229, 169, 58, 0.3));
  }

  .dv-empty-text {
    font-size: 1.05rem;
    color: var(--dv-sepia);
    margin-bottom: 6px;
  }

  .dv-empty-hint {
    font-size: 0.88rem;
    color: var(--dv-umber);
    font-style: italic;
  }

  /* ── Gallery ── */
  .dv-gallery {
    animation: dv-fade-up 500ms ease-out;
  }

  @keyframes dv-fade-up {
    from { opacity: 0; transform: translateY(14px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .dv-gallery-header {
    text-align: center;
    margin-bottom: 28px;
  }

  .dv-flourish-line {
    width: 80px;
    height: 1px;
    margin: 0 auto 12px;
    background: linear-gradient(90deg, transparent, var(--dv-gold-dim), var(--dv-gold), var(--dv-gold-dim), transparent);
  }

  .dv-gallery-title {
    font-family: var(--font-display, "Cinzel Decorative", serif);
    font-size: clamp(1.1rem, 2.4vw, 1.5rem);
    letter-spacing: 0.14em;
    color: var(--dv-gold);
    margin-bottom: 6px;
    filter: drop-shadow(0 0 12px rgba(229, 169, 58, 0.25));
  }

  .dv-gallery-count {
    font-family: var(--font-heading, "Cinzel", serif);
    font-size: 0.68rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--dv-umber);
  }

  .dv-gallery-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
  }

  /* ── Drone Card — The Portrait ── */
  .dv-card {
    position: relative;
    display: flex;
    flex-direction: column;
    padding: 24px 22px 20px;
    border-radius: 14px;
    border: 1px solid rgba(229, 169, 58, 0.2);
    background:
      linear-gradient(155deg, rgba(24, 26, 44, 0.95) 0%, rgba(14, 16, 28, 0.98) 100%);
    text-align: left;
    cursor: pointer;
    overflow: hidden;
    transition: transform 300ms cubic-bezier(0.4, 0, 0.2, 1), border-color 300ms, box-shadow 300ms;
    animation: dv-card-enter 600ms ease-out both;

    /* Chiaroscuro lighting — directional highlight */
    box-shadow:
      0 8px 32px rgba(0, 0, 0, 0.55),
      inset 0 1px 0 rgba(255, 255, 255, 0.04),
      inset -40px -20px 60px rgba(0, 0, 0, 0.15);
  }

  @keyframes dv-card-enter {
    from { opacity: 0; transform: translateY(20px) scale(0.97); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }

  .dv-card:hover {
    transform: translateY(-4px);
    border-color: rgba(229, 169, 58, 0.45);
    box-shadow:
      0 16px 48px rgba(0, 0, 0, 0.6),
      0 0 40px rgba(229, 169, 58, 0.08),
      inset 0 1px 0 rgba(255, 255, 255, 0.06);
  }

  .dv-card-glow {
    position: absolute;
    top: -30%;
    left: -20%;
    width: 70%;
    height: 70%;
    border-radius: 50%;
    pointer-events: none;
    opacity: 0;
    transition: opacity 500ms;
  }

  .dv-card:hover .dv-card-glow {
    opacity: 1;
  }

  .dv-card.status-completed .dv-card-glow {
    background: radial-gradient(circle, rgba(74, 126, 194, 0.12) 0%, transparent 70%);
  }

  .dv-card.status-running .dv-card-glow {
    background: radial-gradient(circle, rgba(229, 169, 58, 0.15) 0%, transparent 70%);
  }

  .dv-card.status-failed .dv-card-glow {
    background: radial-gradient(circle, rgba(139, 41, 66, 0.12) 0%, transparent 70%);
  }

  .dv-card.status-pending .dv-card-glow {
    background: radial-gradient(circle, rgba(154, 127, 208, 0.1) 0%, transparent 70%);
  }

  /* Numeral watermark */
  .dv-card-numeral {
    position: absolute;
    top: 8px;
    right: 14px;
    font-family: var(--font-display, "Cinzel Decorative", serif);
    font-size: 2.2rem;
    color: rgba(229, 169, 58, 0.06);
    line-height: 1;
    pointer-events: none;
    user-select: none;
  }

  /* Status orb */
  .dv-card-orb-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;
  }

  .dv-card-orb {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    flex-shrink: 0;
  }

  .dv-card-orb.status-completed {
    background: radial-gradient(circle at 35% 35%, #6ea9d8, #2a5a8e);
    box-shadow: 0 0 14px rgba(110, 169, 216, 0.5), 0 0 40px rgba(110, 169, 216, 0.15);
  }

  .dv-card-orb.status-running {
    background: radial-gradient(circle at 35% 35%, var(--dv-gold-bright), var(--dv-gold-dim));
    box-shadow: 0 0 14px rgba(229, 169, 58, 0.55), 0 0 40px rgba(229, 169, 58, 0.2);
    animation: dv-orb-breathe 2s ease-in-out infinite;
  }

  .dv-card-orb.status-failed {
    background: radial-gradient(circle at 35% 35%, var(--dv-burgundy-light), #5a1020);
    box-shadow: 0 0 14px rgba(139, 41, 66, 0.55), 0 0 40px rgba(139, 41, 66, 0.2);
  }

  .dv-card-orb.status-pending {
    background: radial-gradient(circle at 35% 35%, #9a7fd0, #5a3f80);
    box-shadow: 0 0 14px rgba(154, 127, 208, 0.4), 0 0 40px rgba(154, 127, 208, 0.12);
    animation: dv-orb-breathe 3s ease-in-out infinite;
  }

  .dv-card-orb-icon {
    font-size: 0.85rem;
    color: white;
    filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
    line-height: 1;
  }

  .dv-card-status-label {
    font-family: var(--font-heading, "Cinzel", serif);
    font-size: 0.62rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--dv-sepia);
  }

  .dv-card-objective {
    font-size: 1.02rem;
    line-height: 1.55;
    color: var(--dv-parchment);
    margin-bottom: 10px;
    flex: 1;
  }

  .dv-card-result {
    font-family: var(--font-mono, monospace);
    font-size: 0.72rem;
    color: var(--dv-umber);
    background: rgba(0, 0, 0, 0.3);
    border-radius: 6px;
    padding: 8px 10px;
    margin-bottom: 10px;
    line-height: 1.45;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .dv-card-times {
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin-bottom: 10px;
  }

  .dv-card-time {
    font-family: var(--font-mono, monospace);
    font-size: 0.62rem;
    color: var(--dv-umber);
    letter-spacing: 0.04em;
  }

  .dv-card-duration {
    font-family: var(--font-heading, "Cinzel", serif);
    font-size: 0.58rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--dv-gold-dim);
    margin-top: 2px;
  }

  .dv-card-cta {
    display: flex;
    align-items: center;
    gap: 6px;
    opacity: 0;
    transform: translateX(-6px);
    transition: opacity 300ms, transform 300ms;
    margin-top: auto;
    padding-top: 8px;
    border-top: 1px solid rgba(229, 169, 58, 0.1);
  }

  .dv-card:hover .dv-card-cta {
    opacity: 1;
    transform: translateX(0);
  }

  .dv-card-cta-text {
    font-family: var(--font-heading, "Cinzel", serif);
    font-size: 0.6rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--dv-gold);
  }

  .dv-card-cta-arrow {
    font-size: 0.9rem;
    color: var(--dv-gold);
    transition: transform 200ms;
  }

  .dv-card:hover .dv-card-cta-arrow {
    transform: translateX(3px);
  }

  /* ── Trace Detail View ── */
  .dv-trace-view {
    animation: dv-fade-up 500ms ease-out;
  }

  .dv-back {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    border-radius: 8px;
    border: 1px solid rgba(229, 169, 58, 0.2);
    background: rgba(229, 169, 58, 0.06);
    color: var(--dv-gold-dim);
    margin-bottom: 24px;
    transition: background 200ms, border-color 200ms, color 200ms;
  }

  .dv-back:hover {
    background: rgba(229, 169, 58, 0.12);
    border-color: rgba(229, 169, 58, 0.4);
    color: var(--dv-gold);
  }

  .dv-back-arrow { font-size: 1rem; }
  .dv-back-text {
    font-family: var(--font-heading, "Cinzel", serif);
    font-size: 0.64rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  /* ── Portrait (Drone Detail Header) ── */
  .dv-portrait {
    display: flex;
    gap: 28px;
    align-items: flex-start;
    margin-bottom: 36px;
    padding: 28px 24px;
    border-radius: 14px;
    border: 1px solid rgba(229, 169, 58, 0.18);
    background:
      radial-gradient(ellipse at 15% 20%, rgba(229, 169, 58, 0.06) 0%, transparent 50%),
      linear-gradient(155deg, rgba(24, 26, 44, 0.95), rgba(10, 12, 20, 0.98));
    box-shadow:
      0 12px 40px rgba(0, 0, 0, 0.5),
      inset 0 1px 0 rgba(255, 255, 255, 0.03);
  }

  .dv-portrait-frame {
    flex-shrink: 0;
    width: 80px;
    height: 80px;
    border-radius: 50%;
    border: 2px solid rgba(229, 169, 58, 0.25);
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    background: rgba(0, 0, 0, 0.3);

    /* Ornamental double ring */
    box-shadow:
      0 0 0 4px rgba(10, 12, 20, 0.9),
      0 0 0 5px rgba(229, 169, 58, 0.12);
  }

  .dv-portrait-inner {
    position: relative;
    width: 56px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .dv-portrait-glow {
    position: absolute;
    inset: -12px;
    border-radius: 50%;
    filter: blur(16px);
    opacity: 0.5;
  }

  .dv-portrait-glow.status-completed { background: rgba(110, 169, 216, 0.35); }
  .dv-portrait-glow.status-running { background: rgba(229, 169, 58, 0.35); animation: dv-orb-breathe 2.5s ease-in-out infinite; }
  .dv-portrait-glow.status-failed { background: rgba(139, 41, 66, 0.35); }
  .dv-portrait-glow.status-pending { background: rgba(154, 127, 208, 0.3); }

  .dv-portrait-orb {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    z-index: 1;
  }

  .dv-portrait-orb.status-completed {
    background: radial-gradient(circle at 35% 35%, #7ab8e8, #2a5a8e);
    box-shadow: 0 0 20px rgba(110, 169, 216, 0.5);
  }

  .dv-portrait-orb.status-running {
    background: radial-gradient(circle at 35% 35%, var(--dv-gold-bright), var(--dv-gold-dim));
    box-shadow: 0 0 20px rgba(229, 169, 58, 0.55);
    animation: dv-orb-breathe 2s ease-in-out infinite;
  }

  .dv-portrait-orb.status-failed {
    background: radial-gradient(circle at 35% 35%, var(--dv-burgundy-light), #5a1020);
    box-shadow: 0 0 20px rgba(139, 41, 66, 0.5);
  }

  .dv-portrait-orb.status-pending {
    background: radial-gradient(circle at 35% 35%, #aa92e0, #5a3f80);
    box-shadow: 0 0 20px rgba(154, 127, 208, 0.4);
  }

  .dv-portrait-icon {
    font-size: 1.3rem;
    color: white;
    filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.4));
  }

  .dv-portrait-info {
    flex: 1;
    min-width: 0;
  }

  .dv-portrait-numeral {
    font-family: var(--font-display, "Cinzel Decorative", serif);
    font-size: 0.66rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--dv-gold-dim);
    display: block;
    margin-bottom: 4px;
  }

  .dv-portrait-objective {
    font-family: var(--font-body, "EB Garamond", Georgia, serif);
    font-size: 1.2rem;
    line-height: 1.5;
    color: var(--dv-parchment);
    margin-bottom: 10px;
  }

  .dv-portrait-meta {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 14px;
  }

  .dv-portrait-status {
    font-family: var(--font-heading, "Cinzel", serif);
    font-size: 0.6rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 999px;
  }

  .dv-portrait-status.status-completed {
    color: #9ac7eb;
    background: rgba(110, 169, 216, 0.15);
    border: 1px solid rgba(110, 169, 216, 0.3);
  }

  .dv-portrait-status.status-running {
    color: var(--dv-gold-bright);
    background: rgba(229, 169, 58, 0.15);
    border: 1px solid rgba(229, 169, 58, 0.3);
  }

  .dv-portrait-status.status-failed {
    color: var(--dv-burgundy-light);
    background: rgba(139, 41, 66, 0.15);
    border: 1px solid rgba(139, 41, 66, 0.3);
  }

  .dv-portrait-status.status-pending {
    color: #b8a6e0;
    background: rgba(154, 127, 208, 0.12);
    border: 1px solid rgba(154, 127, 208, 0.25);
  }

  .dv-portrait-sep { color: var(--dv-umber); font-size: 0.5rem; }

  .dv-portrait-time {
    font-family: var(--font-mono, monospace);
    font-size: 0.68rem;
    color: var(--dv-umber);
  }

  .dv-portrait-result {
    border-top: 1px solid rgba(229, 169, 58, 0.12);
    padding-top: 12px;
  }

  .dv-portrait-result-label {
    font-family: var(--font-heading, "Cinzel", serif);
    font-size: 0.58rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--dv-gold-dim);
    display: block;
    margin-bottom: 6px;
  }

  .dv-portrait-result-text {
    font-size: 0.95rem;
    line-height: 1.6;
    color: var(--dv-sepia);
    white-space: pre-wrap;
    word-break: break-word;
  }

  /* ── The Scroll (Trace Timeline) ── */
  .dv-scroll {
    margin-top: 8px;
  }

  .dv-scroll-header {
    text-align: center;
    margin-bottom: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 16px;
  }

  .dv-scroll-ornament {
    width: 40px;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--dv-gold-dim), transparent);
  }

  .dv-scroll-title {
    font-family: var(--font-display, "Cinzel Decorative", serif);
    font-size: 0.78rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--dv-gold);
    filter: drop-shadow(0 0 8px rgba(229, 169, 58, 0.2));
  }

  /* Timeline structure */
  .dv-timeline {
    position: relative;
    padding-left: 36px;
  }

  .dv-timeline-line {
    position: absolute;
    left: 13px;
    top: 0;
    bottom: 0;
    width: 1px;
    background: linear-gradient(
      180deg,
      transparent 0%,
      rgba(229, 169, 58, 0.3) 5%,
      rgba(229, 169, 58, 0.15) 50%,
      rgba(229, 169, 58, 0.3) 95%,
      transparent 100%
    );
  }

  /* Phase dividers */
  .dv-phase-divider {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 20px 0 14px -36px;
    padding-left: 4px;
    animation: dv-fade-up 400ms ease-out both;
  }

  .dv-phase-gem {
    width: 20px;
    height: 20px;
    flex-shrink: 0;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .dv-phase-gem::before {
    content: "";
    position: absolute;
    width: 10px;
    height: 10px;
    background: var(--dv-gold);
    transform: rotate(45deg);
    box-shadow: 0 0 10px rgba(229, 169, 58, 0.5);
  }

  .dv-phase-label {
    font-family: var(--font-display, "Cinzel Decorative", serif);
    font-size: 0.68rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--dv-gold);
    filter: drop-shadow(0 0 6px rgba(229, 169, 58, 0.2));
  }

  /* Individual timeline events */
  .dv-timeline-event {
    display: flex;
    gap: 14px;
    margin-bottom: 12px;
    margin-left: -36px;
    animation: dv-event-appear 400ms ease-out both;
  }

  @keyframes dv-event-appear {
    from { opacity: 0; transform: translateX(-8px); }
    to { opacity: 1; transform: translateX(0); }
  }

  .dv-timeline-node {
    width: 28px;
    height: 28px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: var(--dv-obsidian);
    border: 1px solid rgba(229, 169, 58, 0.2);
    position: relative;
    z-index: 1;
  }

  .dv-severity-warm .dv-timeline-node {
    border-color: rgba(229, 169, 58, 0.4);
    box-shadow: 0 0 8px rgba(229, 169, 58, 0.15);
  }

  .dv-severity-success .dv-timeline-node {
    border-color: rgba(110, 169, 216, 0.5);
    box-shadow: 0 0 8px rgba(110, 169, 216, 0.2);
  }

  .dv-severity-error .dv-timeline-node {
    border-color: rgba(139, 41, 66, 0.5);
    box-shadow: 0 0 8px rgba(139, 41, 66, 0.2);
  }

  .dv-timeline-icon {
    font-size: 0.78rem;
    line-height: 1;
  }

  .dv-severity-neutral .dv-timeline-icon { color: var(--dv-sepia); }
  .dv-severity-warm .dv-timeline-icon { color: var(--dv-gold); }
  .dv-severity-success .dv-timeline-icon { color: #6ea9d8; }
  .dv-severity-error .dv-timeline-icon { color: var(--dv-burgundy-light); }

  .dv-timeline-content {
    flex: 1;
    min-width: 0;
    padding: 10px 14px 12px;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.04);
    background: linear-gradient(155deg, rgba(24, 26, 44, 0.7), rgba(14, 16, 28, 0.85));
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    transition: border-color 200ms;
  }

  .dv-severity-warm .dv-timeline-content {
    border-left: 2px solid rgba(229, 169, 58, 0.3);
    background: linear-gradient(155deg, rgba(30, 26, 20, 0.75), rgba(14, 12, 8, 0.88));
  }

  .dv-severity-success .dv-timeline-content {
    border-left: 2px solid rgba(110, 169, 216, 0.3);
    background: linear-gradient(155deg, rgba(20, 26, 36, 0.75), rgba(8, 12, 20, 0.88));
  }

  .dv-severity-error .dv-timeline-content {
    border-left: 2px solid rgba(139, 41, 66, 0.4);
    background: linear-gradient(155deg, rgba(30, 16, 20, 0.75), rgba(18, 8, 10, 0.88));
  }

  .dv-timeline-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
  }

  .dv-timeline-type {
    font-family: var(--font-mono, monospace);
    font-size: 0.6rem;
    color: var(--dv-umber);
    background: rgba(255, 255, 255, 0.04);
    padding: 1px 7px;
    border-radius: 4px;
  }

  .dv-timeline-time {
    font-family: var(--font-mono, monospace);
    font-size: 0.58rem;
    color: var(--dv-umber);
    flex-shrink: 0;
  }

  .dv-timeline-title {
    display: block;
    font-family: var(--font-body, "EB Garamond", Georgia, serif);
    font-size: 0.95rem;
    color: var(--dv-parchment);
    margin-bottom: 4px;
  }

  .dv-timeline-detail {
    font-family: var(--font-mono, monospace);
    font-size: 0.72rem;
    color: var(--dv-sepia);
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.5;
  }

  .dv-clamped {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .dv-timeline-expand {
    font-family: var(--font-mono, monospace);
    font-size: 0.6rem;
    color: var(--dv-gold-dim);
    margin-top: 4px;
    padding: 0;
    opacity: 0.7;
    text-decoration: underline;
    display: block;
    text-decoration-style: dotted;
  }

  .dv-timeline-expand:hover { opacity: 1; }

  /* Terminal flourish */
  .dv-timeline-end {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 24px 0 8px -36px;
    padding-left: 4px;
  }

  .dv-timeline-end-gem {
    width: 28px;
    height: 28px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 35%, var(--dv-gold), var(--dv-gold-dim));
    box-shadow: 0 0 14px rgba(229, 169, 58, 0.4), 0 0 40px rgba(229, 169, 58, 0.1);
  }

  .dv-timeline-end-text {
    font-family: var(--font-display, "Cinzel Decorative", serif);
    font-size: 0.72rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--dv-gold);
    font-style: italic;
    filter: drop-shadow(0 0 6px rgba(229, 169, 58, 0.2));
  }

  /* ── Empty State (No Task Selected) ── */
  .dv-empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 64px 24px;
  }

  .dv-empty-state-artwork {
    position: relative;
    width: 120px;
    height: 120px;
    margin-bottom: 24px;
  }

  .dv-empty-ring {
    position: absolute;
    border-radius: 50%;
    border: 1px solid transparent;
  }

  .dv-ring-1 {
    inset: 0;
    border-color: rgba(229, 169, 58, 0.12);
    animation: dv-ring-spin 20s linear infinite;
  }

  .dv-ring-2 {
    inset: 15px;
    border-color: rgba(110, 169, 216, 0.1);
    animation: dv-ring-spin 15s linear infinite reverse;
  }

  .dv-ring-3 {
    inset: 30px;
    border-color: rgba(154, 127, 208, 0.1);
    animation: dv-ring-spin 10s linear infinite;
  }

  @keyframes dv-ring-spin {
    0% { transform: rotate(0deg); border-top-color: rgba(229, 169, 58, 0.3); }
    100% { transform: rotate(360deg); border-top-color: rgba(229, 169, 58, 0.3); }
  }

  .dv-empty-core {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.8rem;
    color: var(--dv-gold-dim);
    opacity: 0.5;
    animation: dv-text-pulse 3s ease-in-out infinite;
  }

  .dv-empty-state-text {
    font-size: 1rem;
    color: var(--dv-sepia);
    font-style: italic;
  }

  /* ── Responsive ── */
  @media (max-width: 700px) {
    .dv-gallery-grid {
      grid-template-columns: 1fr;
    }

    .dv-portrait {
      flex-direction: column;
      align-items: center;
      text-align: center;
    }

    .dv-portrait-meta {
      justify-content: center;
    }

    .dv-timeline {
      padding-left: 30px;
    }

    .dv-timeline-event {
      margin-left: -30px;
    }

    .dv-phase-divider {
      margin-left: -30px;
    }

    .dv-timeline-end {
      margin-left: -30px;
    }
  }
</style>
