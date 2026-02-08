import { useEffect, useRef, useState } from 'react';
import { useSSEStream } from '../../hooks/useSSEStream';
import { useWorkflowStore } from '../../store/workflowStore';

interface ChatDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ChatDialog({ isOpen, onClose }: ChatDialogProps) {
  const [description, setDescription] = useState('');
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const { startStream } = useSSEStream();
  const { isStreaming } = useWorkflowStore();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-focus textarea when dialog opens
  useEffect(() => {
    if (isOpen && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isOpen]);

  // Reset submitted flag when dialog opens
  useEffect(() => {
    if (isOpen) {
      setHasSubmitted(false);
    }
  }, [isOpen]);

  // Close dialog once streaming starts after submission
  useEffect(() => {
    if (hasSubmitted && isStreaming) {
      // Clear input and close dialog
      setDescription('');
      setHasSubmitted(false);
      onClose();
    }
  }, [hasSubmitted, isStreaming, onClose]);

  // Close on Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim() || isStreaming) return;

    // Mark that we've submitted
    setHasSubmitted(true);

    // Start workflow generation
    await startStream(description);
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="terminal-backdrop"
        onClick={handleBackdropClick}
      />

      {/* Dialog */}
      <div className="terminal-dialog">
        <div className="w-full max-w-2xl mx-4">
          <div className="terminal-container terminal-border">
            {/* Header */}
            <div className="terminal-header">
              &gt; New Workflow
            </div>

            {/* Body */}
            <form onSubmit={handleSubmit}>
              <div className="p-4">
                <textarea
                  ref={textareaRef}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe the workflow you want to generate..."
                  className="w-full h-40 bg-terminal-bg text-terminal-text border-2 border-dotted border-terminal-border p-3 font-mono resize-none focus:outline-none focus:border-terminal-border-bright"
                  disabled={isStreaming}
                />
              </div>

              {/* Footer */}
              <div className="terminal-footer flex justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="terminal-button"
                  disabled={isStreaming}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="terminal-button"
                  disabled={!description.trim() || isStreaming}
                >
                  {isStreaming ? 'Generating...' : 'Generate'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}
