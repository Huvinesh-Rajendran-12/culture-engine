import { create } from 'zustand';
import { Message } from '../types/api';
import { WorkflowGraph, WorkflowMetadata } from '../types/workflow';
import { ExecutionReport, NodeExecutionState } from '../types/execution';

interface WorkflowState {
  messages: Message[];
  isStreaming: boolean;
  workflowGraph: WorkflowGraph | null;
  workflowMetadata: WorkflowMetadata;
  costUsd: number;
  totalTokens: number;
  executionReport: ExecutionReport | null;
  nodeExecutionState: Map<string, NodeExecutionState>;
  selectedNodeId: string | null;

  // Actions
  addMessage: (message: Message) => void;
  setStreaming: (isStreaming: boolean) => void;
  setWorkflowGraph: (graph: WorkflowGraph, metadata?: Partial<WorkflowMetadata>) => void;
  setExecutionReport: (report: ExecutionReport) => void;
  updateNodeState: (nodeId: string, state: NodeExecutionState) => void;
  selectNode: (nodeId: string | null) => void;
  reset: () => void;
}

const initialState = {
  messages: [],
  isStreaming: false,
  workflowGraph: null,
  workflowMetadata: { stepCount: 0 },
  costUsd: 0,
  totalTokens: 0,
  executionReport: null,
  nodeExecutionState: new Map<string, NodeExecutionState>(),
  selectedNodeId: null,
};

export const useWorkflowStore = create<WorkflowState>((set) => ({
  ...initialState,

  addMessage: (message) =>
    set((state) => {
      console.log('[workflowStore] addMessage called:', message.type, message);
      const newMessages = [...state.messages, message];
      console.log('[workflowStore] New message count:', newMessages.length);

      // Update metrics if this is a result message
      if (message.type === 'result') {
        console.log('[workflowStore] Result message - updating metrics');
        return {
          messages: newMessages,
          costUsd: message.content.cost_usd,
          totalTokens: message.content.usage.total_tokens,
        };
      }

      // Update workspace path if this is a workspace message
      if (message.type === 'workspace') {
        console.log('[workflowStore] Workspace message - updating path');
        return {
          messages: newMessages,
          workflowMetadata: {
            ...state.workflowMetadata,
            path: message.content.path,
          },
        };
      }

      return { messages: newMessages };
    }),

  setStreaming: (isStreaming) => set({ isStreaming }),

  setWorkflowGraph: (graph, metadata = {}) =>
    set((state) => {
      console.log('[workflowStore] setWorkflowGraph called with', graph.nodes.length, 'nodes');
      return {
        workflowGraph: graph,
        workflowMetadata: {
          ...state.workflowMetadata,
          ...metadata,
          stepCount: graph.nodes.filter((n) => n.type === 'action').length,
        },
      };
    }),

  setExecutionReport: (report) =>
    set((state) => {
      console.log('[workflowStore] setExecutionReport called with', report.trace.steps.length, 'steps');
      const newNodeState = new Map(state.nodeExecutionState);

      // Update each node's execution state from the report
      report.trace.steps.forEach((step) => {
        newNodeState.set(step.node_id, {
          status: step.status,
          error: step.error,
          result: step.result,
          timestamp: step.timestamp,
          duration_ms: step.duration_ms,
        });
      });

      console.log('[workflowStore] Updated node execution state for', newNodeState.size, 'nodes');
      return {
        executionReport: report,
        nodeExecutionState: newNodeState,
      };
    }),

  updateNodeState: (nodeId, state) =>
    set((prevState) => {
      const newNodeState = new Map(prevState.nodeExecutionState);
      newNodeState.set(nodeId, state);
      return { nodeExecutionState: newNodeState };
    }),

  selectNode: (nodeId) => set({ selectedNodeId: nodeId }),

  reset: () => set(initialState),
}));
