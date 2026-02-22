"""Base agent runner using pi-agent-core for FlowForge."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Optional

from pi_agent_core import (
    Agent,
    AgentEvent,
    AgentOptions,
    AgentTool,
    AssistantMessage,
    Model,
    TextContent,
    ToolCall,
)

from ..config import get_settings
from .anthropic_stream import stream_anthropic
from .tools import DEFAULT_TOOL_NAMES, create_flowforge_tools


def _resolve_model_id(model_name: str, *, use_openrouter: bool = False) -> str:
    aliases = {
        "haiku": "claude-3-5-haiku-latest",
        "sonnet": "claude-3-7-sonnet-latest",
        "opus": "claude-3-opus-latest",
    }

    openrouter_aliases = {
        "haiku": "anthropic/claude-haiku-4.5",
    }

    if use_openrouter and model_name in openrouter_aliases:
        return openrouter_aliases[model_name]

    return aliases.get(model_name, model_name)


def _extract_text_blocks(message: AssistantMessage | None) -> list[str]:
    if not isinstance(message, AssistantMessage):
        return []

    text_blocks: list[str] = []
    for block in message.content:
        if isinstance(block, TextContent) and block.text.strip():
            text_blocks.append(block.text)
    return text_blocks


def _extract_tool_calls(message: AssistantMessage | None) -> list[ToolCall]:
    if not isinstance(message, AssistantMessage):
        return []
    return [block for block in message.content if isinstance(block, ToolCall)]


def _extract_tool_result_text(result: Any) -> str:
    chunks: list[str] = []

    if result and getattr(result, "content", None):
        for content_block in result.content:
            if getattr(content_block, "type", None) == "text":
                chunks.append(content_block.text)

    return "\n".join(chunks).strip()


def _last_assistant_message(messages: list[Any] | None) -> AssistantMessage | None:
    if not messages:
        return None

    for message in reversed(messages):
        if isinstance(message, AssistantMessage):
            return message

    return None


def _usage_dict(message: AssistantMessage | None) -> dict[str, Any] | None:
    if not isinstance(message, AssistantMessage):
        return None
    usage = getattr(message, "usage", None)
    if usage is None:
        return None
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    if isinstance(usage, dict):
        return usage
    return None


@dataclass
class _EventTranslator:
    emitted_tool_use_ids: set[str] = field(default_factory=set)
    emitted_errors: set[str] = field(default_factory=set)
    emitted_text_events: int = 0

    def _tool_use_event(
        self,
        *,
        tool_name: str,
        tool_input: Any,
        tool_use_id: str | None,
    ) -> dict[str, Any] | None:
        if tool_use_id and tool_use_id in self.emitted_tool_use_ids:
            return None
        if tool_use_id:
            self.emitted_tool_use_ids.add(tool_use_id)

        return {
            "type": "tool_use",
            "content": {
                "tool": tool_name,
                "input": tool_input or {},
                "id": tool_use_id,
            },
        }

    def _error_event(self, message: str | None) -> dict[str, Any] | None:
        if not message:
            return None
        cleaned = message.strip()
        if not cleaned or cleaned in self.emitted_errors:
            return None
        self.emitted_errors.add(cleaned)
        return {"type": "error", "content": cleaned}

    def _translate_message_update(self, event: AgentEvent) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []

        stream_event = getattr(event, "assistant_message_event", None)
        stream_type = getattr(stream_event, "type", None)

        if stream_type == "text_delta":
            delta = getattr(stream_event, "delta", "")
            if isinstance(delta, str) and delta:
                out.append({"type": "text_delta", "content": delta})

        elif stream_type == "toolcall_end":
            tool_call = getattr(stream_event, "tool_call", None)
            if isinstance(tool_call, ToolCall):
                payload = self._tool_use_event(
                    tool_name=getattr(tool_call, "name", ""),
                    tool_input=getattr(tool_call, "arguments", {}),
                    tool_use_id=getattr(tool_call, "id", None),
                )
                if payload:
                    out.append(payload)

        return out

    def translate(self, event: AgentEvent) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []

        if event.type == "message_update":
            out.extend(self._translate_message_update(event))

        elif event.type == "message_end" and isinstance(
            event.message, AssistantMessage
        ):
            for text_block in _extract_text_blocks(event.message):
                self.emitted_text_events += 1
                out.append({"type": "text", "content": text_block})

            for tool_call in _extract_tool_calls(event.message):
                payload = self._tool_use_event(
                    tool_name=getattr(tool_call, "name", ""),
                    tool_input=getattr(tool_call, "arguments", {}),
                    tool_use_id=getattr(tool_call, "id", None),
                )
                if payload:
                    out.append(payload)

            maybe_error = self._error_event(
                getattr(event.message, "error_message", None)
            )
            if maybe_error:
                out.append(maybe_error)

        elif event.type == "tool_execution_start":
            payload = self._tool_use_event(
                tool_name=getattr(event, "tool_name", ""),
                tool_input=getattr(event, "args", {}),
                tool_use_id=getattr(event, "tool_call_id", None),
            )
            if payload:
                out.append(payload)

        elif event.type == "tool_execution_end":
            out.append(
                {
                    "type": "tool_result",
                    "content": {
                        "tool_use_id": event.tool_call_id,
                        "tool": event.tool_name,
                        "result": _extract_tool_result_text(event.result),
                        "is_error": event.is_error,
                    },
                }
            )

            if event.is_error:
                maybe_error = self._error_event(
                    _extract_tool_result_text(event.result)
                    or f"Tool failed: {event.tool_name}"
                )
                if maybe_error:
                    out.append(maybe_error)

        elif event.type == "turn_end":
            assistant = (
                event.message if isinstance(event.message, AssistantMessage) else None
            )
            maybe_error = self._error_event(getattr(assistant, "error_message", None))
            if maybe_error:
                out.append(maybe_error)

        elif event.type == "agent_end":
            assistant = _last_assistant_message(event.messages)
            usage = _usage_dict(assistant)
            final_text = "\n".join(_extract_text_blocks(assistant)).strip() or None
            stop_reason = getattr(assistant, "stop_reason", None)
            error_message = getattr(assistant, "error_message", None)

            subtype = "completed"
            if error_message or stop_reason in {"error", "aborted"}:
                subtype = stop_reason or "error"

            if final_text and self.emitted_text_events == 0:
                self.emitted_text_events += 1
                out.append({"type": "text", "content": final_text})

            out.append(
                {
                    "type": "result",
                    "content": {
                        "subtype": subtype,
                        "stop_reason": stop_reason,
                        "final_text": final_text,
                        "error_message": error_message,
                        "cost_usd": usage.get("cost", {}).get("total", 0)
                        if usage
                        else 0,
                        "usage": usage,
                    },
                }
            )

            maybe_error = self._error_event(error_message)
            if maybe_error:
                out.append(maybe_error)

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

    use_openrouter = bool(settings.openrouter_api_key) or (
        isinstance(settings.anthropic_base_url, str)
        and "openrouter.ai" in settings.anthropic_base_url.lower()
    )

    all_tools = tools_override or create_flowforge_tools(
        team=team, workspace_dir=workspace_dir
    )

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
            id=_resolve_model_id(settings.default_model, use_openrouter=use_openrouter),
        )
    )
    agent.set_system_prompt(system_prompt)
    agent.set_tools(tools)

    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
    turn_count = 0
    translator = _EventTranslator()

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

        for payload in translator.translate(event):
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
