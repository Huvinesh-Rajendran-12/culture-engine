defmodule AgentHarnessWeb.Layouts do
  use Phoenix.Component

  def root(assigns) do
    ~H"""
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="csrf-token" content={Phoenix.Controller.get_csrf_token()} />
        <title>Agent Harness REPL</title>
        <style>
          * { margin: 0; padding: 0; box-sizing: border-box; }

          body {
            background: #0d1117;
            color: #c9d1d9;
            font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', monospace;
            font-size: 14px;
            line-height: 1.6;
          }

          #repl-container {
            display: flex;
            flex-direction: column;
            height: 100vh;
            max-width: 900px;
            margin: 0 auto;
            padding: 16px;
          }

          .header {
            padding: 12px 0;
            border-bottom: 1px solid #21262d;
            margin-bottom: 12px;
            color: #58a6ff;
            font-weight: 600;
          }

          .messages {
            flex: 1;
            overflow-y: auto;
            padding-bottom: 16px;
          }

          .message {
            margin-bottom: 12px;
            padding: 8px 12px;
            border-radius: 6px;
            white-space: pre-wrap;
            word-break: break-word;
          }

          .message.user {
            color: #79c0ff;
          }
          .message.user::before {
            content: "you> ";
            color: #58a6ff;
            font-weight: 600;
          }

          .message.agent {
            color: #7ee787;
          }
          .message.agent::before {
            content: "agent> ";
            color: #3fb950;
            font-weight: 600;
          }

          .message.tool_use {
            color: #d2a8ff;
            background: #161b22;
            border-left: 3px solid #8b5cf6;
            font-size: 13px;
          }
          .message.tool_use::before {
            content: "[tool] ";
            color: #bc8cff;
            font-weight: 600;
          }

          .message.tool_result {
            color: #a5d6ff;
            background: #161b22;
            border-left: 3px solid #388bfd;
            font-size: 13px;
            max-height: 200px;
            overflow-y: auto;
          }
          .message.tool_result::before {
            content: "[result] ";
            color: #58a6ff;
            font-weight: 600;
          }

          .message.error {
            color: #ffa198;
            background: #1a0f0f;
            border-left: 3px solid #f85149;
          }
          .message.error::before {
            content: "[error] ";
            color: #f85149;
            font-weight: 600;
          }

          .message.system {
            color: #8b949e;
            font-style: italic;
          }

          .tier-badge {
            display: inline-block;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 12px;
            margin-left: 8px;
            font-weight: 400;
            text-transform: uppercase;
            letter-spacing: 0.5px;
          }
          .tier-badge { background: #1f3a5f; color: #58a6ff; }
          .tier-badge.drone { background: #2d1f3a; color: #d2a8ff; }

          .input-area {
            border-top: 1px solid #21262d;
            padding-top: 12px;
          }

          .input-area form {
            display: flex;
            gap: 8px;
          }

          .input-area input {
            flex: 1;
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 10px 14px;
            color: #c9d1d9;
            font-family: inherit;
            font-size: 14px;
            outline: none;
          }

          .input-area input:focus {
            border-color: #58a6ff;
            box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.15);
          }

          .input-area input:disabled {
            opacity: 0.5;
          }

          .input-area button {
            background: #238636;
            color: #fff;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-family: inherit;
            font-size: 14px;
            cursor: pointer;
          }

          .input-area button:hover {
            background: #2ea043;
          }

          .input-area button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
          }

          .header-icon {
            color: #58a6ff;
            font-size: 16px;
            margin-right: 4px;
          }

          .drone-count {
            font-size: 12px;
            color: #d2a8ff;
            margin-left: 12px;
            font-weight: 400;
          }

          .loading-indicator {
            display: inline-block;
            color: #8b949e;
            animation: pulse 1.5s ease-in-out infinite;
          }

          @keyframes pulse {
            0%, 100% { opacity: 0.4; }
            50% { opacity: 1; }
          }

          /* --- Drone Panel --- */

          .drone-panel {
            margin: 12px 0;
            border: 1px solid #30363d;
            border-left: 3px solid #8b5cf6;
            border-radius: 6px;
            background: #161b22;
            overflow: hidden;
            animation: drone-appear 0.2s ease-out;
          }

          @keyframes drone-appear {
            from { opacity: 0; transform: translateY(-4px); }
            to { opacity: 1; transform: translateY(0); }
          }

          .drone-panel.complete {
            border-left-color: #3fb950;
            opacity: 0.85;
          }

          .drone-panel.error {
            border-left-color: #f85149;
          }

          .drone-header {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 12px;
            cursor: pointer;
            background: #1c2128;
            user-select: none;
          }

          .drone-header:hover {
            background: #21262d;
          }

          .drone-indicator {
            color: #d2a8ff;
            font-size: 12px;
          }

          .drone-name {
            color: #d2a8ff;
            font-weight: 600;
            flex: 1;
            font-size: 13px;
          }

          .drone-toggle {
            color: #8b949e;
            font-size: 11px;
          }

          .drone-status-badge {
            font-size: 10px;
            padding: 2px 8px;
            border-radius: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 500;
          }

          .drone-status-badge.running {
            background: #1f2d1f;
            color: #7ee787;
            animation: pulse 1.5s ease-in-out infinite;
          }

          .drone-status-badge.complete {
            background: #1f2d1f;
            color: #3fb950;
          }

          .drone-status-badge.error {
            background: #2d1f1f;
            color: #f85149;
          }

          .drone-task {
            padding: 6px 12px;
            font-size: 12px;
            color: #8b949e;
            border-bottom: 1px solid #21262d;
            white-space: pre-wrap;
            word-break: break-word;
          }

          .drone-panel.collapsed .drone-task,
          .drone-panel.collapsed .drone-events {
            display: none;
          }

          .drone-events {
            padding: 8px 12px;
            max-height: 300px;
            overflow-y: auto;
            font-size: 12px;
          }

          .drone-event {
            padding: 3px 0;
            white-space: pre-wrap;
            word-break: break-word;
          }

          .drone-event.tool_use {
            color: #d2a8ff;
          }
          .drone-event.tool_use::before {
            content: "[tool] ";
            color: #bc8cff;
            font-weight: 600;
          }

          .drone-event.tool_result {
            color: #a5d6ff;
            max-height: 120px;
            overflow-y: auto;
          }
          .drone-event.tool_result::before {
            content: "[result] ";
            color: #58a6ff;
            font-weight: 600;
          }

          .drone-event.text {
            color: #7ee787;
          }
          .drone-event.text::before {
            content: "drone> ";
            color: #3fb950;
            font-weight: 600;
          }

          .drone-event.error {
            color: #ffa198;
          }
          .drone-event.error::before {
            content: "[error] ";
            color: #f85149;
            font-weight: 600;
          }
        </style>
      </head>
      <body>
        <%= @inner_content %>
        <script src="/assets/phoenix.min.js"></script>
        <script src="/assets/phoenix_live_view.min.js"></script>
        <script>
          const Hooks = {
            ScrollBottom: {
              mounted() { this.scrollToBottom() },
              updated() { this.scrollToBottom() },
              scrollToBottom() {
                this.el.scrollTop = this.el.scrollHeight
              }
            }
          }

          const csrfToken = document.querySelector("meta[name='csrf-token']").getAttribute("content")
          const liveSocket = new window.LiveView.LiveSocket("/live", window.Phoenix.Socket, {
            hooks: Hooks,
            params: { _csrf_token: csrfToken }
          })

          liveSocket.connect()
        </script>
      </body>
    </html>
    """
  end
end
