import { useWorkflowStore } from '../../store/workflowStore';
import { useExecutionReplay } from '../../hooks/useExecutionReplay';
import { WorkflowGraph } from './WorkflowGraph';
import { Workflow } from 'lucide-react';

export function WorkflowVisualization() {
  const workflowGraph = useWorkflowStore((state) => state.workflowGraph);
  const workflowMetadata = useWorkflowStore((state) => state.workflowMetadata);

  // Activate execution replay animation
  useExecutionReplay();

  if (!workflowGraph) {
    return (
      <div className="h-full flex items-center justify-center bg-terminal-panel">
        <div className="text-center">
          <Workflow className="w-12 h-12 mx-auto mb-3 text-terminal-green-dim opacity-50" />
          <p className="text-xs font-mono text-terminal-text-dim">
            {'> '}no workflow generated_
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-terminal-panel">
      <div className="border-b border-dashed border-terminal-border px-4 py-3">
        <h2 className="text-sm font-mono font-bold text-terminal-green tracking-widest">
          {workflowMetadata.workflowName?.toUpperCase() || 'WORKFLOW DAG'}
        </h2>
        <div className="flex gap-3 text-[10px] font-mono text-terminal-text-dim mt-0.5">
          <span>{workflowMetadata.stepCount} steps</span>
          {workflowMetadata.path && (
            <span className="truncate">{workflowMetadata.path}</span>
          )}
        </div>
      </div>
      <div className="flex-1">
        <WorkflowGraph graph={workflowGraph} />
      </div>
    </div>
  );
}
