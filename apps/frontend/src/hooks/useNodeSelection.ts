import { useCallback } from 'react';
import { useWorkflowStore } from '../store/workflowStore';

export function useNodeSelection() {
  const { selectedNodeId, selectNode } = useWorkflowStore();

  const handleNodeClick = useCallback(
    (nodeId: string | null) => {
      // Toggle selection: if already selected, deselect
      if (selectedNodeId === nodeId) {
        selectNode(null);
      } else {
        selectNode(nodeId);
      }
    },
    [selectedNodeId, selectNode]
  );

  const clearSelection = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  return {
    selectedNodeId,
    handleNodeClick,
    clearSelection,
  };
}
