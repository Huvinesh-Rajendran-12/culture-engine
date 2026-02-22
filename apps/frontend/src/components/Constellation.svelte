<script lang="ts">
  import { compact, prettyDate } from "../lib/helpers";
  import type { Task } from "../lib/types";

  type OrbitalNode = {
    task: Task;
    x: number;
    y: number;
    ring: number;
  };

  let {
    tasks = [] as Task[],
    selectedTaskId = "",
    busy = false,
    onSelectTask,
  }: {
    tasks: Task[];
    selectedTaskId?: string;
    busy?: boolean;
    onSelectTask?: (taskId: string) => void;
  } = $props();

  const MAX_NODES = 15;
  const CENTER = 500;
  const ORBIT_RADII = [218, 300, 380];

  let orderedTasks = $derived(
    [...tasks]
      .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
      .slice(0, MAX_NODES)
  );

  let orbitalNodes = $derived.by(() => {
    const nodes: OrbitalNode[] = [];
    const count = orderedTasks.length;
    if (!count) return nodes;

    for (let i = 0; i < count; i += 1) {
      const task = orderedTasks[i];
      const ring = i % ORBIT_RADII.length;
      const entriesInRing = Math.ceil((count - ring) / ORBIT_RADII.length);
      const positionInRing = Math.floor(i / ORBIT_RADII.length);
      const angleOffset = ring * 0.28;
      const angle =
        ((Math.PI * 2) / Math.max(entriesInRing, 1)) * positionInRing -
        Math.PI / 2 +
        angleOffset;

      const radius = ORBIT_RADII[ring];
      nodes.push({
        task,
        ring,
        x: CENTER + Math.cos(angle) * radius,
        y: CENTER + Math.sin(angle) * radius,
      });
    }

    return nodes;
  });

  function statusClass(status: string): string {
    if (status === "completed") return "completed";
    if (status === "failed" || status === "error") return "failed";
    if (status === "running" || status === "in_progress") return "running";
    return "pending";
  }

  function onSelect(taskId: string): void {
    onSelectTask?.(taskId);
  }
</script>

<section class="constellation" data-busy={busy} aria-label="Task constellation">
  <div class="constellation-orbits">
    <svg viewBox="0 0 1000 1000" class="constellation-svg" aria-hidden="true">
      <circle cx="500" cy="500" r="218" class="orbit orbit-1"></circle>
      <circle cx="500" cy="500" r="300" class="orbit orbit-2"></circle>
      <circle cx="500" cy="500" r="380" class="orbit orbit-3"></circle>

      {#each orbitalNodes as node (node.task.id)}
        <line
          x1="500"
          y1="500"
          x2={node.x}
          y2={node.y}
          class="orbit-line"
        ></line>
      {/each}
    </svg>

    {#if orbitalNodes.length === 0}
      <div class="constellation-empty">No tasks in orbit yet. Delegate a task to begin.</div>
    {:else}
      {#each orbitalNodes as node (node.task.id)}
        <button
          type="button"
          class="task-node {statusClass(node.task.status)}"
          class:selected={node.task.id === selectedTaskId}
          style={`left: ${(node.x / 1000) * 100}%; top: ${(node.y / 1000) * 100}%`}
          onclick={() => onSelect(node.task.id)}
        >
          <span class="task-node-dot" aria-hidden="true"></span>
          <span class="task-node-title">{compact(node.task.description, 58)}</span>
          <span class="task-node-meta">{node.task.status}</span>
        </button>
      {/each}
    {/if}
  </div>

  <div class="constellation-strip" role="list">
    {#if orderedTasks.length === 0}
      <div class="constellation-empty">No tasks in orbit yet. Delegate a task to begin.</div>
    {:else}
      {#each orderedTasks as task (task.id)}
        <button
          type="button"
          class="strip-card {statusClass(task.status)}"
          class:selected={task.id === selectedTaskId}
          onclick={() => onSelect(task.id)}
        >
          <span class="strip-title">{compact(task.description, 72)}</span>
          <span class="strip-meta">{task.status} - {prettyDate(task.created_at)}</span>
        </button>
      {/each}
    {/if}
  </div>
</section>

<style>
  .constellation {
    position: relative;
    width: 100%;
    height: 100%;
    min-height: 520px;
    border-radius: 18px;
    border: 1px solid rgba(232, 175, 71, 0.17);
    background:
      radial-gradient(ellipse at 50% 50%, rgba(232, 175, 71, 0.06) 0%, transparent 50%),
      radial-gradient(ellipse at 18% 20%, rgba(123, 176, 224, 0.08) 0%, transparent 48%),
      linear-gradient(165deg, rgba(10, 14, 26, 0.9), rgba(6, 8, 15, 0.94));
    overflow: hidden;
  }

  .constellation-orbits {
    position: relative;
    width: 100%;
    height: 100%;
    min-height: 520px;
  }

  .constellation-svg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }

  .orbit {
    fill: none;
    stroke-width: 1;
    stroke-dasharray: 4 10;
    transform-origin: center;
  }

  .orbit-1 {
    stroke: rgba(232, 175, 71, 0.26);
    animation: orbit-spin 34s linear infinite;
  }

  .orbit-2 {
    stroke: rgba(123, 176, 224, 0.2);
    animation: orbit-spin 28s linear infinite reverse;
  }

  .orbit-3 {
    stroke: rgba(232, 175, 71, 0.17);
    animation: orbit-spin 42s linear infinite;
  }

  .orbit-line {
    stroke: rgba(232, 175, 71, 0.11);
    stroke-width: 1;
  }

  .task-node {
    position: absolute;
    transform: translate(-50%, -50%);
    max-width: 180px;
    padding: 7px 9px;
    border-radius: 10px;
    border: 1px solid rgba(232, 175, 71, 0.23);
    background: rgba(8, 10, 18, 0.88);
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
    text-align: left;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.38);
    transition: transform 180ms ease, border-color 180ms ease;
  }

  .task-node:hover {
    transform: translate(-50%, -50%) scale(1.03);
    border-color: rgba(232, 175, 71, 0.5);
  }

  .task-node.selected {
    border-color: rgba(123, 176, 224, 0.75);
    box-shadow:
      0 12px 24px rgba(0, 0, 0, 0.45),
      0 0 22px rgba(123, 176, 224, 0.2);
  }

  .task-node-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #a39ab2;
    box-shadow: 0 0 10px rgba(163, 154, 178, 0.35);
  }

  .task-node.running .task-node-dot {
    background: #f1be5c;
    box-shadow: 0 0 10px rgba(241, 190, 92, 0.65);
    animation: node-pulse 1.2s ease-in-out infinite;
  }

  .task-node.completed .task-node-dot {
    background: #76c29e;
    box-shadow: 0 0 10px rgba(118, 194, 158, 0.62);
  }

  .task-node.failed .task-node-dot {
    background: #d17373;
    box-shadow: 0 0 10px rgba(209, 115, 115, 0.55);
  }

  .task-node-title {
    color: var(--ink-1);
    font-size: 0.8rem;
    line-height: 1.2;
  }

  .task-node-meta {
    color: var(--ink-3);
    font-size: 0.64rem;
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  .constellation-empty {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    color: var(--ink-3);
    font-style: italic;
    font-size: 0.96rem;
  }

  .constellation-strip {
    display: none;
  }

  .strip-card {
    min-width: 260px;
    border-radius: 10px;
    border: 1px solid rgba(232, 175, 71, 0.22);
    background: rgba(8, 10, 18, 0.9);
    padding: 10px;
    text-align: left;
    display: flex;
    flex-direction: column;
    gap: 6px;
    color: var(--ink-2);
  }

  .strip-card.selected {
    border-color: rgba(123, 176, 224, 0.75);
  }

  .strip-card.running {
    border-color: rgba(232, 175, 71, 0.55);
  }

  .strip-card.completed {
    border-color: rgba(118, 194, 158, 0.55);
  }

  .strip-card.failed {
    border-color: rgba(209, 115, 115, 0.55);
  }

  .strip-title {
    color: var(--ink-1);
    font-size: 0.88rem;
    line-height: 1.25;
  }

  .strip-meta {
    color: var(--ink-3);
    font-size: 0.62rem;
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  @keyframes node-pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.35); }
  }

  @keyframes orbit-spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  .constellation[data-busy="true"] .task-node {
    opacity: 0.42;
  }

  .constellation[data-busy="true"] .task-node.selected,
  .constellation[data-busy="true"] .task-node:hover {
    opacity: 1;
  }

  @media (max-width: 960px) {
    .constellation {
      min-height: 190px;
      padding: 10px;
    }

    .constellation-orbits {
      display: none;
    }

    .constellation-strip {
      display: flex;
      gap: 10px;
      overflow-x: auto;
      padding-bottom: 6px;
      scrollbar-width: thin;
      scrollbar-color: rgba(191, 143, 59, 0.28) transparent;
    }
  }

  @media (max-width: 700px) {
    .constellation {
      min-height: 0;
      border-radius: 12px;
      padding: 8px;
    }

    .constellation-strip {
      flex-direction: column;
      overflow-x: hidden;
      overflow-y: auto;
      max-height: 42vh;
    }

    .strip-card {
      min-width: 0;
      width: 100%;
    }
  }
</style>
