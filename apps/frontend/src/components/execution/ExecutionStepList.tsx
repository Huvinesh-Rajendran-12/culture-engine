import React from 'react';
import { TraceStep } from '../../types/execution';
import { ExecutionStepDetail } from './ExecutionStepDetail';

interface ExecutionStepListProps {
  steps: TraceStep[];
  selectedNodeId: string | null;
}

export const ExecutionStepList: React.FC<ExecutionStepListProps> = ({
  steps,
  selectedNodeId,
}) => {
  // Filter steps if a node is selected
  const filteredSteps = selectedNodeId
    ? steps.filter((step) => step.node_id === selectedNodeId)
    : steps;

  if (filteredSteps.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-terminal-text-dim">
        <div className="text-center">
          <div className="text-sm">No steps to display</div>
        </div>
      </div>
    );
  }

  return (
    <div className="terminal-scroll">
      {filteredSteps.map((step, index) => (
        <ExecutionStepDetail
          key={`${step.node_id}-${index}`}
          step={step}
          isSelected={step.node_id === selectedNodeId}
        />
      ))}
    </div>
  );
};
