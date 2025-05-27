"""Type stubs for MCP library."""

from typing import Any

class MCP:
    """Base MCP class stub for type checking."""

    pass

class MCPServer:
    """MCP Server stub for type checking."""

    pass

class types:
    """MCP types stub."""

    class TextResourceContents:
        """Text resource contents."""

        text: str
        uri: str
        meta: dict[str, Any]

    class ReadResourceResult:
        """Resource read result."""

        contents: list[Any]
        meta: dict[str, Any]

    class ToolCallResult:
        """Tool call result."""

        text: str
        meta: dict[str, Any]

    class Resource:
        """Resource representation."""

        uri: str
        name: str
        description: str | None
        meta: dict[str, Any]
