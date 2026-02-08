import { Node, Edge } from 'reactflow';
import { ExecutionStatus } from './execution';

export type NodeType = 'start' | 'action' | 'end';

export interface WorkflowNode extends Node {
  type: NodeType;
  data: {
    label: string;
    description?: string;
    service?: string;
    executionState?: ExecutionStatus;
  };
}

export interface WorkflowGraph {
  nodes: WorkflowNode[];
  edges: Edge[];
}

export interface WorkflowMetadata {
  path?: string;
  stepCount: number;
}
