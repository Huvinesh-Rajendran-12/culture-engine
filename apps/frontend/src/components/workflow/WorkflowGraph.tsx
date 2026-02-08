import { useCallback } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { CustomNode } from './CustomNode';
import { WorkflowGraph as WorkflowGraphType } from '../../types/workflow';

const nodeTypes = {
  start: CustomNode,
  action: CustomNode,
  end: CustomNode,
};

interface WorkflowGraphProps {
  graph: WorkflowGraphType;
}

export function WorkflowGraph({ graph }: WorkflowGraphProps) {
  const [nodes, , onNodesChange] = useNodesState(graph.nodes);
  const [edges, , onEdgesChange] = useEdgesState(graph.edges);

  const onInit = useCallback((reactFlowInstance: any) => {
    reactFlowInstance.fitView({ padding: 0.2 });
  }, []);

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        onInit={onInit}
        fitView
      >
        <Background color="#1a3a1a" gap={20} size={1} />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            const service = node.data?.service;
            if (service === 'slack') return '#E01E5A';
            if (service === 'jira') return '#0052CC';
            if (service === 'google') return '#4285F4';
            if (service === 'hr') return '#8B5CF6';
            if (service === 'github') return '#F0883E';
            if (node.type === 'start' || node.type === 'end') return '#166534';
            return '#4ade80';
          }}
        />
      </ReactFlow>
    </div>
  );
}
