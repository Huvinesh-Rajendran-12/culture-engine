import { useCallback } from 'react';
import { useWorkflowStore } from '../store/workflowStore';
import { Message } from '../types/api';
import { extractWorkflowFromToolUse, parseWorkflowCode, parseWorkflowJSON } from '../utils/workflowParser';

export function useSSEStream() {
  const { addMessage, setStreaming, setWorkflowGraph, setExecutionReport, reset } = useWorkflowStore();

  const startStream = useCallback(
    async (description: string) => {
      reset();
      setStreaming(true);
      console.log('[useSSEStream] Starting stream with description:', description);

      try {
        console.log('[useSSEStream] Fetching /api/workflows/generate');
        const response = await fetch('/api/workflows/generate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ description }),
        });

        console.log('[useSSEStream] Response status:', response.status, response.ok);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) {
          throw new Error('No response body');
        }

        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');

          // Keep the last incomplete line in the buffer
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                console.log('[useSSEStream] Received message:', data.type, data);

                const message: Message = {
                  id: crypto.randomUUID(),
                  timestamp: Date.now(),
                  type: data.type,
                  content: data.content,
                } as Message;

                console.log('[useSSEStream] Adding message to store:', message);
                addMessage(message);

                // Check if this is a workflow.py write operation
                if (message.type === 'tool_use') {
                  const workflowCode = extractWorkflowFromToolUse(message.content.input);
                  if (workflowCode) {
                    const graph = parseWorkflowCode(workflowCode);
                    if (graph.nodes.length > 0) {
                      setWorkflowGraph(graph);
                    }
                  }
                }

                // Handle workflow message type from backend
                if (message.type === 'workflow') {
                  // message.content has shape { workflow: {...} }
                  const workflowData = (message.content as any).workflow;
                  console.log('[useSSEStream] Received workflow data:', workflowData);
                  const graph = parseWorkflowJSON(workflowData);
                  console.log('[useSSEStream] Parsed workflow graph:', graph);
                  if (graph.nodes.length > 0) {
                    setWorkflowGraph(graph);
                    console.log('[useSSEStream] Workflow graph set with', graph.nodes.length, 'nodes');
                  }
                }

                // Handle execution_report message type
                if (message.type === 'execution_report') {
                  const report = (message.content as any).report;
                  console.log('[useSSEStream] Received execution report:', report);
                  setExecutionReport(report);
                }
              } catch (error) {
                console.error('Error parsing SSE message:', error, line);
              }
            }
          }
        }
      } catch (error) {
        console.error('[useSSEStream] Error during stream:', error);
        const errorMessage: Message = {
          id: crypto.randomUUID(),
          timestamp: Date.now(),
          type: 'error',
          content: error instanceof Error ? error.message : 'Unknown error occurred',
        };
        addMessage(errorMessage);
      } finally {
        console.log('[useSSEStream] Stream ended, setting streaming to false');
        setStreaming(false);
      }
    },
    [addMessage, setStreaming, setWorkflowGraph, setExecutionReport, reset]
  );

  return { startStream };
}
