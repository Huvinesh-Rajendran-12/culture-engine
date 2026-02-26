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

          .loading-indicator {
            display: inline-block;
            color: #8b949e;
            animation: pulse 1.5s ease-in-out infinite;
          }

          @keyframes pulse {
            0%, 100% { opacity: 0.4; }
            50% { opacity: 1; }
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
