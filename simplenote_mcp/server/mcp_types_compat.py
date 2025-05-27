"""
Compatibility types for MCP server.

This module provides type definitions that are needed by the codebase but
may be missing in the installed version of MCP.
"""

from typing import Union

from mcp import types as orig_mcp_types


# Define missing types
class Context:
    """Context for MCP requests."""

    def __init__(self, request_id: str | None = None) -> None:
        self.request_id = request_id


# Create compatibility classes for request/response types
class ListResourcesRequest:
    def __init__(
        self, tag=None, limit=None, offset=0, sort_by=None, sort_direction=None
    ):
        self.tag = tag
        self.limit = limit
        self.offset = offset
        self.sort_by = sort_by
        self.sort_direction = sort_direction


class ReadResourceRequest:
    def __init__(self, uri=None):
        self.uri = uri


class GetNoteRequest:
    def __init__(self, note_id=None):
        self.note_id = note_id


class UpdateNoteRequest:
    def __init__(
        self,
        note_id=None,
        content=None,
        tags=None,
        version=None,
        markdown=None,
        pinned=None,
    ):
        self.note_id = note_id
        self.content = content
        self.tags = tags
        self.version = version
        self.markdown = markdown
        self.pinned = pinned


class DeleteNoteRequest:
    def __init__(self, note_id=None, force=False):
        self.note_id = note_id
        self.force = force


class AddTagsToNoteRequest:
    def __init__(self, note_id=None, tags=None):
        self.note_id = note_id
        self.tags = tags


class RemoveTagsFromNoteRequest:
    def __init__(self, note_id=None, tags=None):
        self.note_id = note_id
        self.tags = tags


class ReplaceTagsOnNoteRequest:
    def __init__(self, note_id=None, tags=None):
        self.note_id = note_id
        self.tags = tags


class ListPromptsRequest:
    def __init__(self):
        pass


class GetPromptRequest:
    def __init__(self, name=None, arguments=None):
        self.name = name
        self.arguments = arguments or {}


# Response classes
class GetNoteResponse:
    def __init__(self, note=None):
        self.note = note


class UpdateNoteResponse:
    def __init__(self, note=None, status=None):
        self.note = note
        self.status = status


class DeleteNoteResponse:
    def __init__(self, status=None, note_id=None):
        self.status = status
        self.note_id = note_id


class AddTagsToNoteResponse:
    def __init__(self, success=False, id=None, status=None, tags=None):
        self.success = success
        self.id = id
        self.status = status
        self.tags = tags or []


class RemoveTagsFromNoteResponse:
    def __init__(self, success=False, id=None, status=None, tags=None):
        self.success = success
        self.id = id
        self.status = status
        self.tags = tags or []


class ReplaceTagsOnNoteResponse:
    def __init__(self, success=False, id=None, status=None, tags=None):
        self.success = success
        self.id = id
        self.status = status
        self.tags = tags or []


class ListResourcesResponse:
    def __init__(self, resources=None):
        self.resources = resources or []


class ReadResourceResponse:
    def __init__(self, contents=None):
        self.contents = contents or []


class GetPromptResponse:
    def __init__(self, messages=None):
        self.messages = messages or []


class ListPromptsResponse:
    def __init__(self, prompts=None):
        self.prompts = prompts or []


# Map other types to orig_mcp_types equivalents for compatibility
Content = Union[
    orig_mcp_types.TextContent,
    orig_mcp_types.ImageContent,
    orig_mcp_types.BlobResourceContents,
    orig_mcp_types.TextResourceContents,
]
TextContent = orig_mcp_types.TextContent
TextResourceContents = orig_mcp_types.TextResourceContents
Resource = orig_mcp_types.Resource
Prompt = orig_mcp_types.Prompt
PromptArgument = orig_mcp_types.PromptArgument
PromptMessage = orig_mcp_types.PromptMessage


# Custom types not in MCP
class ErrorContent:
    def __init__(self, type="error", message=None, category=None):
        self.type = type
        self.message = message
        self.category = category


class ToolRequestContent:
    def __init__(self, type="tool_request", toolName=None, toolArguments=None):
        self.type = type
        self.toolName = toolName
        self.toolArguments = toolArguments or {}
