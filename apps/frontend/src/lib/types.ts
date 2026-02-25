// ── Types aligned with the simplified agent runner backend ──────────────────

/** Request body for POST /run */
export type RunRequest = {
  prompt: string;
  system_prompt?: string;
  team?: string;
  workspace_dir?: string | null;
  allowed_tools?: string[] | null;
  max_turns?: number;
};

/** A single SSE event from the /run stream */
export type StreamEvent = {
  type: string;
  content: unknown;
  timestamp?: string;
};

/** Processed view of a StreamEvent for display */
export type EventView = {
  id: string;
  type: string;
  title: string;
  detail: string;
  fullDetail: string;
  severity: "info" | "success" | "warn" | "error";
  timestamp: string | null;
};

/** Aggregated stats from a run's event stream */
export type RunStats = {
  total: number;
  text: number;
  toolUse: number;
  toolResult: number;
  errors: number;
  status: string;
};

/** Items for the Output feed */
export type OutputItem =
  | { kind: "text"; content: string }
  | { kind: "tool"; name: string; status: "pending" | "ok" | "error" };
