import { useCallback, useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { ServiceNode } from './ServiceNode';
import { WorkflowGraph as WorkflowGraphType, WorkflowNode } from '../../types/workflow';
import { useWorkflowStore } from '../../store/workflowStore';

const nodeTypes = {
  start: ServiceNode,
  action: ServiceNode,
  end: ServiceNode,
};

interface WorkflowGraphProps {
  graph: WorkflowGraphType;
}

export function WorkflowGraph({ graph }: WorkflowGraphProps) {
  const { nodeExecutionState, selectNode } = useWorkflowStore();

  // Enrich nodes with execution state
  const enrichedNodes = useMemo(() => {
    return graph.nodes.map((node) => {
      const executionState = nodeExecutionState.get(node.id);
      return {
        ...node,
        data: {
          ...node.data,
          executionState: executionState?.status,
        },
      } as WorkflowNode;
    });
  }, [graph.nodes, nodeExecutionState]);

  const [nodes, , onNodesChange] = useNodesState(enrichedNodes);
  const [edges, , onEdgesChange] = useEdgesState(graph.edges);

  const onInit = useCallback((reactFlowInstance: any) => {
    reactFlowInstance.fitView({ padding: 0.2 });
  }, []);

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: any) => {
      if (node.id !== 'start' && node.id !== 'end') {
        selectNode(node.id);
      }
    },
    [selectNode]
  );

  return (
    <div className="h-full w-full bg-terminal-bg">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        onInit={onInit}
        onNodeClick={onNodeClick}
        fitView
        attributionPosition="bottom-left"
      >
        <Background color="#15803d" gap={16} />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            const workflowNode = node as WorkflowNode;
            const executionState = workflowNode.data.executionState;

            if (executionState === 'success') return '#22c55e';
            if (executionState === 'failed') return '#ef4444';
            if (executionState === 'running') return '#eab308';
            if (executionState === 'skipped') return '#9ca3af';

            switch (node.type) {
              case 'start':
                return '#10b981';
              case 'end':
                return '#10b981';
              case 'action':
                return '#15803d';
              default:
                return '#047857';
            }
          }}
        />
      </ReactFlow>
    </div>
  );
}
