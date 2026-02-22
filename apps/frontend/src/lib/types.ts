// ── Shared Types ────────────────────────────────────────────────────────────

export type MindCharter = {
  mission: string;
  reason_for_existence: string;
  operating_principles: string[];
  non_goals: string[];
  reflection_focus: string[];
};

export type Mind = {
  id: string;
  name: string;
  personality: string;
  preferences: Record<string, unknown>;
  system_prompt: string;
  charter: MindCharter;
  created_at: string;
};

export type Task = {
  id: string;
  mind_id?: string;
  description: string;
  status: string;
  result: string | null;
  created_at: string;
  completed_at?: string | null;
};

export type StreamEvent = {
  type: string;
  content: unknown;
  timestamp?: string;
};

export type TraceEvent = {
  type: string;
  content: unknown;
  timestamp: string;
};

export type TaskTrace = {
  task_id: string;
  mind_id: string;
  events: TraceEvent[];
};

export type MemoryEntry = {
  id: string;
  mind_id: string;
  content: string;
  category: string | null;
  relevance_keywords: string[];
  created_at: string;
};

export type EventView = {
  id: string;
  type: string;
  title: string;
  detail: string;
  fullDetail: string;
  severity: "info" | "success" | "warn" | "error";
  timestamp: string | null;
};

export type SpawnRun = {
  callId: string;
  objective: string;
  maxTurns: number;
  result: string;
  isError: boolean;
};

export type RunStats = {
  total: number;
  text: number;
  toolUse: number;
  toolResult: number;
  errors: number;
  status: string;
  taskId: string;
};

export type OutputItem =
  | { kind: "text"; content: string }
  | { kind: "tool"; name: string; status: "pending" | "ok" | "error" }
  | { kind: "spawn"; objective: string; result: string; isError: boolean };

export type Overlay = "none" | "task-detail" | "mind-profile" | "memory-vault" | "mind-create";

// ── Drone types (from DroneViewer) ────────────────────────────────────────

export type Drone = {
  id: string;
  mind_id: string;
  task_id: string;
  objective: string;
  status: "pending" | "running" | "completed" | "failed";
  result: string | null;
  created_at: string;
  completed_at: string | null;
};

export type DroneTraceEvent = {
  id?: string;
  type: string;
  seq?: number;
  ts?: string;
  trace_id?: string;
  content: unknown;
  timestamp?: string;
};

export type DroneTrace = {
  drone_id: string;
  mind_id: string;
  events: DroneTraceEvent[];
};
