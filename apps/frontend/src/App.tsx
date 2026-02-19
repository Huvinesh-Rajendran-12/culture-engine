import { FormEvent, useEffect, useMemo, useState } from "react";

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

export function App() {
  const [minds, setMinds] = useState<Mind[]>([]);
  const [selectedMindId, setSelectedMindId] = useState<string>("");
  const [newMindName, setNewMindName] = useState("Orbit");
  const [taskText, setTaskText] = useState("Summarize this week's project updates");
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string>("");
  const [trace, setTrace] = useState<TaskTrace | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>("");

  const selectedMind = useMemo(() => minds.find((m) => m.id === selectedMindId), [minds, selectedMindId]);

  useEffect(() => {
    void refreshMinds();
  }, []);

  useEffect(() => {
    if (!selectedMindId) {
      setTasks([]);
      return;
    }
    void refreshTasks(selectedMindId);
  }, [selectedMindId]);

  async function refreshMinds() {
    try {
      const data = await api.listMinds();
      setMinds(data);
      if (!selectedMindId && data.length > 0) {
        setSelectedMindId(data[0].id);
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function refreshTasks(mindId: string) {
    try {
      const data = await api.listTasks(mindId);
      setTasks(data);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function onCreateMind(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!newMindName.trim()) return;

    try {
      const mind = await api.createMind(newMindName.trim());
      const next = [mind, ...minds];
      setMinds(next);
      setSelectedMindId(mind.id);
      setNewMindName("");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onDelegate(e: FormEvent) {
    e.preventDefault();
    if (!selectedMindId || !taskText.trim()) return;

    setBusy(true);
    setError("");
    setEvents([]);
    setTrace(null);

    try {
      const res = await fetch(`/api/minds/${selectedMindId}/delegate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: taskText, team: "default" }),
      });

      if (!res.ok || !res.body) {
        throw new Error("Failed to start delegation stream");
      }

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
            const payload = line.slice(6);
            const event = JSON.parse(payload) as StreamEvent;
            setEvents((prev) => [...prev, event]);
          }

          split = buffer.indexOf("\n\n");
        }
      }

      await refreshTasks(selectedMindId);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function loadTrace(taskId: string) {
    if (!selectedMindId) return;
    try {
      setSelectedTaskId(taskId);
      const data = await api.getTrace(selectedMindId, taskId);
      setTrace(data);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div style={{ fontFamily: "sans-serif", padding: 16 }}>
      <h1>Culture Engine</h1>
      <p style={{ color: "#666" }}>Create/select a Mind, delegate work, inspect live events and traces.</p>

      <form onSubmit={onCreateMind} style={{ marginBottom: 12 }}>
        <input value={newMindName} onChange={(e) => setNewMindName(e.target.value)} placeholder="Mind name" />
        <button type="submit" style={{ marginLeft: 8 }}>
          Create Mind
        </button>
      </form>

      <div style={{ marginBottom: 12 }}>
        <label>Selected Mind: </label>
        <select value={selectedMindId} onChange={(e) => setSelectedMindId(e.target.value)}>
          <option value="">-- choose --</option>
          {minds.map((mind) => (
            <option key={mind.id} value={mind.id}>
              {mind.name} ({mind.id})
            </option>
          ))}
        </select>
        {selectedMind ? <span style={{ marginLeft: 8, color: "#666" }}>personality: {selectedMind.personality || "n/a"}</span> : null}
      </div>

      <form onSubmit={onDelegate} style={{ marginBottom: 16 }}>
        <input
          value={taskText}
          onChange={(e) => setTaskText(e.target.value)}
          placeholder="Delegate a task"
          style={{ width: 520 }}
        />
        <button type="submit" disabled={!selectedMindId || busy} style={{ marginLeft: 8 }}>
          {busy ? "Running..." : "Delegate"}
        </button>
      </form>

      {error ? <div style={{ color: "crimson", marginBottom: 12 }}>{error}</div> : null}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <section>
          <h3>Live Stream Events</h3>
          <div style={{ border: "1px solid #ddd", padding: 8, maxHeight: 320, overflow: "auto", fontSize: 12 }}>
            {events.length === 0 ? (
              <div style={{ color: "#777" }}>No events yet.</div>
            ) : (
              events.map((evt, idx) => (
                <pre key={`${evt.type}-${idx}`} style={{ margin: 0, marginBottom: 8, whiteSpace: "pre-wrap" }}>
                  [{evt.type}] {JSON.stringify(evt.content)}
                </pre>
              ))
            )}
          </div>
        </section>

        <section>
          <h3>Task History</h3>
          <div style={{ border: "1px solid #ddd", padding: 8, maxHeight: 320, overflow: "auto", fontSize: 12 }}>
            {tasks.length === 0 ? (
              <div style={{ color: "#777" }}>No tasks yet.</div>
            ) : (
              tasks.map((task) => (
                <div key={task.id} style={{ marginBottom: 8, paddingBottom: 8, borderBottom: "1px solid #eee" }}>
                  <div>
                    <strong>{task.status}</strong> · {task.description}
                  </div>
                  <button onClick={() => void loadTrace(task.id)} style={{ marginTop: 4 }}>
                    View trace
                  </button>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      <section style={{ marginTop: 16 }}>
        <h3>Selected Task Trace {selectedTaskId ? `(${selectedTaskId})` : ""}</h3>
        <div style={{ border: "1px solid #ddd", padding: 8, maxHeight: 280, overflow: "auto", fontSize: 12 }}>
          {!trace ? (
            <div style={{ color: "#777" }}>Pick a task to inspect full trace.</div>
          ) : (
            trace.events.map((evt, idx) => (
              <pre key={`${evt.type}-${idx}`} style={{ margin: 0, marginBottom: 8, whiteSpace: "pre-wrap" }}>
                {evt.timestamp} [{evt.type}] {JSON.stringify(evt.content)}
              </pre>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
