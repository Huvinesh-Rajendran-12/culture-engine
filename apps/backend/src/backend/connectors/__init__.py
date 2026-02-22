"""Connector package: real API connector discovery and lifecycle.

Usage:
    from backend.connectors import create_service_layer, close_service_layer

    state, trace, services = create_service_layer(settings)
    try:
        ...
    finally:
        await close_service_layer(services)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

from .base import BaseConnector
from .contracts import ExecutionTrace, ServiceLayerState
from .registry import ConnectorRegistry

if TYPE_CHECKING:
    from ..config import Settings

# Import all built-in connectors to trigger @register decoration
from . import github, google, hr, jira, slack  # noqa: E402, F401


def create_service_layer(
    settings: Settings,
) -> tuple[ServiceLayerState, ExecutionTrace, dict[str, Any]]:
    """Create connector services for currently configured real connectors.

    Simulator fallback has been removed. This returns only connector-backed services.
    """
    state = ServiceLayerState()
    trace = ExecutionTrace()

    http_client = httpx.AsyncClient(timeout=30.0)
    registry = ConnectorRegistry(settings, trace, http_client)

    services: dict[str, Any] = {}
    service_names = set(registry.list_available())

    for name in sorted(service_names):
        connector = registry.get(name)

        if connector is not None and connector.is_configured(settings):
            services[name] = connector

    # Stash the http_client so close_service_layer can always close it,
    # even when no connectors ended up in the service map.
    services["_http_client"] = http_client

    return state, trace, services


async def close_service_layer(services: dict[str, Any]) -> None:
    """Close any connector AsyncClient instances attached to the service map."""
    clients: dict[int, httpx.AsyncClient] = {}

    # Always close the shared http_client created by create_service_layer.
    stashed = services.pop("_http_client", None)
    if isinstance(stashed, httpx.AsyncClient):
        clients[id(stashed)] = stashed

    for service in services.values():
        if isinstance(service, BaseConnector):
            clients[id(service.http)] = service.http

    for client in clients.values():
        await client.aclose()
