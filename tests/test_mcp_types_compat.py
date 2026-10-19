"""Tests for MCP types compatibility module."""

from typing import get_args

import pytest
from mcp import types as mcp_types

from simplenote_mcp.server import mcp_types_compat as compat
from simplenote_mcp.server.mcp_types_compat import (
    AddTagsToNoteRequest,
    AddTagsToNoteResponse,
    Context,
    DeleteNoteRequest,
    DeleteNoteResponse,
    ErrorContent,
    GetNoteRequest,
    GetNoteResponse,
    GetPromptRequest,
    GetPromptResponse,
    ListPromptsRequest,
    ListPromptsResponse,
    ListResourcesRequest,
    ListResourcesResponse,
    ReadResourceRequest,
    ReadResourceResponse,
    RemoveTagsFromNoteRequest,
    RemoveTagsFromNoteResponse,
    ReplaceTagsOnNoteRequest,
    ReplaceTagsOnNoteResponse,
    ToolRequestContent,
    UpdateNoteRequest,
    UpdateNoteResponse,
)

TAG_REQUESTS = [
    AddTagsToNoteRequest,
    RemoveTagsFromNoteRequest,
    ReplaceTagsOnNoteRequest,
]
TAG_RESPONSES = [
    AddTagsToNoteResponse,
    RemoveTagsFromNoteResponse,
    ReplaceTagsOnNoteResponse,
]
# (class, attribute) pairs whose list defaults are built with `value or []`.
LIST_DEFAULTS = [
    (ListResourcesResponse, "resources"),
    (ReadResourceResponse, "contents"),
    (GetPromptResponse, "messages"),
    (ListPromptsResponse, "prompts"),
    *[(cls, "tags") for cls in TAG_RESPONSES],
]


class TestContext:
    """Test the Context class."""

    def test_context_creation_default(self):
        """Test creating Context with default values."""
        context = Context()
        assert context.request_id is None

    def test_context_creation_with_id(self):
        """Test creating Context with request ID."""
        context = Context(request_id="test-123")
        assert context.request_id == "test-123"


class TestListResourcesRequest:
    """Test the ListResourcesRequest class."""

    def test_default_creation(self):
        """Test creating ListResourcesRequest with defaults."""
        request = ListResourcesRequest()

        assert request.tag is None
        assert request.limit is None
        assert request.offset == 0
        assert request.sort_by is None
        assert request.sort_direction is None

    def test_creation_with_parameters(self):
        """Test creating ListResourcesRequest with parameters."""
        request = ListResourcesRequest(
            tag="work", limit=50, offset=10, sort_by="modified", sort_direction="desc"
        )

        assert request.tag == "work"
        assert request.limit == 50
        assert request.offset == 10
        assert request.sort_by == "modified"
        assert request.sort_direction == "desc"


class TestReadResourceRequest:
    """Test the ReadResourceRequest class."""

    def test_default_creation(self):
        """Test creating ReadResourceRequest with defaults."""
        request = ReadResourceRequest()
        assert request.uri is None

    def test_creation_with_uri(self):
        """Test creating ReadResourceRequest with URI."""
        request = ReadResourceRequest(uri="simplenote://note/123")
        assert request.uri == "simplenote://note/123"


class TestGetNoteRequest:
    """Test the GetNoteRequest class."""

    def test_default_creation(self):
        """Test creating GetNoteRequest with defaults."""
        request = GetNoteRequest()
        assert request.note_id is None

    def test_creation_with_note_id(self):
        """Test creating GetNoteRequest with note ID."""
        request = GetNoteRequest(note_id="note-123")
        assert request.note_id == "note-123"


class TestNoteRequests:
    """Update/delete request shims."""

    def test_update_note_request_defaults(self):
        request = UpdateNoteRequest()

        assert vars(request) == {
            "note_id": None,
            "content": None,
            "tags": None,
            "version": None,
            "markdown": None,
            "pinned": None,
        }

    def test_update_note_request_keeps_falsy_values(self):
        request = UpdateNoteRequest(
            note_id="n1", content="", tags=[], version=0, markdown=False, pinned=False
        )

        assert request.content == ""
        assert request.tags == []
        assert request.version == 0
        assert request.markdown is False
        assert request.pinned is False

    def test_delete_note_request(self):
        assert vars(DeleteNoteRequest()) == {"note_id": None, "force": False}
        assert vars(DeleteNoteRequest(note_id="n1", force=True)) == {
            "note_id": "n1",
            "force": True,
        }


class TestTagRequests:
    """Tag request shims keep ``tags`` as given (``None`` by default)."""

    @pytest.mark.parametrize("cls", TAG_REQUESTS)
    def test_defaults(self, cls):
        assert vars(cls()) == {"note_id": None, "tags": None}

    @pytest.mark.parametrize("cls", TAG_REQUESTS)
    def test_tags_list_is_kept_by_identity(self, cls):
        tags = ["work", "urgent"]

        request = cls(note_id="n1", tags=tags)

        assert request.note_id == "n1"
        assert request.tags is tags


class TestPromptRequests:
    def test_list_prompts_request_has_no_state(self):
        assert vars(ListPromptsRequest()) == {}

    def test_get_prompt_request_defaults_to_fresh_argument_dict(self):
        first = GetPromptRequest(name="summarize")
        second = GetPromptRequest()

        first.arguments["note_id"] = "n1"

        assert first.name == "summarize"
        assert second.name is None
        assert second.arguments == {}

    def test_get_prompt_request_keeps_given_arguments(self):
        arguments = {"note_id": "n1"}

        assert GetPromptRequest("p", arguments).arguments is arguments


class TestResponses:
    def test_get_note_response(self):
        note = {"key": "n1"}

        assert GetNoteResponse().note is None
        assert GetNoteResponse(note).note is note

    def test_update_note_response(self):
        response = UpdateNoteResponse(note={"key": "n1"}, status="updated")

        assert vars(UpdateNoteResponse()) == {"note": None, "status": None}
        assert response.note == {"key": "n1"}
        assert response.status == "updated"

    def test_delete_note_response(self):
        assert vars(DeleteNoteResponse()) == {"status": None, "note_id": None}
        assert vars(DeleteNoteResponse("trashed", "n1")) == {
            "status": "trashed",
            "note_id": "n1",
        }

    @pytest.mark.parametrize("cls", TAG_RESPONSES)
    def test_tag_response_defaults(self, cls):
        assert vars(cls()) == {
            "success": False,
            "id": None,
            "status": None,
            "tags": [],
        }

    @pytest.mark.parametrize("cls", TAG_RESPONSES)
    def test_tag_response_values(self, cls):
        response = cls(success=True, id="n1", status="ok", tags=["a"])

        assert vars(response) == {
            "success": True,
            "id": "n1",
            "status": "ok",
            "tags": ["a"],
        }

    @pytest.mark.parametrize(("cls", "attr"), LIST_DEFAULTS)
    def test_list_defaults_are_not_shared(self, cls, attr):
        first, second = cls(), cls()

        getattr(first, attr).append("x")

        assert getattr(second, attr) == []

    @pytest.mark.parametrize(("cls", "attr"), LIST_DEFAULTS)
    def test_non_empty_list_is_kept_by_identity(self, cls, attr):
        items = ["x"]

        assert getattr(cls(**{attr: items}), attr) is items


class TestCustomContent:
    def test_error_content(self):
        assert vars(ErrorContent()) == {
            "type": "error",
            "message": None,
            "category": None,
        }
        content = ErrorContent(message="Note not found", category="not_found")
        assert content.type == "error"
        assert content.message == "Note not found"
        assert content.category == "not_found"

    def test_tool_request_content(self):
        default = ToolRequestContent()
        other = ToolRequestContent(tool_name="search_notes", tool_arguments={"q": 1})

        default.tool_arguments["x"] = 1

        assert default.type == "tool_request"
        assert default.tool_name is None
        assert ToolRequestContent().tool_arguments == {}
        assert other.tool_name == "search_notes"
        assert other.tool_arguments == {"q": 1}


class TestMcpTypeAliases:
    """Aliases must resolve to the installed MCP SDK's own classes."""

    @pytest.mark.parametrize(
        "name",
        [
            "TextContent",
            "TextResourceContents",
            "Resource",
            "Prompt",
            "PromptArgument",
            "PromptMessage",
        ],
    )
    def test_alias_is_sdk_class(self, name):
        assert getattr(compat, name) is getattr(mcp_types, name)

    def test_content_union_members(self):
        assert set(get_args(compat.Content)) == {
            mcp_types.TextContent,
            mcp_types.ImageContent,
            mcp_types.BlobResourceContents,
            mcp_types.TextResourceContents,
        }

    def test_content_union_supports_isinstance(self):
        text = compat.TextContent(type="text", text="hello")

        assert isinstance(text, compat.Content)
        assert not isinstance("hello", compat.Content)
