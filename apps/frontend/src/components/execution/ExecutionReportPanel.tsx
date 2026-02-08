import React from 'react';
import { useWorkflowStore } from '../../store/workflowStore';
import { ExecutionSummary } from './ExecutionSummary';
import { ExecutionStepList } from './ExecutionStepList';

export const ExecutionReportPanel: React.FC = () => {
  const { executionReport, selectedNodeId } = useWorkflowStore();

  if (!executionReport) {
    return (
      <div className="terminal-container h-full flex flex-col">
        <div className="terminal-header">Execution Report</div>
        <div className="flex-1 flex items-center justify-center text-terminal-text-dim">
          <div className="text-center">
            <div className="text-2xl mb-2">⊙</div>
            <div className="text-sm">No execution report yet</div>
          </div>
        </div>
      </div>
    );
  }

  const duration = (executionReport.total_duration_ms / 1000).toFixed(2);

  return (
    <div className="terminal-container h-full flex flex-col">
      {/* Header */}
      <div className="terminal-header">
        <div className="flex items-center justify-between">
          <span>Execution Report</span>
          {selectedNodeId && (
            <span className="text-terminal-border text-xs">
              [Filtered: {selectedNodeId}]
            </span>
          )}
        </div>
      </div>

      {/* Summary */}
      <ExecutionSummary report={executionReport} />

      {/* Steps List */}
      <div className="flex-1 overflow-y-auto terminal-scanline">
        <ExecutionStepList
          steps={executionReport.trace.steps}
          selectedNodeId={selectedNodeId}
        />
      </div>

      {/* Footer with duration */}
      <div className="terminal-footer flex justify-between">
        <span>Duration: {duration}s</span>
        <span>
          {new Date(executionReport.start_time).toLocaleTimeString()} -{' '}
          {new Date(executionReport.end_time).toLocaleTimeString()}
        </span>
      </div>
    </div>
  );
};
