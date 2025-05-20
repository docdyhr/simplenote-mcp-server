"""
Patch for MCP Server to add decorators that are missing in the current version.

This patch adds decorator methods to the Server class that allow registering resource providers,
tools, and prompt providers with the server. These decorators were expected by the codebase but
are missing in the installed version of MCP.
"""

import logging
from typing import Any, Callable, Dict, TypeVar

from mcp.server import Server

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# Store decorated functions
RESOURCE_PROVIDERS: Dict[str, Callable] = {}
TOOL_PROVIDERS: Dict[str, Callable] = {}
PROMPT_PROVIDERS: Dict[str, Callable] = {}


def apply_patch() -> None:
    """Apply the patch to add decorators to the Server class."""
    logger.info("Applying MCP Server patch to add missing decorators")

    def resource_provider(_=None) -> Callable[[F], F]:
        """Decorator for registering resource providers."""

        def decorator(func: F) -> F:
            name = func.__name__
            if name.startswith("handle_"):
                name = name[7:]  # Remove 'handle_' prefix
            logger.info(f"Registering resource provider: {name}")
            RESOURCE_PROVIDERS[name] = func
            return func

        return decorator

    def list_resources(_=None) -> Callable[[F], F]:
        """Decorator for registering list_resources handler."""

        def decorator(func: F) -> F:
            logger.info(f"Registering list_resources handler: {func.__name__}")
            RESOURCE_PROVIDERS["list_resources"] = func
            return func

        return decorator

    def read_resource(_=None) -> Callable[[F], F]:
        """Decorator for registering read_resource handler."""

        def decorator(func: F) -> F:
            logger.info(f"Registering read_resource handler: {func.__name__}")
            RESOURCE_PROVIDERS["read_resource"] = func
            return func

        return decorator

    def tool(_) -> Callable[[F], F]:
        """Decorator for registering tools."""

        def decorator(func: F) -> F:
            name = func.__name__
            logger.info(f"Registering tool: {name}")
            TOOL_PROVIDERS[name] = func
            return func

        return decorator

    def call_tool(_=None) -> Callable[[F], F]:
        """Decorator for registering call_tool handlers."""

        def decorator(func: F) -> F:
            name = func.__name__
            if name.startswith("handle_"):
                name = name[7:]  # Remove 'handle_' prefix
            logger.info(f"Registering call_tool handler: {name}")
            TOOL_PROVIDERS[name] = func
            return func

        return decorator

    def prompt_provider(_=None) -> Callable[[F], F]:
        """Decorator for registering prompt providers."""

        def decorator(func: F) -> F:
            name = func.__name__
            if name.startswith("handle_"):
                name = name[7:]  # Remove 'handle_' prefix
            logger.info(f"Registering prompt provider: {name}")
            PROMPT_PROVIDERS[name] = func
            return func

        return decorator

    def list_prompts(_=None) -> Callable[[F], F]:
        """Decorator for registering list_prompts handler."""

        def decorator(func: F) -> F:
            logger.info(f"Registering list_prompts handler: {func.__name__}")
            PROMPT_PROVIDERS["list_prompts"] = func
            return func

        return decorator

    def get_prompt(_=None) -> Callable[[F], F]:
        """Decorator for registering get_prompt handler."""

        def decorator(func: F) -> F:
            logger.info(f"Registering get_prompt handler: {func.__name__}")
            PROMPT_PROVIDERS["get_prompt"] = func
            return func

        return decorator

    # Add the decorator methods to the Server class
    Server.resource_provider = resource_provider
    Server.list_resources = list_resources
    Server.read_resource = read_resource
    Server.tool = tool
    Server.call_tool = call_tool
    Server.prompt_provider = prompt_provider
    Server.list_prompts = list_prompts
    Server.get_prompt = get_prompt

    logger.info("MCP Server patch applied successfully")
