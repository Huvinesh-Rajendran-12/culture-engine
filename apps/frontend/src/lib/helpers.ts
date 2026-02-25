import type {
  StreamEvent,
  EventView,
  RunStats,
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

// ── Event processing ──────────────────────────────────────────────────────

function getTimestamp(event: StreamEvent): string | null {
  return typeof event.timestamp === "string" ? event.timestamp : null;
}

export function toEventView(event: StreamEvent, index: number): EventView {
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
      view.title = "Agent output";
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
      view.fullDetail = fullString(event.content);
      view.severity = "success";
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

  for (const event of events) {
    if (event.type === "text") text += 1;
    if (event.type === "tool_use") toolUse += 1;
    if (event.type === "tool_result") toolResult += 1;
    if (event.type === "error") errors += 1;
    if (event.type === "result") status = "completed";
    if (event.type === "error") status = "error";
  }

  return { total: events.length, text, toolUse, toolResult, errors, status };
}

export function toolLabel(name: string): { glyph: string; label: string } {
  const map: Record<string, { glyph: string; label: string }> = {
    read_file: { glyph: "\u25C9", label: "read file" },
    write_file: { glyph: "\u25C9", label: "wrote file" },
    edit_file: { glyph: "\u25C9", label: "edited file" },
    run_command: { glyph: "\u27E9", label: "ran command" },
  };
  return map[name] ?? { glyph: "\u25EC", label: name };
}

export function buildOutputItems(events: StreamEvent[]): OutputItem[] {
  const items: OutputItem[] = [];
  const toolCallMap = new Map<string, number>();

  for (const event of events) {
    if (event.type === "text") {
      const text = typeof event.content === "string" ? event.content : "";
      if (text.trim()) items.push({ kind: "text", content: text });
    }

    if (event.type === "tool_use") {
      const payload = asObject(event.content);
      const toolName = typeof payload.tool === "string" ? payload.tool : "unknown";
      const callId = typeof payload.id === "string" ? payload.id : "";
      const idx = items.length;
      items.push({ kind: "tool", name: toolName, status: "pending" });
      if (callId) toolCallMap.set(callId, idx);
    }

    if (event.type === "tool_result") {
      const payload = asObject(event.content);
      const callId = typeof payload.tool_use_id === "string" ? payload.tool_use_id : "";
      const isError = Boolean(payload.is_error);

      if (callId && toolCallMap.has(callId)) {
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
    if (event.type === "text") {
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
