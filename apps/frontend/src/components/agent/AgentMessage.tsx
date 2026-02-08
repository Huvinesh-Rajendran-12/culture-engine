import React from 'react';
import { Message } from '../../types/api';

interface AgentMessageProps {
  message: Message;
}

export const AgentMessage: React.FC<AgentMessageProps> = ({ message }) => {
  switch (message.type) {
    case 'text':
      return (
        <div className="terminal-message">
          <div className="text-terminal-text">{message.content}</div>
        </div>
      );

    case 'tool_use':
      return (
        <div className="terminal-message terminal-message-tool">
          <div className="text-terminal-border-bright font-semibold mb-1">
            [{message.content.tool}]
          </div>
          <div className="terminal-code">
            <pre className="text-xs">
              {JSON.stringify(message.content.input, null, 2)}
            </pre>
          </div>
        </div>
      );

    case 'result':
      return (
        <div className="terminal-message">
          <div className="text-terminal-text-dim text-xs space-y-1">
            <div>Cost: ${message.content.cost_usd.toFixed(4)}</div>
            <div>Tokens: {message.content.usage.total_tokens}</div>
          </div>
        </div>
      );

    case 'error':
      return (
        <div className="terminal-message terminal-message-error">
          <div className="font-semibold mb-1">[ERROR]</div>
          <div>{message.content}</div>
        </div>
      );

    case 'workspace':
      return (
        <div className="terminal-message">
          <div className="text-terminal-text-dim text-xs">
            Workspace: {message.content.path}
          </div>
        </div>
      );

    case 'workflow':
      return (
        <div className="terminal-message">
          <div className="text-terminal-border-bright font-semibold">
            [WORKFLOW GENERATED]
          </div>
        </div>
      );

    case 'execution_report':
      return (
        <div className="terminal-message">
          <div className="text-terminal-border-bright font-semibold">
            [EXECUTION COMPLETE]
          </div>
        </div>
      );

    default:
      return null;
  }
};
