"""Domain exceptions for Mind operations.

These are protocol-agnostic — HTTP handlers translate them to appropriate
status codes; other transports (WebSocket, MCP, CLI) can map them differently.
"""


class MindNotFoundError(Exception):
    """Raised when a Mind profile does not exist."""


class TaskNotFoundError(Exception):
    """Raised when a Task does not exist."""


class ValidationError(Exception):
    """Raised when a request fails domain validation."""
