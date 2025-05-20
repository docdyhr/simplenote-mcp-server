from typing import Any, Dict

from mcp_patch import TOOL_PROVIDERS


async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> Any:
    """Helper to call a registered tool provider by name with arguments."""
    # Look for the main call_tool handler
    if "call_tool" in TOOL_PROVIDERS:
        tool_func = TOOL_PROVIDERS["call_tool"]
        return await tool_func(name, arguments)
    elif name in TOOL_PROVIDERS:
        tool_func = TOOL_PROVIDERS[name]
        # Simulate request and context objects as needed
        request = type("Request", (), {"name": name, **arguments})()
        context = None  # or a mock context if needed
        return await tool_func(request, context)
    else:
        raise ValueError(
            f"Tool '{name}' is not registered. Available: {list(TOOL_PROVIDERS.keys())}"
        )


async def handle_list_tools() -> Any:
    """Helper to list available tools."""
    from simplenote_mcp.server.server import server_instance

    if server_instance:
        return await server_instance.list_tools()
    return []
