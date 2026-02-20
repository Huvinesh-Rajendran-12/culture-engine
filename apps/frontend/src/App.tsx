import { FormEvent, useEffect, useMemo, useState } from "react";
import "./App.css";

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
    <div className="app">
      <header className="hero">
        <h1>Culture Engine</h1>
        <p className="subtitle">A renaissance-inspired atelier for your autonomous Mind and delegated craftwork.</p>
      </header>

      <div className="controls">
        <section className="card">
          <h3>Create Mind</h3>
          <form onSubmit={onCreateMind} className="row">
            <input value={newMindName} onChange={(e) => setNewMindName(e.target.value)} placeholder="Mind name" />
            <button type="submit">Create</button>
          </form>
        </section>

        <section className="card">
          <h3>Current Mind</h3>
          <div className="row">
            <select value={selectedMindId} onChange={(e) => setSelectedMindId(e.target.value)}>
              <option value="">-- choose --</option>
              {minds.map((mind) => (
                <option key={mind.id} value={mind.id}>
                  {mind.name} ({mind.id})
                </option>
              ))}
            </select>
            {selectedMind ? <span className="muted">personality: {selectedMind.personality || "n/a"}</span> : null}
          </div>
        </section>
      </div>

      <section className="card" style={{ marginBottom: 14 }}>
        <h3>Delegate a Task</h3>
        <form onSubmit={onDelegate} className="row">
          <input
            className="wide"
            value={taskText}
            onChange={(e) => setTaskText(e.target.value)}
            placeholder="Delegate a task"
          />
          <button type="submit" disabled={!selectedMindId || busy}>
            {busy ? "In Progress..." : "Delegate"}
          </button>
        </form>
      </section>

      {error ? <div className="error">{error}</div> : null}

      <div className="grid">
        <section className="card">
          <h3>Live Event Chronicle</h3>
          <div className="panel">
            {events.length === 0 ? (
              <div className="muted">No events yet.</div>
            ) : (
              events.map((evt, idx) => (
                <pre key={`${evt.type}-${idx}`}>
                  [{evt.type}] {JSON.stringify(evt.content)}
                </pre>
              ))
            )}
          </div>
        </section>

        <section className="card">
          <h3>Task Ledger</h3>
          <div className="panel">
            {tasks.length === 0 ? (
              <div className="muted">No tasks yet.</div>
            ) : (
              tasks.map((task) => (
                <div key={task.id} className="task-row">
                  <div>
                    <span className="badge">{task.status}</span>
                    {task.description}
                  </div>
                  <button onClick={() => void loadTrace(task.id)} style={{ marginTop: 6 }}>
                    View trace
                  </button>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      <section className="card" style={{ marginTop: 14 }}>
        <h3>Selected Trace {selectedTaskId ? `(${selectedTaskId})` : ""}</h3>
        <div className="panel trace-panel">
          {!trace ? (
            <div className="muted">Pick a task to inspect full trace.</div>
          ) : (
            trace.events.map((evt, idx) => (
              <pre key={`${evt.type}-${idx}`}>
                {evt.timestamp} [{evt.type}] {JSON.stringify(evt.content)}
              </pre>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
