"""Interactive FlowForge chat built in the same style as pi-agent-core's interactive_tool_check.

Usage:
    OPENROUTER_API_KEY=... ANTHROPIC_BASE_URL=https://openrouter.ai/api \
    uv run python examples/interactive_workflow_generator.py
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from pi_agent_core import Agent, AgentEvent, AgentOptions, Model, TextContent
from pi_agent_core.anthropic import stream_anthropic

from backend.agents.tools import create_flowforge_tools

# Match pi-agent-core example style: explicit OpenRouter-compatible model id.
MODEL = Model(api="anthropic-messages", provider="anthropic", id="anthropic/claude-haiku-4.5")


def build_agent(workspace: str) -> Agent:
    tools = create_flowforge_tools(team="default", workspace_dir=workspace)

    agent = Agent(
        AgentOptions(
            initial_state={
                "model": MODEL,
                "system_prompt": (
                    "You are FlowForge. Be concise and helpful. "
                    "Always answer with at least one sentence of text. "
                    f"If asked to create a workflow, write JSON to {workspace}/workflow.json."
                ),
                "tools": tools,
            },
            stream_fn=stream_anthropic,
        )
    )

    def on_event(event: AgentEvent) -> None:
        if event.type == "tool_execution_start":
            print(f"\n[tool start] {event.tool_name} args={event.args}")
        elif event.type == "tool_execution_end":
            status = "error" if event.is_error else "ok"
            print(f"[tool end] {event.tool_name} ({status})")

    agent.subscribe(on_event)
    return agent


def latest_assistant_text(agent: Agent) -> str:
    assistant = next((m for m in reversed(agent.state.messages) if m.role == "assistant"), None)
    if assistant is None:
        return "[no response]"

    text = "\n".join(c.text for c in assistant.content if isinstance(c, TextContent)).strip()
    if text:
        return text

    # Useful for diagnosing blank output
    if getattr(assistant, "error_message", None):
        return f"[assistant error] {assistant.error_message}"

    return "[empty response]"


async def main() -> None:
    if not (os.environ.get("OPENROUTER_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")):
        raise RuntimeError("Set OPENROUTER_API_KEY or ANTHROPIC_API_KEY first")

    workspace = tempfile.mkdtemp(prefix="flowforge-chat-")
    workflow_file = Path(workspace) / "workflow.json"
    agent = build_agent(workspace)

    print("Interactive FlowForge (core-style)")
    print(f"Workspace: {workspace}")
    print("Type /show-workflow, /workspace, or /exit.\n")

    await agent.prompt("Introduce yourself in one sentence and ask what workflow to build.")
    print(f"assistant> {latest_assistant_text(agent)}\n")

    while True:
        user_input = input("you> ").strip()
        if user_input in {"/exit", "exit", "quit"}:
            print("bye")
            return
        if user_input == "/workspace":
            print(workspace)
            continue
        if user_input == "/show-workflow":
            if workflow_file.exists():
                print(workflow_file.read_text())
            else:
                print("No workflow.json yet.")
            continue
        if not user_input:
            continue

        await agent.prompt(user_input)
        print(f"assistant> {latest_assistant_text(agent)}\n")


if __name__ == "__main__":
    asyncio.run(main())
