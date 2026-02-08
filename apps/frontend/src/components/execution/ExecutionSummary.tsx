import React from 'react';
import { ExecutionReport } from '../../types/execution';

interface ExecutionSummaryProps {
  report: ExecutionReport;
}

export const ExecutionSummary: React.FC<ExecutionSummaryProps> = ({
  report,
}) => {
  const { summary, trace } = report;

  return (
    <div className="p-4 space-y-3">
      {/* Summary counts */}
      <div className="grid grid-cols-2 gap-3">
        <div className="terminal-border p-2">
          <div className="text-terminal-text-dim text-xs mb-1">Total Steps</div>
          <div className="text-terminal-text text-xl font-bold">
            {summary.total_steps}
          </div>
        </div>
        <div className="terminal-border p-2">
          <div className="text-terminal-text-dim text-xs mb-1">Successful</div>
          <div className="text-status-success text-xl font-bold">
            {summary.successful}
          </div>
        </div>
        <div className="terminal-border p-2">
          <div className="text-terminal-text-dim text-xs mb-1">Failed</div>
          <div className="text-status-failed text-xl font-bold">
            {summary.failed}
          </div>
        </div>
        <div className="terminal-border p-2">
          <div className="text-terminal-text-dim text-xs mb-1">Skipped</div>
          <div className="text-status-skipped text-xl font-bold">
            {summary.skipped}
          </div>
        </div>
      </div>

      {/* Dependency violations warning */}
      {trace.dependency_violations.length > 0 && (
        <div className="terminal-border border-status-failed p-3">
          <div className="text-status-failed font-semibold text-sm mb-2">
            ⚠ Dependency Violations
          </div>
          <div className="space-y-1">
            {trace.dependency_violations.map((violation, index) => (
              <div key={index} className="text-status-failed text-xs">
                • {violation}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
