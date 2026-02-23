"""LEGACY shim kept for import-path compatibility.

The Culture Engine runtime no longer depends on the pi-agent-core stream adapter.
Use ``backend.agents.base.run_agent`` directly.
"""

from __future__ import annotations

from typing import Any


async def stream_anthropic(*_: Any, **__: Any) -> dict[str, Any]:
    """Compatibility stub for removed pi-agent-core stream integration."""
    raise RuntimeError(
        "stream_anthropic is no longer used. "
        "Use backend.agents.base.run_agent for Anthropic/OpenRouter execution."
    )
