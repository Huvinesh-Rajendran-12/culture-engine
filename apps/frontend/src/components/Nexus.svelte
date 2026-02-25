<script lang="ts">
  let {
    busy = false,
    status = "idle",
  }: {
    busy?: boolean;
    status?: string;
  } = $props();

  let statusLabel = $derived.by(() => {
    if (busy) return "processing";
    if (status === "completed") return "ready";
    if (status === "error") return "error";
    return "standing by";
  });
</script>

<section class="nexus" data-busy={busy} aria-live="polite">
  <div class="nexus-rings" aria-hidden="true">
    <span class="ring ring-a"></span>
    <span class="ring ring-b"></span>
    <span class="ring ring-c"></span>
  </div>

  <div class="nexus-core">
    <span class="nexus-core-glow" aria-hidden="true"></span>
    <span class="nexus-title">Nexus</span>
    <span class="nexus-name">Agent Runner</span>
    <span class="nexus-status">{statusLabel}</span>
  </div>
</section>

<style>
  .nexus {
    position: relative;
    width: min(260px, 48vw);
    aspect-ratio: 1;
    display: grid;
    place-items: center;
    pointer-events: none;
  }

  .nexus-rings {
    position: absolute;
    inset: -32%;
    display: grid;
    place-items: center;
  }

  .ring {
    position: absolute;
    border-radius: 50%;
    border: 1px solid rgba(232, 175, 71, 0.26);
    box-shadow: 0 0 30px rgba(232, 175, 71, 0.14);
  }

  .ring-a {
    width: 100%;
    height: 100%;
    animation: ring-spin 36s linear infinite;
  }

  .ring-b {
    width: 82%;
    height: 82%;
    border-color: rgba(123, 176, 224, 0.22);
    animation: ring-spin 24s linear infinite reverse;
  }

  .ring-c {
    width: 64%;
    height: 64%;
    border-color: rgba(232, 175, 71, 0.34);
    animation: ring-pulse 4.6s ease-in-out infinite;
  }

  .nexus-core {
    position: relative;
    width: 68%;
    height: 68%;
    border-radius: 50%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    background:
      radial-gradient(circle at 32% 28%, rgba(244, 206, 126, 0.36), transparent 45%),
      radial-gradient(circle at 68% 72%, rgba(111, 162, 205, 0.2), transparent 46%),
      linear-gradient(165deg, rgba(16, 21, 38, 0.96), rgba(8, 11, 20, 0.98));
    border: 1px solid rgba(232, 175, 71, 0.36);
    box-shadow:
      0 0 28px rgba(232, 175, 71, 0.2),
      0 0 80px rgba(232, 175, 71, 0.08),
      inset 0 1px 0 rgba(255, 255, 255, 0.08);
    animation: core-breathe 4.8s ease-in-out infinite;
  }

  .nexus[data-busy="true"] .nexus-core {
    animation: core-busy 1.9s ease-in-out infinite;
    box-shadow:
      0 0 48px rgba(232, 175, 71, 0.35),
      0 0 120px rgba(232, 175, 71, 0.12),
      inset 0 1px 0 rgba(255, 255, 255, 0.12);
  }

  .nexus-core-glow {
    position: absolute;
    inset: -12%;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(232, 175, 71, 0.3) 0%, transparent 65%);
    filter: blur(12px);
    z-index: -1;
  }

  .nexus-title {
    font-family: var(--font-heading);
    text-transform: uppercase;
    letter-spacing: 0.24em;
    font-size: 0.58rem;
    color: rgba(238, 194, 114, 0.78);
  }

  .nexus-name {
    font-family: var(--font-display);
    font-size: clamp(0.92rem, 1.6vw, 1.15rem);
    color: var(--ink-1);
    text-align: center;
    padding: 0 10px;
    line-height: 1.2;
    max-width: 92%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .nexus-status {
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-size: 0.62rem;
    color: var(--ink-3);
  }

  @keyframes core-breathe {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.04); }
  }

  @keyframes core-busy {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.08); }
  }

  @keyframes ring-spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  @keyframes ring-pulse {
    0%, 100% { opacity: 0.55; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.04); }
  }

  @media (max-width: 700px) {
    .nexus {
      width: min(170px, 46vw);
    }

    .nexus-title {
      font-size: 0.5rem;
    }
  }
</style>
