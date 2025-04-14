"""Type stubs for MCP library."""

from typing import Any, Dict, List, Optional

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
        meta: Dict[str, Any]

    class ReadResourceResult:
        """Resource read result."""

        contents: List[Any]
        meta: Dict[str, Any]

    class ToolCallResult:
        """Tool call result."""

        text: str
        meta: Dict[str, Any]

    class Resource:
        """Resource representation."""

        uri: str
        name: str
        description: Optional[str]
        meta: Dict[str, Any]
