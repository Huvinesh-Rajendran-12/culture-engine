import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { WorkflowNode } from '../../types/workflow';
import { useWorkflowStore } from '../../store/workflowStore';

const getServiceColorClass = (service?: string): string => {
  if (!service) return 'border-terminal-border';

  const serviceLower = service.toLowerCase();
  if (serviceLower.includes('slack')) return 'node-slack';
  if (serviceLower.includes('hr')) return 'node-hr';
  if (serviceLower.includes('google')) return 'node-google';
  if (serviceLower.includes('github')) return 'node-github';
  if (serviceLower.includes('jira')) return 'node-jira';
  return 'border-terminal-border';
};

const getStatusIcon = (status?: string): string => {
  switch (status) {
    case 'success':
      return '✓';
    case 'failed':
      return '✗';
    case 'running':
      return '...';
    case 'skipped':
      return '⊘';
    case 'pending':
      return '○';
    default:
      return '';
  }
};

const getStatusColorClass = (status?: string): string => {
  switch (status) {
    case 'success':
      return 'border-status-success';
    case 'failed':
      return 'border-status-failed';
    case 'running':
      return 'border-status-running terminal-pulse';
    case 'skipped':
      return 'border-status-skipped';
    case 'pending':
      return 'border-status-pending';
    default:
      return '';
  }
};

export const ServiceNode: React.FC<NodeProps<WorkflowNode['data']>> = ({
  data,
  id,
}) => {
  const { selectNode, selectedNodeId, nodeExecutionState } = useWorkflowStore();

  // Get execution state for this node
  const executionState = nodeExecutionState.get(id);
  const executionStatus = executionState?.status || data.executionState;

  const isStart = id === 'start';
  const isEnd = id === 'end';
  const isSelected = selectedNodeId === id;

  const handleClick = () => {
    if (!isStart && !isEnd) {
      selectNode(isSelected ? null : id);
    }
  };

  // Determine border color based on service and execution state
  let borderClass = '';
  if (executionStatus) {
    borderClass = getStatusColorClass(executionStatus);
  } else if (!isStart && !isEnd) {
    borderClass = getServiceColorClass(data.service);
  } else {
    borderClass = 'border-terminal-border';
  }

  const baseClasses = `
    px-4 py-3
    rounded-none
    border-2 border-dotted
    bg-terminal-bg
    text-terminal-text
    font-mono text-sm
    cursor-pointer
    transition-all
    ${borderClass}
    ${isSelected ? 'ring-2 ring-terminal-border-bright' : ''}
  `;

  return (
    <div className={baseClasses} onClick={handleClick}>
      {!isStart && <Handle type="target" position={Position.Top} />}

      <div className="flex items-center gap-2">
        {executionStatus && (
          <span className={`font-bold ${getStatusColorClass(executionStatus)}`}>
            {getStatusIcon(executionStatus)}
          </span>
        )}

        <div>
          <div className="font-semibold">{data.label}</div>
          {data.description && (
            <div className="text-xs text-terminal-text-dim mt-1">
              {data.description}
            </div>
          )}
          {data.service && (
            <div className="text-xs text-terminal-border-bright mt-1">
              [{data.service}]
            </div>
          )}
        </div>
      </div>

      {!isEnd && <Handle type="source" position={Position.Bottom} />}
    </div>
  );
};
