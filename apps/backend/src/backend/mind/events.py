"""Canonical event envelope for Mind delegation streams."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _new_event_id() -> str:
    return uuid.uuid4().hex[:16]


class Event(BaseModel):
    """Protocol-agnostic event envelope.

    Every event emitted during a Mind delegation run carries these fields.
    The ``type`` and ``content`` fields are unchanged from the original raw
    dicts so existing consumers (frontend SSE readers) keep working.  The
    additional fields (``id``, ``seq``, ``ts``, ``trace_id``) are additive.
    """

    id: str = Field(default_factory=_new_event_id)
    type: str
    seq: int = 0
    ts: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    trace_id: str = ""
    content: Any = None


class EventStream:
    """Wraps a raw ``AsyncGenerator[dict, None]`` and yields ``Event`` objects.

    Assigns ``id``, ``seq``, ``ts``, and ``trace_id`` to each raw event dict
    produced by the underlying generator (e.g. ``delegate_to_mind``).
    """

    def __init__(
        self,
        raw: AsyncGenerator[dict, None],
        trace_id: str,
    ) -> None:
        self._raw = raw
        self._trace_id = trace_id
        self._seq = 0

    async def __aiter__(self) -> AsyncGenerator[Event, None]:
        async for raw_event in self._raw:
            event = Event(
                type=raw_event.get("type", "unknown"),
                content=raw_event.get("content"),
                seq=self._seq,
                trace_id=self._trace_id,
            )
            self._seq += 1
            yield event
