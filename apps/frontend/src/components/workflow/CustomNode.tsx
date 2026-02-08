import { Handle, Position, NodeProps } from 'reactflow';
import { cn } from '../../utils/cn';
import { useWorkflowStore } from '../../store/workflowStore';
import { Play, Square, CheckCircle } from 'lucide-react';
import { ExecutionStatus } from '../../types/workflow';

const serviceColors: Record<string, string> = {
  slack: '#E01E5A',
  jira: '#0052CC',
  google: '#4285F4',
  hr: '#8B5CF6',
  github: '#F0883E',
};

function StatusDot({ status }: { status?: ExecutionStatus }) {
  if (!status || status === 'pending') return null;

  return (
    <span
      className={cn('w-2 h-2 rounded-full', {
        'bg-terminal-cyan animate-pulse-green': status === 'running',
        'bg-terminal-green': status === 'success',
        'bg-terminal-red': status === 'failed',
        'bg-terminal-text-dim': status === 'skipped',
      })}
    />
  );
}

export function CustomNode({ data, type, id }: NodeProps) {
  const nodeStatus = useWorkflowStore((state) => state.nodeStatuses[id]);
  const service = data.service as string | undefined;
  const borderColor = service ? serviceColors[service] : undefined;

  const Icon = type === 'start' ? Play : type === 'end' ? CheckCircle : Square;

  const isTerminal = type === 'start' || type === 'end';

  return (
    <div
      className={cn(
        'px-4 py-3 rounded border border-dashed min-w-[180px] bg-terminal-card font-mono transition-all',
        {
          'border-terminal-green-dim': isTerminal,
          'border-terminal-border': !isTerminal && !borderColor,
          'shadow-[0_0_10px_rgba(0,255,65,0.15)]': nodeStatus === 'running',
          'shadow-[0_0_8px_rgba(0,255,65,0.1)]': nodeStatus === 'success',
          'shadow-[0_0_8px_rgba(239,68,68,0.15)]': nodeStatus === 'failed',
        }
      )}
      style={borderColor && !isTerminal ? { borderColor, borderLeftWidth: '3px', borderLeftStyle: 'solid' } : undefined}
    >
      {type !== 'start' && <Handle type="target" position={Position.Top} />}
      <div className="flex items-center gap-2">
        <Icon className={cn('w-4 h-4 flex-shrink-0', {
          'text-terminal-green': isTerminal,
          'text-terminal-text-dim': !isTerminal,
        })} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-medium text-terminal-text capitalize">
              {data.label}
            </span>
            <StatusDot status={nodeStatus} />
          </div>
          {data.description && (
            <div className="text-[10px] mt-0.5 text-terminal-text-dim leading-tight">
              {data.description}
            </div>
          )}
          {data.service && (
            <div className="text-[9px] mt-1 text-terminal-text-dim uppercase tracking-wider">
              {data.service}.{data.action}
            </div>
          )}
        </div>
      </div>
      {type !== 'end' && <Handle type="source" position={Position.Bottom} />}
    </div>
  );
}
