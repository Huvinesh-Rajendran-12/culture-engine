"""Anthropic streaming adapter for pi-agent-core."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
from typing import Any

import anthropic

from pi_agent_core import (
    AgentContext,
    AssistantMessage,
    AssistantMessageEvent,
    ImageContent,
    Model,
    SimpleStreamOptions,
    StreamDoneEvent,
    StreamErrorEvent,
    StreamStartEvent,
    StreamTextDeltaEvent,
    StreamTextEndEvent,
    StreamTextStartEvent,
    StreamThinkingDeltaEvent,
    StreamThinkingEndEvent,
    StreamThinkingStartEvent,
    StreamToolCallDeltaEvent,
    StreamToolCallEndEvent,
    StreamToolCallStartEvent,
    TextContent,
    ThinkingContent,
    ToolCall,
    ToolResultMessage,
    UserMessage,
)

STOP_REASON_MAP: dict[str, str] = {
    "end_turn": "stop",
    "max_tokens": "length",
    "tool_use": "toolUse",
}


class AnthropicAsyncStream:
    """Async stream bridging Anthropic SSE events to AssistantMessageEvent iteration."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[AssistantMessageEvent | None] = asyncio.Queue()
        self._final_message: AssistantMessage | None = None
        self._done = asyncio.Event()

    def push(self, event: AssistantMessageEvent) -> None:
        self._queue.put_nowait(event)

    def set_result(self, message: AssistantMessage) -> None:
        self._final_message = message
        self._done.set()

    def end(self) -> None:
        self._queue.put_nowait(None)

    def __aiter__(self) -> AnthropicAsyncStream:
        return self

    async def __anext__(self) -> AssistantMessageEvent:
        item = await self._queue.get()
        if item is None:
            raise StopAsyncIteration
        return item

    async def result(self) -> AssistantMessage:
        await self._done.wait()
        if self._final_message is None:
            raise RuntimeError("No result available")
        return self._final_message


def _convert_user_content(content: TextContent | ImageContent) -> dict[str, Any]:
    if isinstance(content, TextContent):
        return {"type": "text", "text": content.text}
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": content.media_type,
            "data": content.data,
        },
    }


def _convert_messages(messages: list[Any]) -> list[dict[str, Any]]:
    api_messages: list[dict[str, Any]] = []

    for msg in messages:
        if isinstance(msg, UserMessage):
            api_messages.append(
                {
                    "role": "user",
                    "content": [_convert_user_content(c) for c in msg.content],
                }
            )

        elif isinstance(msg, AssistantMessage):
            blocks: list[dict[str, Any]] = []
            for c in msg.content:
                if isinstance(c, TextContent) and c.text:
                    blocks.append({"type": "text", "text": c.text})
                elif isinstance(c, ThinkingContent) and c.thinking:
                    block: dict[str, Any] = {"type": "thinking", "thinking": c.thinking}
                    if c.thinking_signature:
                        block["signature"] = c.thinking_signature
                    blocks.append(block)
                elif isinstance(c, ToolCall):
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": c.id,
                            "name": c.name,
                            "input": c.arguments,
                        }
                    )
            if blocks:
                api_messages.append({"role": "assistant", "content": blocks})

        elif isinstance(msg, ToolResultMessage):
            tool_result_block: dict[str, Any] = {
                "type": "tool_result",
                "tool_use_id": msg.tool_call_id,
                "content": [_convert_user_content(c) for c in msg.content],
                "is_error": msg.is_error,
            }
            if api_messages and api_messages[-1].get("_tool_results"):
                api_messages[-1]["content"].append(tool_result_block)
            else:
                api_messages.append(
                    {
                        "role": "user",
                        "content": [tool_result_block],
                        "_tool_results": True,
                    }
                )

    for msg_dict in api_messages:
        msg_dict.pop("_tool_results", None)

    return api_messages


def _convert_tools(tools: list[Any]) -> list[dict[str, Any]]:
    result = []
    for tool in tools:
        result.append(
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": {
                    "type": tool.parameters.type,
                    "properties": tool.parameters.properties,
                    "required": tool.parameters.required,
                },
            }
        )
    return result


async def stream_anthropic(
    model: Model,
    context: AgentContext,
    options: SimpleStreamOptions,
) -> dict[str, Any]:
    stream = AnthropicAsyncStream()

    partial = AssistantMessage(
        api=model.api,
        provider=model.provider,
        model=model.id,
    )

    api_key = (
        options.api_key
        or os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
    )
    base_url = os.environ.get("ANTHROPIC_BASE_URL")

    if not api_key:
        raise RuntimeError(
            "No API key configured. Set OPENROUTER_API_KEY or ANTHROPIC_API_KEY."
        )

    client_kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = anthropic.AsyncAnthropic(**client_kwargs)
    api_messages = _convert_messages(context.messages)

    kwargs: dict[str, Any] = {
        "model": model.id,
        "messages": api_messages,
    }

    if context.system_prompt:
        kwargs["system"] = context.system_prompt

    kwargs["max_tokens"] = (
        options.max_tokens if options.max_tokens is not None else 8192
    )

    if options.temperature is not None:
        kwargs["temperature"] = options.temperature

    if context.tools:
        kwargs["tools"] = _convert_tools(context.tools)

    if options.reasoning and options.reasoning != "off":
        budget = 4096
        if options.thinking_budgets:
            budget = getattr(options.thinking_budgets, options.reasoning, budget)
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}

    content_block_types: dict[int, str] = {}
    tool_json_accumulators: dict[int, str] = {}

    async def _run() -> None:
        nonlocal partial

        try:
            async with client.messages.stream(**kwargs) as raw_stream:
                async for event in raw_stream:
                    if options.cancel_event and options.cancel_event.is_set():
                        raise RuntimeError("Request aborted by user")

                    _process_anthropic_event(
                        event,
                        partial,
                        stream,
                        content_block_types,
                        tool_json_accumulators,
                    )

            if options.cancel_event and options.cancel_event.is_set():
                raise RuntimeError("Request aborted by user")

            stream.set_result(partial)
            stream.end()

        except Exception as error:
            error_message = str(error)
            reason = (
                "aborted"
                if (options.cancel_event and options.cancel_event.is_set())
                else "error"
            )
            partial.stop_reason = reason
            partial.error_message = error_message
            stream.push(StreamErrorEvent(reason=reason, error=partial))
            stream.set_result(partial)
            stream.end()

    asyncio.create_task(_run())
    return {
        "events": stream,
        "result": stream.result,
    }


def _process_anthropic_event(
    event: Any,
    partial: AssistantMessage,
    stream: AnthropicAsyncStream,
    content_block_types: dict[int, str],
    tool_json_accumulators: dict[int, str],
) -> None:
    event_type = event.type

    if event_type == "message_start":
        if hasattr(event, "message") and hasattr(event.message, "usage"):
            partial.usage.input = getattr(event.message.usage, "input_tokens", 0)
        stream.push(StreamStartEvent(partial=partial))

    elif event_type == "content_block_start":
        idx = event.index
        block = event.content_block

        while len(partial.content) <= idx:
            partial.content.append(TextContent())

        if block.type == "text":
            partial.content[idx] = TextContent()
            content_block_types[idx] = "text"
            stream.push(StreamTextStartEvent(content_index=idx, partial=partial))

        elif block.type == "thinking":
            partial.content[idx] = ThinkingContent()
            content_block_types[idx] = "thinking"
            stream.push(StreamThinkingStartEvent(content_index=idx, partial=partial))

        elif block.type == "tool_use":
            partial.content[idx] = ToolCall(id=block.id, name=block.name)
            content_block_types[idx] = "tool_use"
            tool_json_accumulators[idx] = ""
            stream.push(StreamToolCallStartEvent(content_index=idx, partial=partial))

    elif event_type == "content_block_delta":
        idx = event.index
        delta = event.delta

        if delta.type == "text_delta":
            content = partial.content[idx]
            if isinstance(content, TextContent):
                content.text += delta.text
            stream.push(
                StreamTextDeltaEvent(
                    content_index=idx, delta=delta.text, partial=partial
                )
            )

        elif delta.type == "thinking_delta":
            content = partial.content[idx]
            if isinstance(content, ThinkingContent):
                content.thinking += delta.thinking
            stream.push(
                StreamThinkingDeltaEvent(
                    content_index=idx, delta=delta.thinking, partial=partial
                )
            )

        elif delta.type == "input_json_delta":
            content = partial.content[idx]
            if isinstance(content, ToolCall):
                if content.partial_json is None:
                    content.partial_json = ""
                content.partial_json += delta.partial_json
                tool_json_accumulators[idx] = content.partial_json
                with contextlib.suppress(json.JSONDecodeError):
                    content.arguments = json.loads(content.partial_json)
            stream.push(
                StreamToolCallDeltaEvent(
                    content_index=idx, delta=delta.partial_json, partial=partial
                )
            )

    elif event_type == "content_block_stop":
        idx = event.index
        block_type = content_block_types.get(idx)

        if block_type == "text":
            content = partial.content[idx]
            text = content.text if isinstance(content, TextContent) else ""
            stream.push(
                StreamTextEndEvent(content_index=idx, content=text, partial=partial)
            )

        elif block_type == "thinking":
            content = partial.content[idx]
            thinking = content.thinking if isinstance(content, ThinkingContent) else ""
            stream.push(
                StreamThinkingEndEvent(
                    content_index=idx, content=thinking, partial=partial
                )
            )

        elif block_type == "tool_use":
            content = partial.content[idx]
            if isinstance(content, ToolCall):
                accumulated = tool_json_accumulators.get(idx, "")
                if accumulated:
                    with contextlib.suppress(json.JSONDecodeError):
                        content.arguments = json.loads(accumulated)
                content.partial_json = None
                stream.push(
                    StreamToolCallEndEvent(
                        content_index=idx, tool_call=content, partial=partial
                    )
                )

    elif event_type == "message_delta":
        if hasattr(event, "delta"):
            raw_reason = getattr(event.delta, "stop_reason", None)
            if raw_reason:
                partial.stop_reason = STOP_REASON_MAP.get(raw_reason, "stop")

        if hasattr(event, "usage"):
            input_tokens = getattr(event.usage, "input_tokens", None)
            if input_tokens is not None:
                partial.usage.input = input_tokens
            partial.usage.output = getattr(event.usage, "output_tokens", 0)
            partial.usage.total_tokens = partial.usage.input + partial.usage.output

        stream.push(StreamDoneEvent(reason=partial.stop_reason, message=partial))
