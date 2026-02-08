import React from 'react';
import { useWorkflowStore } from '../../store/workflowStore';
import { WorkflowGraph } from './WorkflowGraph';

export const WorkflowDAGPanel: React.FC = () => {
  const { workflowGraph, workflowMetadata } = useWorkflowStore();

  if (!workflowGraph || workflowGraph.nodes.length === 0) {
    return (
      <div className="terminal-container h-full flex flex-col">
        <div className="terminal-header">Workflow DAG</div>
        <div className="flex-1 flex items-center justify-center text-terminal-text-dim">
          <div className="text-center">
            <div className="text-2xl mb-2">◇</div>
            <div className="text-sm">NO WORKFLOW LOADED</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="terminal-container h-full flex flex-col">
      {/* Header */}
      <div className="terminal-header flex items-center justify-between">
        <span>Workflow DAG</span>
        <span className="text-terminal-border text-xs">
          {workflowMetadata.stepCount} steps
        </span>
      </div>

      {/* Graph */}
      <div className="flex-1 terminal-scanline">
        <WorkflowGraph graph={workflowGraph} />
      </div>
    </div>
  );
};
