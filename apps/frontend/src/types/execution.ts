export type ExecutionStatus = 'pending' | 'running' | 'success' | 'failed' | 'skipped';

export interface ExecutionStepResult {
  [key: string]: unknown;
}

export interface TraceStep {
  node_id: string;
  service: string;
  action: string;
  parameters: Record<string, unknown>;
  status: ExecutionStatus;
  result?: ExecutionStepResult;
  error?: string;
  timestamp: string;
  duration_ms?: number;
}

export interface ExecutionTrace {
  steps: TraceStep[];
  dependency_violations: string[];
}

export interface ExecutionReport {
  workflow_name: string;
  trace: ExecutionTrace;
  summary: {
    total_steps: number;
    successful: number;
    failed: number;
    skipped: number;
  };
  start_time: string;
  end_time: string;
  total_duration_ms: number;
}

export interface NodeExecutionState {
  status: ExecutionStatus;
  error?: string;
  result?: ExecutionStepResult;
  timestamp?: string;
  duration_ms?: number;
}
