import { AgentStreamPanel } from './components/agent/AgentStreamPanel';
import { WorkflowVisualization } from './components/workflow/WorkflowVisualization';
import { ToolActivityPanel } from './components/activity/ToolActivityPanel';

export function App() {
  return (
    <div className="flex h-screen overflow-hidden bg-terminal-bg">
      <div className="w-1/4 flex-shrink-0">
        <AgentStreamPanel />
      </div>
      <div className="flex-1 border-x border-dashed border-terminal-border">
        <WorkflowVisualization />
      </div>
      <div className="w-1/4 flex-shrink-0">
        <ToolActivityPanel />
      </div>
    </div>
  );
}
