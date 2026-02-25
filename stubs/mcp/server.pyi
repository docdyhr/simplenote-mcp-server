"""Type stubs for mcp.server module.

These stubs ensure that Pyright (and other type checkers) correctly understand
that MCP server decorators are identity functions — they register the handler
but return the original function unchanged, preserving its full signature.
"""

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from mcp import types as types

F = TypeVar("F", bound=Callable[..., Any])

class Server:
    """MCP Server stub with identity-preserving decorator types."""

    name: str

    def __init__(self, name: str, version: str | None = None) -> None: ...

    # Resource decorators — identity: the wrapped function keeps its full signature.
    def list_resources(self) -> Callable[[F], F]: ...
    def read_resource(self) -> Callable[[F], F]: ...
    def subscribe_resource(self) -> Callable[[F], F]: ...
    def unsubscribe_resource(self) -> Callable[[F], F]: ...

    # Tool decorators
    def list_tools(self) -> Callable[[F], F]: ...
    def call_tool(self) -> Callable[[F], F]: ...

    # Prompt decorators
    def list_prompts(self) -> Callable[[F], F]: ...
    def get_prompt(self) -> Callable[[F], F]: ...

    # Completion decorator
    def complete(self) -> Callable[[F], F]: ...

    # Lifecycle / transport
    def create_initialization_options(self, **kwargs: Any) -> Any: ...
    async def run(
        self,
        read_stream: Any,
        write_stream: Any,
        initialization_options: Any,
        **kwargs: Any,
    ) -> None: ...

    # Request / notification handlers (populated by decorators)
    request_handlers: dict[Any, Callable[..., Awaitable[Any]]]
    notification_handlers: dict[Any, Callable[..., Awaitable[None]]]
