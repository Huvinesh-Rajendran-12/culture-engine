import type {
  StreamEvent,
  TraceEvent,
  EventView,
  RunStats,
  SpawnRun,
  MemoryEntry,
  Mind,
  OutputItem,
} from "./types";

// ── Generic utilities ─────────────────────────────────────────────────────

export function asObject(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

export function compact(value: unknown, max = 220): string {
  const raw = typeof value === "string" ? value : JSON.stringify(value, null, 0);
  if (!raw) return "";
  return raw.length > max ? `${raw.slice(0, max)}...` : raw;
}

export function fullString(value: unknown): string {
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

export function prettyDate(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function linesToList(raw: string): string[] {
  return raw
    .split("\n")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

export function listToLines(items: string[] | null | undefined): string {
  if (!items || items.length === 0) return "";
  return items.join("\n");
}

export function parsePreferencesInput(raw: string): Record<string, unknown> {
  const value = raw.trim();
  if (!value) return {};
  const parsed = JSON.parse(value);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Preferences must be a JSON object");
  }
  return parsed as Record<string, unknown>;
}

export function sortMinds(list: Mind[]): Mind[] {
  return [...list].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
}

// ── Event processing ──────────────────────────────────────────────────────

export function getTaskIdFromEvent(event: StreamEvent): string {
  if (event.type !== "task_started") return "";
  const payload = asObject(event.content);
  return typeof payload.task_id === "string" ? payload.task_id : "";
}

function getTimestamp(event: StreamEvent | TraceEvent): string | null {
  return typeof event.timestamp === "string" ? event.timestamp : null;
}

export function toEventView(event: StreamEvent | TraceEvent, index: number): EventView {
  const payload = asObject(event.content);
  const view: EventView = {
    id: `${index}-${event.type}`,
    type: event.type,
    title: event.type,
    detail: compact(event.content, 400),
    fullDetail: fullString(event.content),
    severity: "info",
    timestamp: getTimestamp(event),
  };

  switch (event.type) {
    case "task_started": {
      const taskId = typeof payload.task_id === "string" ? payload.task_id : "unknown";
      view.title = "Task started";
      view.detail = `Task ${taskId} started`;
      view.fullDetail = view.detail;
      break;
    }
    case "memory_context": {
      const count = typeof payload.count === "number" ? payload.count : 0;
      const ids = Array.isArray(payload.memory_ids)
        ? payload.memory_ids.filter((x): x is string => typeof x === "string")
        : [];
      view.title = "Memory loaded";
      view.detail = `${count} memories injected (${ids.join(", ") || "none"})`;
      view.fullDetail = view.detail;
      break;
    }
    case "tool_registry": {
      const tools = Array.isArray(payload.tools)
        ? payload.tools.filter((t): t is string => typeof t === "string")
        : [];
      view.title = "Tool registry";
      view.detail = tools.join(", ");
      view.fullDetail = view.detail;
      break;
    }
    case "tool_use": {
      const toolName = typeof payload.tool === "string" ? payload.tool : "unknown";
      view.title = `Tool call: ${toolName}`;
      view.detail = compact(payload.input, 320);
      view.fullDetail = fullString(payload.input);
      break;
    }
    case "tool_result": {
      const isError = Boolean(payload.is_error);
      view.title = `Tool result${isError ? " (error)" : ""}`;
      view.detail = compact(payload.result, 320);
      view.fullDetail = fullString(payload.result);
      view.severity = isError ? "warn" : "success";
      break;
    }
    case "text": {
      view.title = "Mind output";
      view.detail =
        typeof event.content === "string" ? event.content : compact(event.content, 400);
      view.fullDetail =
        typeof event.content === "string" ? event.content : fullString(event.content);
      break;
    }
    case "result": {
      const subtype = typeof payload.subtype === "string" ? payload.subtype : "completed";
      view.title = "Run result";
      view.detail = `Subtype: ${subtype}`;
      view.fullDetail = view.detail;
      view.severity = "success";
      break;
    }
    case "task_finished": {
      const status = typeof payload.status === "string" ? payload.status : "unknown";
      view.title = "Task finished";
      view.detail = `Status: ${status}`;
      view.fullDetail = view.detail;
      view.severity = status === "completed" ? "success" : "warn";
      break;
    }
    case "error": {
      view.title = "Error";
      view.detail =
        typeof event.content === "string" ? event.content : compact(event.content, 400);
      view.fullDetail =
        typeof event.content === "string" ? event.content : fullString(event.content);
      view.severity = "error";
      break;
    }
    default:
      break;
  }

  return view;
}

export function buildRunStats(events: StreamEvent[]): RunStats {
  let text = 0,
    toolUse = 0,
    toolResult = 0,
    errors = 0;
  let status = events.length > 0 ? "running" : "idle";
  let taskId = "";

  for (const event of events) {
    if (event.type === "text") text += 1;
    if (event.type === "tool_use") toolUse += 1;
    if (event.type === "tool_result") toolResult += 1;
    if (event.type === "error") errors += 1;
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

export function extractToolRegistry(events: StreamEvent[]): string[] {
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

export function extractMemoryContextIds(events: StreamEvent[]): string[] {
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

export function extractSpawnRuns(events: StreamEvent[]): SpawnRun[] {
  const runs = new Map<string, SpawnRun>();

  for (const event of events) {
    if (event.type === "tool_use") {
      const payload = asObject(event.content);
      if (payload.tool !== "spawn_agent") continue;
      const callId = typeof payload.id === "string" ? payload.id : `spawn-${runs.size + 1}`;
      const input = asObject(payload.input);
      const objective =
        typeof input.objective === "string" ? input.objective : "No objective provided";
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

export function buildMemoryCategories(items: MemoryEntry[]): string[] {
  const cats = new Set<string>();
  for (const item of items) cats.add(item.category || "uncategorized");
  return ["all", ...Array.from(cats).sort((a, b) => a.localeCompare(b))];
}

export function filterMemories(
  items: MemoryEntry[],
  query: string,
  category: string,
): MemoryEntry[] {
  const q = query.trim().toLowerCase();
  return items.filter((item) => {
    const cat = item.category || "uncategorized";
    if (category !== "all" && cat !== category) return false;
    if (!q) return true;
    const hay = [item.content, item.category || "", item.relevance_keywords.join(" ")]
      .join(" ")
      .toLowerCase();
    return hay.includes(q);
  });
}

export function toolLabel(name: string): { glyph: string; label: string } {
  const map: Record<string, { glyph: string; label: string }> = {
    memory_save: { glyph: "\u2B21", label: "saved to memory" },
    memory_search: { glyph: "\u2B21", label: "searched memory" },
    search_knowledge_base: { glyph: "\u25C8", label: "searched knowledge base" },
    search_apis: { glyph: "\u25C8", label: "searched API catalog" },
    read_file: { glyph: "\u25C9", label: "read file" },
    write_file: { glyph: "\u25C9", label: "wrote file" },
    edit_file: { glyph: "\u25C9", label: "edited file" },
    run_command: { glyph: "\u27E9", label: "ran command" },
    spawn_agent: { glyph: "\u2295", label: "delegated sub-task" },
  };
  return map[name] ?? { glyph: "\u25EC", label: name };
}

export function buildOutputItems(events: StreamEvent[]): OutputItem[] {
  const items: OutputItem[] = [];
  const toolCallMap = new Map<string, number>();
  const spawnMap = new Map<string, number>();

  for (const event of events) {
    if (event.type === "text") {
      const text = typeof event.content === "string" ? event.content : "";
      if (text.trim()) items.push({ kind: "text", content: text });
    }

    if (event.type === "tool_use") {
      const payload = asObject(event.content);
      const toolName = typeof payload.tool === "string" ? payload.tool : "unknown";
      const callId = typeof payload.id === "string" ? payload.id : "";

      if (toolName === "spawn_agent") {
        const input = asObject(payload.input);
        const objective =
          typeof input.objective === "string" ? input.objective : "Delegated sub-task";
        const idx = items.length;
        items.push({ kind: "spawn", objective, result: "", isError: false });
        if (callId) spawnMap.set(callId, idx);
      } else {
        const idx = items.length;
        items.push({ kind: "tool", name: toolName, status: "pending" });
        if (callId) toolCallMap.set(callId, idx);
      }
    }

    if (event.type === "tool_result") {
      const payload = asObject(event.content);
      const callId = typeof payload.tool_use_id === "string" ? payload.tool_use_id : "";
      const isError = Boolean(payload.is_error);

      if (callId && spawnMap.has(callId)) {
        const item = items[spawnMap.get(callId)!] as {
          kind: "spawn";
          result: string;
          isError: boolean;
        };
        item.result = compact(payload.result, 300) || "completed";
        item.isError = isError;
      } else if (callId && toolCallMap.has(callId)) {
        const item = items[toolCallMap.get(callId)!] as { kind: "tool"; status: string };
        item.status = isError ? "error" : "ok";
      }
    }
  }
  return items;
}

export function buildLiveTypingText(events: StreamEvent[]): string {
  let buffer = "";
  for (const event of events) {
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
}

export function formatPreferences(mind: Mind): string {
  return JSON.stringify(mind.preferences, null, 2);
}
