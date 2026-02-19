"""Base agent runner using pi-agent-core for FlowForge."""

from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Optional

from pi_agent_core import Agent, AgentEvent, AgentOptions, AgentTool, AssistantMessage, Model, TextContent, ToolCall
from ..config import get_settings
from .anthropic_stream import stream_anthropic
from .tools import DEFAULT_TOOL_NAMES, create_flowforge_tools

def _resolve_model_id(model_name: str) -> str:
    aliases = {
        "haiku": "claude-3-5-haiku-latest",
        "sonnet": "claude-3-7-sonnet-latest",
        "opus": "claude-3-opus-latest",
    }
    return aliases.get(model_name, model_name)


def _translate_event(event: AgentEvent) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    if event.type == "message_end" and isinstance(event.message, AssistantMessage):
        for block in event.message.content:
            if isinstance(block, TextContent) and block.text.strip():
                out.append({"type": "text", "content": block.text})
            elif isinstance(block, ToolCall):
                out.append(
                    {
                        "type": "tool_use",
                        "content": {
                            "tool": getattr(block, "name", ""),
                            "input": getattr(block, "arguments", {}),
                            "id": getattr(block, "id", None),
                        },
                    }
                )

    elif event.type == "tool_execution_end":
        result = event.result
        content = []
        if result and getattr(result, "content", None):
            for c in result.content:
                if getattr(c, "type", None) == "text":
                    content.append(c.text)

        out.append(
            {
                "type": "tool_result",
                "content": {
                    "tool_use_id": event.tool_call_id,
                    "result": "\n".join(content),
                    "is_error": event.is_error,
                },
            }
        )

    elif event.type == "agent_end":
        usage = None
        messages = event.messages or []
        for message in reversed(messages):
            if isinstance(message, AssistantMessage):
                usage = message.usage.model_dump()
                break

        out.append(
            {
                "type": "result",
                "content": {
                    "subtype": "completed",
                    "cost_usd": usage.get("cost", {}).get("total", 0) if usage else 0,
                    "usage": usage,
                },
            }
        )

    return out


async def run_agent(
    prompt: str,
    system_prompt: str,
    workspace_dir: str,
    team: str,
    allowed_tools: Optional[list[str]] = None,
    tools_override: Optional[list[AgentTool]] = None,
    max_turns: int = 50,
) -> AsyncGenerator[dict[str, Any], None]:
    """Run a pi-agent-core agent and yield streaming events."""
    settings = get_settings()

    all_tools = tools_override or create_flowforge_tools(team=team, workspace_dir=workspace_dir)

    if allowed_tools is None:
        if tools_override is None:
            allowed_tools = DEFAULT_TOOL_NAMES
        else:
            allowed_tools = [tool.name for tool in all_tools]

    tool_set = set(allowed_tools)
    tools = [tool for tool in all_tools if tool.name in tool_set]

    agent = Agent(
        AgentOptions(
            stream_fn=stream_anthropic,
            get_api_key=lambda _provider: (
                settings.openrouter_api_key
                or settings.anthropic_auth_token
                or settings.anthropic_api_key
            ),
        )
    )

    agent.set_model(
        Model(
            api="anthropic-messages",
            provider="anthropic",
            id=_resolve_model_id(settings.default_model),
        )
    )
    agent.set_system_prompt(system_prompt)
    agent.set_tools(tools)

    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
    turn_count = 0

    def on_event(event: AgentEvent) -> None:
        nonlocal turn_count

        if event.type == "turn_end":
            turn_count += 1
            if turn_count >= max_turns:
                agent.abort()
                queue.put_nowait(
                    {
                        "type": "error",
                        "content": f"Max turns reached ({max_turns}). Aborting run.",
                    }
                )

        for payload in _translate_event(event):
            queue.put_nowait(payload)

    unsubscribe = agent.subscribe(on_event)

    async def _run_prompt() -> None:
        try:
            await agent.prompt(prompt)
        except Exception as e:
            queue.put_nowait({"type": "error", "content": str(e)})
        finally:
            queue.put_nowait(None)

    task = asyncio.create_task(_run_prompt())

    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
    finally:
        unsubscribe()
        await task
