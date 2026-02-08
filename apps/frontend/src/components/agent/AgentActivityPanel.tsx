import React, { useEffect, useRef } from 'react';
import { useWorkflowStore } from '../../store/workflowStore';
import { AgentMessage } from './AgentMessage';
import { StatusBadge } from './StatusBadge';

export const AgentActivityPanel: React.FC = () => {
  const { messages, isStreaming, costUsd, totalTokens } = useWorkflowStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="terminal-container h-full flex flex-col">
      {/* Header */}
      <div className="terminal-header flex items-center justify-between">
        <span>Agent Activity</span>
        <StatusBadge isStreaming={isStreaming} />
      </div>

      {/* Message Stream */}
      <div className="flex-1 overflow-y-auto terminal-scroll terminal-scanline">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-terminal-text-dim">
            <div className="text-center">
              <div className="text-2xl mb-2">▶</div>
              <div className="text-sm">Waiting for input...</div>
            </div>
          </div>
        ) : (
          <div>
            {messages.map((message) => (
              <AgentMessage key={message.id} message={message} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Footer with metrics */}
      {(costUsd > 0 || totalTokens > 0) && (
        <div className="terminal-footer flex justify-between">
          <span>Cost: ${costUsd.toFixed(4)}</span>
          <span>Tokens: {totalTokens.toLocaleString()}</span>
        </div>
      )}
    </div>
  );
};
