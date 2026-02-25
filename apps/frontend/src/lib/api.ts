import type { RunRequest, StreamEvent } from "./types";

export const api = {
  async health(): Promise<{ status: string }> {
    const res = await fetch("/health");
    if (!res.ok) throw new Error("Backend unreachable");
    return res.json();
  },

  /**
   * POST /run — returns a ReadableStream of SSE events.
   * The caller is responsible for reading and parsing the stream.
   */
  async run(request: RunRequest): Promise<ReadableStream<Uint8Array>> {
    const res = await fetch("/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });

    if (!res.ok || !res.body) {
      throw new Error("Failed to start agent run");
    }

    return res.body;
  },
};

/**
 * Helper: read an SSE body stream and invoke `onEvent` for each parsed event.
 */
export async function consumeSSEStream(
  body: ReadableStream<Uint8Array>,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const reader = body.getReader();
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
        try {
          const event = JSON.parse(line.slice(6)) as StreamEvent;
          onEvent(event);
        } catch {
          // skip malformed events
        }
      }

      split = buffer.indexOf("\n\n");
    }
  }
}
