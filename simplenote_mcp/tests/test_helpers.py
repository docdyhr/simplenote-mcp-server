from typing import Any

import mcp.types as types


async def handle_read_resource(uri: str) -> types.ReadResourceResult:
    return await helper_handle_read_resource(uri)


async def handle_call_tool(name: str, arguments: dict[str, Any]) -> Any:
    return await helper_handle_call_tool(name, arguments)


async def handle_list_tools() -> Any:
    return await helper_handle_list_tools()


async def helper_handle_read_resource(uri: str) -> types.ReadResourceResult:
    """Helper to read a resource by URI."""
    from simplenote_mcp.server.server import server_instance

    if server_instance:
        # Import the actual function from server
        from simplenote_mcp.server.server import (
            handle_read_resource as server_handle_read_resource,
        )

        return await server_handle_read_resource(uri)
    else:
        raise ValueError("Server instance not available")


async def helper_handle_call_tool(name: str, arguments: dict[str, Any]) -> Any:
    """Helper to call a tool using the server's handle_call_tool function."""
    from simplenote_mcp.server.server import handle_call_tool as server_handle_call_tool

    return await server_handle_call_tool(name, arguments)


async def helper_handle_list_tools() -> Any:
    """Helper to list available tools."""
    from simplenote_mcp.server.server import server_instance

    if server_instance:
        return await server_instance.list_tools()
    return []
