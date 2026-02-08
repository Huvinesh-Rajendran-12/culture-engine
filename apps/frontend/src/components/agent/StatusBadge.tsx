import React from 'react';

interface StatusBadgeProps {
  isStreaming: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ isStreaming }) => {
  if (!isStreaming) {
    return (
      <div className="status-badge status-success">
        <span>●</span>
        <span>Ready</span>
      </div>
    );
  }

  return (
    <div className="status-badge status-running terminal-pulse">
      <span>●</span>
      <span>Processing</span>
    </div>
  );
};
