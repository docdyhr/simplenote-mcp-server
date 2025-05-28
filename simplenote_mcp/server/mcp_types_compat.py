"""
Compatibility types for MCP server.

This module provides type definitions that are needed by the codebase but
may be missing in the installed version of MCP.
"""

from typing import Any

from mcp import types as orig_mcp_types


# Define missing types
class Context:
    """Context for MCP requests."""

    def __init__(self, request_id: str | None = None) -> None:
        self.request_id = request_id


# Create compatibility classes for request/response types
class ListResourcesRequest:
    """Request for listing resources."""

    def __init__(
        self,
        tag: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        sort_by: str | None = None,
        sort_direction: str | None = None,
    ) -> None:
        self.tag = tag
        self.limit = limit
        self.offset = offset
        self.sort_by = sort_by
        self.sort_direction = sort_direction


class ReadResourceRequest:
    """Request for reading a resource."""

    def __init__(self, uri: str | None = None) -> None:
        self.uri = uri


class GetNoteRequest:
    """Request for getting a note."""

    def __init__(self, note_id: str | None = None) -> None:
        self.note_id = note_id


class UpdateNoteRequest:
    """Request for updating a note."""

    def __init__(
        self,
        note_id: str | None = None,
        content: str | None = None,
        tags: list[str] | None = None,
        version: int | None = None,
        markdown: bool | None = None,
        pinned: bool | None = None,
    ) -> None:
        self.note_id = note_id
        self.content = content
        self.tags = tags
        self.version = version
        self.markdown = markdown
        self.pinned = pinned


class DeleteNoteRequest:
    """Request for deleting a note."""

    def __init__(self, note_id: str | None = None, force: bool = False) -> None:
        self.note_id = note_id
        self.force = force


class AddTagsToNoteRequest:
    """Request for adding tags to a note."""

    def __init__(
        self, note_id: str | None = None, tags: list[str] | None = None
    ) -> None:
        self.note_id = note_id
        self.tags = tags


class RemoveTagsFromNoteRequest:
    """Request for removing tags from a note."""

    def __init__(
        self, note_id: str | None = None, tags: list[str] | None = None
    ) -> None:
        self.note_id = note_id
        self.tags = tags


class ReplaceTagsOnNoteRequest:
    """Request for replacing tags on a note."""

    def __init__(
        self, note_id: str | None = None, tags: list[str] | None = None
    ) -> None:
        self.note_id = note_id
        self.tags = tags


class ListPromptsRequest:
    """Request for listing prompts."""

    def __init__(self) -> None:
        pass


class GetPromptRequest:
    """Request for getting a prompt."""

    def __init__(
        self, name: str | None = None, arguments: dict[str, Any] | None = None
    ) -> None:
        self.name = name
        self.arguments = arguments or {}


# Response classes
class GetNoteResponse:
    """Response for getting a note."""

    def __init__(self, note: Any | None = None) -> None:
        self.note = note


class UpdateNoteResponse:
    """Response for updating a note."""

    def __init__(self, note: Any | None = None, status: str | None = None) -> None:
        self.note = note
        self.status = status


class DeleteNoteResponse:
    """Response for deleting a note."""

    def __init__(self, status: str | None = None, note_id: str | None = None) -> None:
        self.status = status
        self.note_id = note_id


class AddTagsToNoteResponse:
    """Response for adding tags to a note."""

    def __init__(
        self,
        success: bool = False,
        id: str | None = None,  # noqa: A002
        status: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        self.success = success
        self.id = id
        self.status = status
        self.tags = tags or []


class RemoveTagsFromNoteResponse:
    """Response for removing tags from a note."""

    def __init__(
        self,
        success: bool = False,
        id: str | None = None,  # noqa: A002
        status: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        self.success = success
        self.id = id
        self.status = status
        self.tags = tags or []


class ReplaceTagsOnNoteResponse:
    """Response for replacing tags on a note."""

    def __init__(
        self,
        success: bool = False,
        id: str | None = None,  # noqa: A002
        status: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        self.success = success
        self.id = id
        self.status = status
        self.tags = tags or []


class ListResourcesResponse:
    """Response for listing resources."""

    def __init__(self, resources: list[Any] | None = None) -> None:
        self.resources = resources or []


class ReadResourceResponse:
    """Response for reading a resource."""

    def __init__(self, contents: list[Any] | None = None) -> None:
        self.contents = contents or []


class GetPromptResponse:
    """Response for getting a prompt."""

    def __init__(self, messages: list[Any] | None = None) -> None:
        self.messages = messages or []


class ListPromptsResponse:
    """Response for listing prompts."""

    def __init__(self, prompts: list[Any] | None = None) -> None:
        self.prompts = prompts or []


# Map other types to orig_mcp_types equivalents for compatibility
Content = (
    orig_mcp_types.TextContent
    | orig_mcp_types.ImageContent
    | orig_mcp_types.BlobResourceContents
    | orig_mcp_types.TextResourceContents
)
TextContent = orig_mcp_types.TextContent
TextResourceContents = orig_mcp_types.TextResourceContents
Resource = orig_mcp_types.Resource
Prompt = orig_mcp_types.Prompt
PromptArgument = orig_mcp_types.PromptArgument
PromptMessage = orig_mcp_types.PromptMessage


# Custom types not in MCP
class ErrorContent:
    """Content for error responses."""

    def __init__(
        self,
        type: str = "error",
        message: str | None = None,
        category: str | None = None,
    ) -> None:
        self.type = type
        self.message = message
        self.category = category


class ToolRequestContent:
    """Content for tool request responses."""

    def __init__(
        self,
        type: str = "tool_request",
        tool_name: str | None = None,
        tool_arguments: dict[str, Any] | None = None,
    ) -> None:
        self.type = type
        self.tool_name = tool_name
        self.tool_arguments = tool_arguments or {}
