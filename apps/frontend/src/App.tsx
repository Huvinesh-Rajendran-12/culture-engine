import { useState, useEffect } from 'react';
import { WorkflowDAGPanel } from './components/workflow/WorkflowDAGPanel';
import { ExecutionReportPanel } from './components/execution/ExecutionReportPanel';
import { ChatDialog } from './components/chat/ChatDialog';

export function App() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Keyboard shortcut: Ctrl+K or Cmd+K to open dialog
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsDialogOpen(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="h-screen bg-terminal-bg relative">
      {/* Chat Button - Fixed top-right */}
      <button
        onClick={() => setIsDialogOpen(true)}
        className="terminal-button fixed top-4 right-4 z-10"
      >
        + New Workflow
      </button>

      {/* Two-panel layout */}
      <div className="flex h-full overflow-hidden">
        {/* Left Panel: Workflow DAG (60%) */}
        <div className="w-[60%] flex-shrink-0 border-r-2 border-dotted border-terminal-border">
          <WorkflowDAGPanel />
        </div>

        {/* Right Panel: Execution Report (40%) */}
        <div className="w-[40%] flex-shrink-0">
          <ExecutionReportPanel />
        </div>
      </div>

      {/* Chat Dialog */}
      <ChatDialog
        isOpen={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
      />
    </div>
  );
}
