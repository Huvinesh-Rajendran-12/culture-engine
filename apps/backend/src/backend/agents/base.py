"""Minimal Anthropic/OpenRouter agent runner for Culture Engine."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any, Optional

import anthropic

from ..config import get_settings
from .tools import DEFAULT_TOOL_NAMES, create_culture_engine_tools
from .types import AgentTool, AgentToolResult, TextContent

_STOP_REASON_MAP: dict[str, str] = {
    "end_turn": "stop",
    "max_tokens": "length",
    "tool_use": "toolUse",
}


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


def _extract_tool_result_text(result: AgentToolResult | None) -> str:
    if result is None:
        return ""

    chunks: list[str] = []
    for block in result.content:
        if isinstance(block, TextContent) and block.text:
            chunks.append(block.text)

    return "\n".join(chunks).strip()


def _normalize_stop_reason(reason: str | None) -> str | None:
    if reason is None:
        return None
    return _STOP_REASON_MAP.get(reason, reason)


def _usage_dict(message: Any) -> dict[str, Any] | None:
    usage = getattr(message, "usage", None)
    if usage is None:
        return None

    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)

    payload: dict[str, Any] = {
        "input": input_tokens,
        "output": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }

    if hasattr(usage, "model_dump"):
        payload["raw"] = usage.model_dump(mode="json")

    return payload


def _tool_params(tools: list[AgentTool]) -> list[dict[str, Any]]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": {
                "type": tool.parameters.type,
                "properties": tool.parameters.properties,
                "required": tool.parameters.required,
            },
        }
        for tool in tools
    ]


def _error_payload_once(
    message: str | None,
    emitted_errors: set[str],
) -> dict[str, Any] | None:
    if not isinstance(message, str):
        return None
    cleaned = message.strip()
    if not cleaned or cleaned in emitted_errors:
        return None
    emitted_errors.add(cleaned)
    return {"type": "error", "content": cleaned}


async def run_agent(
    prompt: str,
    system_prompt: str,
    workspace_dir: str,
    team: str,
    allowed_tools: Optional[list[str]] = None,
    tools_override: Optional[list[AgentTool]] = None,
    max_turns: int = 50,
) -> AsyncGenerator[dict[str, Any], None]:
    """Run a minimal agent loop and yield normalized stream events.

    The loop is intentionally simple: request → optional tool execution → continue.
    """
    settings = get_settings()

    use_openrouter = bool(settings.openrouter_api_key) or (
        isinstance(settings.anthropic_base_url, str)
        and "openrouter.ai" in settings.anthropic_base_url.lower()
    )

    all_tools = tools_override or create_culture_engine_tools(
        team=team,
        workspace_dir=workspace_dir,
    )

    if allowed_tools is None:
        if tools_override is None:
            allowed_tools = DEFAULT_TOOL_NAMES
        else:
            allowed_tools = [tool.name for tool in all_tools]

    tool_set = set(allowed_tools)
    tools = [tool for tool in all_tools if tool.name in tool_set]
    tools_by_name = {tool.name: tool for tool in tools}

    api_key = (
        settings.openrouter_api_key
        or settings.anthropic_auth_token
        or settings.anthropic_api_key
    )

    emitted_tool_use_ids: set[str] = set()
    emitted_errors: set[str] = set()
    emitted_text_events = 0

    if not api_key:
        message = "No API key configured. Set OPENROUTER_API_KEY or ANTHROPIC_API_KEY."
        yield {
            "type": "result",
            "content": {
                "subtype": "error",
                "stop_reason": "error",
                "final_text": None,
                "error_message": message,
                "cost_usd": 0,
                "usage": None,
            },
        }
        maybe_error = _error_payload_once(message, emitted_errors)
        if maybe_error:
            yield maybe_error
        return

    client_kwargs: dict[str, Any] = {"api_key": api_key}
    if settings.anthropic_base_url:
        client_kwargs["base_url"] = settings.anthropic_base_url

    client = anthropic.AsyncAnthropic(**client_kwargs)
    model_id = _resolve_model_id(settings.default_model, use_openrouter=use_openrouter)

    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": [{"type": "text", "text": prompt}],
        }
    ]

    turns = 0
    run_error: str | None = None
    forced_subtype: str | None = None
    last_assistant_message: Any = None

    try:
        while True:
            if turns >= max_turns:
                forced_subtype = "aborted"
                run_error = f"Max turns reached ({max_turns}). Aborting run."
                maybe_error = _error_payload_once(run_error, emitted_errors)
                if maybe_error:
                    yield maybe_error
                break

            turns += 1

            request: dict[str, Any] = {
                "model": model_id,
                "messages": messages,
                "max_tokens": 8192,
            }

            if system_prompt:
                request["system"] = system_prompt

            if tools:
                request["tools"] = _tool_params(tools)

            message = await client.messages.create(**request)
            last_assistant_message = message

            assistant_content: list[dict[str, Any]] = []
            tool_calls: list[dict[str, Any]] = []

            for block in getattr(message, "content", []):
                block_type = getattr(block, "type", "")

                if block_type == "text":
                    text = getattr(block, "text", "")
                    assistant_content.append({"type": "text", "text": text})
                    if isinstance(text, str) and text.strip():
                        emitted_text_events += 1
                        yield {"type": "text", "content": text}
                    continue

                if block_type == "thinking":
                    thinking_block: dict[str, Any] = {
                        "type": "thinking",
                        "thinking": getattr(block, "thinking", ""),
                    }
                    signature = getattr(block, "signature", None)
                    if isinstance(signature, str) and signature:
                        thinking_block["signature"] = signature
                    assistant_content.append(thinking_block)
                    continue

                if block_type == "redacted_thinking":
                    assistant_content.append(
                        {
                            "type": "redacted_thinking",
                            "data": getattr(block, "data", ""),
                        }
                    )
                    continue

                if block_type != "tool_use":
                    continue

                raw_tool_call_id = getattr(block, "id", "")
                event_tool_call_id = (
                    raw_tool_call_id
                    if isinstance(raw_tool_call_id, str) and raw_tool_call_id
                    else None
                )
                tool_call_id = event_tool_call_id or f"tool_auto_{turns}_{len(tool_calls) + 1}"
                tool_name = getattr(block, "name", "")
                tool_input = getattr(block, "input", {}) or {}

                if not isinstance(tool_input, dict):
                    with_json = {}
                    if isinstance(tool_input, str):
                        try:
                            with_json = json.loads(tool_input)
                        except json.JSONDecodeError:
                            with_json = {"raw": tool_input}
                    tool_input = with_json

                assistant_content.append(
                    {
                        "type": "tool_use",
                        "id": tool_call_id,
                        "name": tool_name,
                        "input": tool_input,
                    }
                )

                if event_tool_call_id:
                    if event_tool_call_id not in emitted_tool_use_ids:
                        emitted_tool_use_ids.add(event_tool_call_id)
                        yield {
                            "type": "tool_use",
                            "content": {
                                "tool": tool_name,
                                "input": tool_input,
                                "id": event_tool_call_id,
                            },
                        }
                else:
                    yield {
                        "type": "tool_use",
                        "content": {
                            "tool": tool_name,
                            "input": tool_input,
                            "id": None,
                        },
                    }

                tool_calls.append(
                    {
                        "id": tool_call_id,
                        "name": tool_name,
                        "input": tool_input,
                    }
                )

            if assistant_content:
                messages.append({"role": "assistant", "content": assistant_content})

            if not tool_calls:
                break

            tool_results: list[dict[str, Any]] = []

            for call in tool_calls:
                tool_id = call["id"] if isinstance(call["id"], str) else ""
                tool_name = call["name"] if isinstance(call["name"], str) else ""
                tool_input = call["input"] if isinstance(call["input"], dict) else {}

                tool = tools_by_name.get(tool_name)
                is_error = False

                if tool is None:
                    tool_result_text = f"Tool {tool_name} not found"
                    is_error = True
                else:
                    try:
                        result = await tool.execute(tool_id, tool_input)
                        tool_result_text = _extract_tool_result_text(result)
                    except Exception as exc:  # pragma: no cover - defensive boundary
                        tool_result_text = str(exc)
                        is_error = True

                yield {
                    "type": "tool_result",
                    "content": {
                        "tool_use_id": tool_id or None,
                        "tool": tool_name,
                        "result": tool_result_text,
                        "is_error": is_error,
                    },
                }

                if is_error:
                    maybe_error = _error_payload_once(tool_result_text, emitted_errors)
                    if maybe_error:
                        yield maybe_error

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": tool_result_text,
                        "is_error": is_error,
                    }
                )

            if tool_results:
                messages.append({"role": "user", "content": tool_results})

    except Exception as exc:  # pragma: no cover - transport/network boundary
        forced_subtype = "error"
        run_error = str(exc)
        maybe_error = _error_payload_once(run_error, emitted_errors)
        if maybe_error:
            yield maybe_error

    stop_reason = _normalize_stop_reason(
        getattr(last_assistant_message, "stop_reason", None)
    )

    text_blocks: list[str] = []
    if last_assistant_message is not None:
        for block in getattr(last_assistant_message, "content", []):
            if getattr(block, "type", "") != "text":
                continue
            text = getattr(block, "text", "")
            if isinstance(text, str) and text.strip():
                text_blocks.append(text)

    final_text = "\n".join(text_blocks).strip() or None

    subtype = forced_subtype or "completed"
    if not forced_subtype:
        if run_error:
            subtype = "error"
        elif stop_reason in {"error", "aborted"}:
            subtype = stop_reason

    if final_text and emitted_text_events == 0:
        emitted_text_events += 1
        yield {"type": "text", "content": final_text}

    usage = _usage_dict(last_assistant_message)

    yield {
        "type": "result",
        "content": {
            "subtype": subtype,
            "stop_reason": stop_reason,
            "final_text": final_text,
            "error_message": run_error,
            "cost_usd": 0,
            "usage": usage,
        },
    }

    maybe_error = _error_payload_once(run_error, emitted_errors)
    if maybe_error:
        yield maybe_error
