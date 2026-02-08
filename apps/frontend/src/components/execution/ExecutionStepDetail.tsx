import React from 'react';
import { TraceStep } from '../../types/execution';

interface ExecutionStepDetailProps {
  step: TraceStep;
  isSelected?: boolean;
}

const getStatusIcon = (status: string): string => {
  switch (status) {
    case 'success':
      return '✓';
    case 'failed':
      return '✗';
    case 'running':
      return '...';
    case 'skipped':
      return '⊘';
    default:
      return '○';
  }
};

const getServiceColor = (service: string): string => {
  const serviceLower = service.toLowerCase();
  if (serviceLower.includes('slack')) return 'text-service-slack';
  if (serviceLower.includes('hr')) return 'text-service-hr';
  if (serviceLower.includes('google')) return 'text-service-google';
  if (serviceLower.includes('github')) return 'text-service-github';
  if (serviceLower.includes('jira')) return 'text-service-jira';
  return 'text-terminal-text';
};

export const ExecutionStepDetail: React.FC<ExecutionStepDetailProps> = ({
  step,
  isSelected = false,
}) => {
  const statusClass = `status-${step.status}`;
  const serviceColor = getServiceColor(step.service);

  return (
    <div
      className={`terminal-message ${
        isSelected ? 'bg-terminal-border bg-opacity-20' : ''
      }`}
    >
      {/* Header with status and service */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`${statusClass} text-lg font-bold`}>
            {getStatusIcon(step.status)}
          </span>
          <span className={`font-semibold ${serviceColor}`}>
            [{step.service}]
          </span>
          <span className="text-terminal-text">{step.action}</span>
        </div>
        {step.duration_ms && (
          <span className="text-terminal-text-dim text-xs">
            {step.duration_ms}ms
          </span>
        )}
      </div>

      {/* Node ID */}
      <div className="text-terminal-text-dim text-xs mb-2">
        Node: {step.node_id}
      </div>

      {/* Parameters */}
      {Object.keys(step.parameters).length > 0 && (
        <div className="mb-2">
          <div className="text-terminal-text-dim text-xs mb-1">Parameters:</div>
          <div className="terminal-code">
            <pre className="text-xs">
              {JSON.stringify(step.parameters, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Result */}
      {step.result && (
        <div className="mb-2">
          <div className="text-terminal-text-dim text-xs mb-1">Result:</div>
          <div className="terminal-code">
            <pre className="text-xs">
              {JSON.stringify(step.result, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Error */}
      {step.error && (
        <div className="terminal-message-error mt-2 p-2">
          <div className="font-semibold text-xs mb-1">ERROR:</div>
          <div className="text-xs">{step.error}</div>
        </div>
      )}

      {/* Timestamp */}
      <div className="text-terminal-text-dim text-xs mt-2">
        {new Date(step.timestamp).toLocaleTimeString()}
      </div>
    </div>
  );
};
