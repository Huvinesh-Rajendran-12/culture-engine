import type { Mind, MindCharter, Task, TaskTrace, MemoryEntry } from "./types";

export const api = {
  async listMinds(): Promise<Mind[]> {
    const res = await fetch("/api/minds");
    if (!res.ok) throw new Error("Failed to list minds");
    return res.json();
  },

  async createMind(payload: {
    name: string;
    personality: string;
    system_prompt: string;
    preferences: Record<string, unknown>;
  }): Promise<Mind> {
    const res = await fetch("/api/minds", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to create mind");
    return res.json();
  },

  async updateMind(
    mindId: string,
    payload: {
      name?: string;
      personality?: string;
      system_prompt?: string;
      preferences?: Record<string, unknown>;
      charter?: Partial<MindCharter>;
    },
  ): Promise<Mind> {
    const res = await fetch(`/api/minds/${mindId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to update mind");
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

  async listMemory(mindId: string): Promise<MemoryEntry[]> {
    const res = await fetch(`/api/minds/${mindId}/memory`);
    if (!res.ok) throw new Error("Failed to list memory");
    return res.json();
  },
};
