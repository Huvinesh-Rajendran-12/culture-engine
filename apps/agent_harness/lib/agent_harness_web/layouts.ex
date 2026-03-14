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
        <title>Culture Engine</title>
        <style>
          *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

          :root {
            --bg-primary: #0a0e14;
            --bg-secondary: #111820;
            --bg-tertiary: #1a2130;
            --bg-hover: #1e2736;
            --border: #1e2a3a;
            --border-active: #2d4a6f;
            --text-primary: #d4dce8;
            --text-secondary: #7a8ba0;
            --text-muted: #4d5f73;
            --accent-blue: #5b9bd5;
            --accent-green: #6bc46d;
            --accent-purple: #b48ead;
            --accent-red: #d36050;
            --accent-amber: #d4a959;
            --accent-cyan: #78c4d4;
          }

          body {
            background: var(--bg-primary);
            color: var(--text-primary);
            font-family: -apple-system, 'Inter', 'Segoe UI', system-ui, sans-serif;
            font-size: 14px;
            line-height: 1.65;
            -webkit-font-smoothing: antialiased;
          }

          code, pre, .mono {
            font-family: 'SF Mono', 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
            font-size: 13px;
          }

          /* --- Navigation --- */

          .nav {
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 8px 20px;
            border-bottom: 1px solid var(--border);
            background: var(--bg-secondary);
          }

          .nav-brand {
            font-weight: 700;
            font-size: 14px;
            color: var(--accent-blue);
            margin-right: 20px;
            letter-spacing: -0.3px;
            text-decoration: none;
          }

          .nav-brand span {
            color: var(--text-muted);
            font-weight: 400;
          }

          .nav-link {
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 13px;
            color: var(--text-secondary);
            text-decoration: none;
            transition: color 0.15s, background 0.15s;
          }

          .nav-link:hover {
            color: var(--text-primary);
            background: var(--bg-tertiary);
          }

          .nav-link.active {
            color: var(--accent-blue);
            background: rgba(91, 155, 213, 0.1);
          }

          .nav-spacer { flex: 1; }

          .nav-status {
            font-size: 12px;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 6px;
          }

          .nav-status .dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--accent-green);
            animation: breathe 3s ease-in-out infinite;
          }

          @keyframes breathe {
            0%, 100% { opacity: 0.5; }
            50% { opacity: 1; }
          }

          /* --- App Shell --- */

          .app-shell {
            display: flex;
            flex-direction: column;
            height: calc(100vh - 45px);
          }

          /* --- Messages / Conversation --- */

          .conversation {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
          }

          .conversation-inner {
            max-width: 820px;
            margin: 0 auto;
          }

          .msg {
            margin-bottom: 16px;
            animation: msg-in 0.15s ease-out;
          }

          @keyframes msg-in {
            from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
          }

          .msg-user {
            padding: 12px 16px;
            background: var(--bg-tertiary);
            border-radius: 10px;
            border: 1px solid var(--border);
            color: var(--text-primary);
          }

          .msg-user .msg-label {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            margin-bottom: 4px;
          }

          .msg-agent {
            padding: 12px 0;
            color: var(--text-primary);
            line-height: 1.7;
          }

          .msg-agent p { margin-bottom: 8px; }
          .msg-agent p:last-child { margin-bottom: 0; }

          .msg-agent pre {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px 16px;
            overflow-x: auto;
            margin: 8px 0;
          }

          .msg-agent code {
            background: var(--bg-tertiary);
            padding: 2px 5px;
            border-radius: 4px;
            font-size: 12.5px;
          }

          .msg-agent pre code {
            background: none;
            padding: 0;
          }

          .msg-error {
            padding: 10px 14px;
            background: rgba(211, 96, 80, 0.08);
            border: 1px solid rgba(211, 96, 80, 0.2);
            border-radius: 8px;
            color: var(--accent-red);
            font-size: 13px;
          }

          .msg-system {
            color: var(--text-muted);
            font-size: 13px;
            font-style: italic;
            padding: 4px 0;
          }

          /* --- Tool Calls (collapsed by default) --- */

          .tool-group {
            margin: 8px 0;
            border-radius: 8px;
            border: 1px solid var(--border);
            background: var(--bg-secondary);
            overflow: hidden;
          }

          .tool-header {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 14px;
            cursor: pointer;
            user-select: none;
            font-size: 12px;
            color: var(--text-secondary);
            transition: background 0.1s;
          }

          .tool-header:hover {
            background: var(--bg-tertiary);
          }

          .tool-icon {
            font-size: 10px;
            color: var(--accent-purple);
            transition: transform 0.15s;
          }

          .tool-icon.open { transform: rotate(90deg); }

          .tool-name {
            color: var(--accent-purple);
            font-family: 'SF Mono', monospace;
            font-weight: 500;
          }

          .tool-body {
            display: none;
            padding: 10px 14px;
            border-top: 1px solid var(--border);
            font-size: 12px;
            max-height: 250px;
            overflow-y: auto;
          }

          .tool-body.open { display: block; }

          .tool-input {
            color: var(--accent-purple);
            white-space: pre-wrap;
            word-break: break-word;
          }

          .tool-result {
            color: var(--accent-cyan);
            white-space: pre-wrap;
            word-break: break-word;
            margin-top: 6px;
            padding-top: 6px;
            border-top: 1px solid var(--border);
          }

          /* --- Drone Panels --- */

          .drone-panel {
            margin: 12px 0;
            border-radius: 10px;
            border: 1px solid var(--border);
            background: var(--bg-secondary);
            overflow: hidden;
            animation: msg-in 0.2s ease-out;
          }

          .drone-header {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 16px;
            cursor: pointer;
            user-select: none;
            transition: background 0.1s;
          }

          .drone-header:hover { background: var(--bg-tertiary); }

          .drone-icon {
            font-size: 14px;
            color: var(--accent-purple);
          }

          .drone-info { flex: 1; }

          .drone-name {
            font-weight: 600;
            font-size: 13px;
            color: var(--text-primary);
          }

          .drone-task-text {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 2px;
            line-height: 1.4;
          }

          .drone-badge {
            font-size: 10px;
            padding: 3px 10px;
            border-radius: 20px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
          }

          .drone-badge.running {
            background: rgba(107, 196, 109, 0.12);
            color: var(--accent-green);
            animation: breathe 2s ease-in-out infinite;
          }

          .drone-badge.complete {
            background: rgba(107, 196, 109, 0.08);
            color: var(--accent-green);
            opacity: 0.7;
          }

          .drone-badge.error {
            background: rgba(211, 96, 80, 0.12);
            color: var(--accent-red);
          }

          .drone-toggle {
            color: var(--text-muted);
            font-size: 10px;
            transition: transform 0.15s;
          }

          .drone-toggle.open { transform: rotate(90deg); }

          .drone-events {
            border-top: 1px solid var(--border);
            padding: 10px 16px;
            max-height: 300px;
            overflow-y: auto;
            font-size: 12px;
          }

          .drone-event {
            padding: 3px 0;
            white-space: pre-wrap;
            word-break: break-word;
          }

          .drone-event.tool_use { color: var(--accent-purple); }
          .drone-event.tool_use::before {
            content: "tool ";
            font-weight: 600;
            opacity: 0.6;
          }

          .drone-event.tool_result {
            color: var(--accent-cyan);
            max-height: 120px;
            overflow-y: auto;
          }
          .drone-event.tool_result::before {
            content: "result ";
            font-weight: 600;
            opacity: 0.6;
          }

          .drone-event.text { color: var(--text-primary); }
          .drone-event.error { color: var(--accent-red); }

          .drone-panel.complete { opacity: 0.7; }
          .drone-panel.error { border-color: rgba(211, 96, 80, 0.3); }

          /* --- Input Area --- */

          .input-area {
            border-top: 1px solid var(--border);
            padding: 16px 20px;
            background: var(--bg-secondary);
          }

          .input-inner {
            max-width: 820px;
            margin: 0 auto;
          }

          .input-form {
            display: flex;
            gap: 10px;
            align-items: flex-end;
          }

          .input-wrap {
            flex: 1;
            position: relative;
          }

          .input-field {
            width: 100%;
            resize: none;
            background: var(--bg-primary);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 11px 16px;
            color: var(--text-primary);
            font-family: inherit;
            font-size: 14px;
            line-height: 1.5;
            outline: none;
            min-height: 44px;
            max-height: 200px;
            overflow-y: auto;
            transition: border-color 0.15s;
          }

          .input-field:focus {
            border-color: var(--accent-blue);
          }

          .input-field::placeholder {
            color: var(--text-muted);
          }

          .input-field:disabled {
            opacity: 0.5;
          }

          .send-btn {
            background: var(--accent-blue);
            color: #fff;
            border: none;
            border-radius: 10px;
            padding: 11px 22px;
            font-family: inherit;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.15s;
            white-space: nowrap;
          }

          .send-btn:hover { background: #4e8bbf; }
          .send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

          /* --- Loading indicator --- */

          .thinking {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 0;
            color: var(--text-muted);
            font-size: 13px;
          }

          .thinking-dots span {
            display: inline-block;
            width: 4px;
            height: 4px;
            border-radius: 50%;
            background: var(--text-muted);
            animation: dot-bounce 1.4s infinite ease-in-out both;
          }

          .thinking-dots span:nth-child(1) { animation-delay: -0.32s; }
          .thinking-dots span:nth-child(2) { animation-delay: -0.16s; }

          @keyframes dot-bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
          }

          /* --- Observatory --- */

          .obs-layout {
            display: flex;
            height: calc(100vh - 45px);
          }

          .obs-sidebar {
            width: 340px;
            border-right: 1px solid var(--border);
            padding: 20px;
            overflow-y: auto;
            background: var(--bg-secondary);
          }

          .obs-title {
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            margin-bottom: 16px;
          }

          .obs-agent {
            padding: 10px 14px;
            border-radius: 8px;
            margin-bottom: 4px;
            cursor: pointer;
            border: 1px solid transparent;
            transition: background 0.1s, border-color 0.1s;
          }

          .obs-agent:hover { background: var(--bg-tertiary); }

          .obs-agent.selected {
            background: var(--bg-tertiary);
            border-color: var(--border-active);
          }

          .obs-agent-name {
            font-size: 13px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
          }

          .obs-agent-meta {
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 2px;
          }

          .obs-tier {
            font-size: 10px;
            padding: 2px 8px;
            border-radius: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.3px;
          }

          .obs-tier.mind { background: rgba(91, 155, 213, 0.12); color: var(--accent-blue); }
          .obs-tier.drone { background: rgba(180, 142, 173, 0.12); color: var(--accent-purple); }

          .obs-main {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
          }

          .obs-empty {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: var(--text-muted);
            font-size: 14px;
          }

          .obs-event {
            margin-bottom: 6px;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 13px;
            white-space: pre-wrap;
            word-break: break-word;
          }

          .obs-event.text { color: var(--text-primary); }
          .obs-event.tool_use { color: var(--accent-purple); background: var(--bg-secondary); }
          .obs-event.tool_result { color: var(--accent-cyan); background: var(--bg-secondary); }
          .obs-event.error { color: var(--accent-red); background: rgba(211, 96, 80, 0.06); }
          .obs-event.system { color: var(--text-muted); font-style: italic; }

          /* --- Scrollbar --- */

          ::-webkit-scrollbar { width: 6px; }
          ::-webkit-scrollbar-track { background: transparent; }
          ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
          ::-webkit-scrollbar-thumb:hover { background: var(--border-active); }

          /* --- Utility --- */

          .tier-badge {
            display: inline-block;
            font-size: 10px;
            padding: 2px 8px;
            border-radius: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.3px;
          }

          .tier-badge.mind { background: rgba(91, 155, 213, 0.12); color: var(--accent-blue); }
          .tier-badge.drone { background: rgba(180, 142, 173, 0.12); color: var(--accent-purple); }
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
            },
            AutoResize: {
              mounted() {
                this.el.addEventListener("input", () => this.resize())
                this.el.addEventListener("keydown", (e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault()
                    this.el.closest("form").dispatchEvent(new Event("submit", {bubbles: true, cancelable: true}))
                  }
                })
                this.resize()
              },
              updated() { this.resize() },
              resize() {
                this.el.style.height = "auto"
                this.el.style.height = Math.min(this.el.scrollHeight, 200) + "px"
              }
            },
            ToolToggle: {
              mounted() {
                this.el.addEventListener("click", () => {
                  const body = this.el.nextElementSibling
                  const icon = this.el.querySelector(".tool-icon")
                  body.classList.toggle("open")
                  icon.classList.toggle("open")
                })
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
