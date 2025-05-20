#!/usr/bin/env python
"""
Tests for server capabilities with pytest-style assertions.

This module tests the server capabilities such as resource listing,
resource reading, and tool calls using improved pytest-style assertions.
"""

import asyncio
import json
import os
import sys
import time

import mcp.types as types
import pytest

from simplenote_mcp.server.cache import initialize_cache
from simplenote_mcp.server.compat import Path
from simplenote_mcp.server.errors import ResourceNotFoundError, ValidationError
from simplenote_mcp.server.logging import logger as mcp_logger
from simplenote_mcp.tests.test_helpers import handle_call_tool, handle_read_resource

# Add the parent directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(script_dir, "../../"))

# Skip all tests in this file for now as we would need to refactor it
pytestmark = pytest.mark.skip(
    reason="Tests need to be refactored to use server instance directly instead of internal functions"
)
sys.path.insert(0, PROJECT_ROOT)

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Logger for this test module
logger = mcp_logger.getChild("tests.server_capabilities")


@pytest.fixture(scope="module", autouse=True)
async def setup_server_cache():
    """Initialize server cache for tests."""
    await initialize_cache()
    yield


@pytest.mark.asyncio
async def test_list_resources():
    """Test listing resources with different filters and limits."""
    # Test without filters
    resources = await handle_list_resources()

    # Assertions
    assert resources is not None, "Resources should not be None"
    assert isinstance(resources, list), "Resources should be a list"
    assert len(resources) > 0, "At least one resource should be returned"

    # Verify resource structure
    first_resource = resources[0]
    assert isinstance(first_resource, types.Resource), "Each item should be a Resource"
    assert first_resource.name is not None, "Resource should have a name"
    assert first_resource.uri is not None, "Resource should have a URI"
    assert str(first_resource.uri).startswith("simplenote://note/"), (
        "URI should have expected format"
    )

    # Test with limit
    limited_resources = await handle_list_resources(limit=3)
    assert len(limited_resources) <= 3, (
        f"Should return at most 3 resources, got {len(limited_resources)}"
    )

    # Try with a tag filter if resources have tags
    for resource in resources[:10]:  # Check the first few resources
        if resource.meta and "tags" in resource.meta and resource.meta["tags"]:
            tag = resource.meta["tags"][0]
            tagged_resources = await handle_list_resources(tag=tag)

            # Verify tag filtering
            assert all(tag in r.meta.get("tags", []) for r in tagged_resources), (
                f"All resources should have the '{tag}' tag"
            )
            break


@pytest.mark.asyncio
async def test_read_resource():
    """Test reading resources by URI."""
    # First get some resources
    resources = await handle_list_resources(limit=5)
    assert resources, "Need at least one resource for testing"

    # Read the first resource
    resource = resources[0]
    uri = resource.uri

    # Test reading the resource
    content = await handle_read_resource(uri)

    # Assertions
    assert content is not None, "Content should not be None"
    assert isinstance(content, types.ReadResourceResult), (
        "Content should be a ReadResourceResult"
    )
    assert (
        hasattr(content, "contents")
        and content.contents is not None
        and len(content.contents) > 0
    ), "Content should not be empty"

    # Verify content items
    text_content = next(
        (item for item in content.contents if hasattr(item, "text")), None
    )
    assert text_content is not None, "Should have text content item"
    assert isinstance(text_content.text, str), "Text content should be a string"
    assert len(text_content.text) > 0, "Text content should not be empty"

    # Test with non-existent URI
    invalid_uri = "simplenote://note/nonexistent"
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await handle_read_resource(invalid_uri)

    # Check for various "not found" phrases in the error message
    error_msg = str(exc_info.value).lower()
    assert any(phrase in error_msg for phrase in ["not found", "not_found"]), (
        "Error should indicate resource not found"
    )

    # Test with malformed URI
    malformed_uri = "invalid://format"
    with pytest.raises(ValidationError) as exc_info:
        await handle_read_resource(malformed_uri)

    assert "invalid" in str(exc_info.value).lower(), (
        "Error should indicate invalid URI format"
    )


@pytest.mark.asyncio
async def test_list_tools():
    """Test listing available tools."""
    # Get tools
    tools = await handle_list_tools()

    # Assertions
    assert tools is not None, "Tools should not be None"
    assert isinstance(tools, list), "Tools should be a list"
    assert len(tools) > 0, "At least one tool should be available"

    # Verify expected tools
    expected_tools = {
        "create_note",
        "update_note",
        "delete_note",
        "get_note",
        "search_notes",
        "add_tags",
        "remove_tags",
        "replace_tags",
    }

    tool_names = {tool.name for tool in tools}
    for expected_tool in expected_tools:
        assert expected_tool in tool_names, f"Expected tool '{expected_tool}' not found"

    # Verify tool structure
    for tool in tools:
        assert isinstance(tool, types.Tool), "Each item should be a Tool"
        assert tool.name, "Tool should have a name"
        assert tool.description, "Tool should have a description"
        assert tool.inputSchema, "Tool should have an input schema"
        assert isinstance(tool.inputSchema, dict), "Input schema should be a dictionary"


@pytest.mark.asyncio
async def test_create_note_tool():
    """Test the create_note tool."""
    # Generate unique content to avoid duplicates
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    test_content = f"Test note created by pytest at {timestamp}\nThis is a test."

    # Call the tool
    arguments = {"content": test_content, "tags": ["pytest", "test"]}

    result = await handle_call_tool("create_note", arguments)

    # Assertions
    assert result is not None, "Result should not be None"
    assert isinstance(result, list), "Result should be a list"
    assert len(result) > 0, "Result should have at least one item"

    # Verify result contains the note ID
    text_result = next((item for item in result if item.type == "text"), None)
    assert text_result is not None, "Should have text result"
    assert "key" in text_result.text, "Result should contain note key"

    # Extract note ID for cleanup
    import json

    note_data = json.loads(text_result.text)
    assert "key" in note_data, "JSON result should contain note key"
    note_id = note_data["key"]

    # Clean up - delete the created note
    delete_args = {"note_id": note_id}
    await handle_call_tool("delete_note", delete_args)


@pytest.mark.asyncio
async def test_search_notes_tool():
    """Test the search_notes tool."""
    # Create a note with specific content for searching
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    unique_text = f"uniquesearchterm{timestamp}"
    test_content = f"Test note for search testing. {unique_text}"

    # Call create_note tool
    create_args = {"content": test_content, "tags": ["pytest", "search-test"]}

    create_result = await handle_call_tool("create_note", create_args)
    text_result = next((item for item in create_result if item.type == "text"), None)
    note_data = json.loads(text_result.text)
    note_id = note_data["key"]

    try:
        # Wait briefly for indexing
        await asyncio.sleep(1)

        # Search for the unique text
        search_args = {"query": unique_text}
        search_result = await handle_call_tool("search_notes", search_args)

        # Assertions
        assert search_result is not None, "Search result should not be None"
        assert isinstance(search_result, list), "Search result should be a list"
        assert len(search_result) > 0, "Search result should have at least one item"

        # Verify search results contain our note
        text_result = next(
            (item for item in search_result if item.type == "text"), None
        )
        assert text_result is not None, "Should have text result"
        result_text = text_result.text
        assert unique_text in result_text, (
            "Search result should contain the unique text"
        )
        assert note_id in result_text, "Search result should contain the note ID"

    finally:
        # Clean up - delete the test note
        delete_args = {"note_id": note_id}
        await handle_call_tool("delete_note", delete_args)


@pytest.mark.asyncio
async def test_tag_management_tools():
    """Test tag management tools (add_tags, remove_tags, replace_tags)."""
    # Create a note for testing
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    test_content = f"Test note for tag testing at {timestamp}"

    # Call create_note tool with initial tags
    create_args = {"content": test_content, "tags": ["pytest", "initial"]}

    create_result = await handle_call_tool("create_note", create_args)
    text_result = next((item for item in create_result if item.type == "text"), None)
    note_data = json.loads(text_result.text)
    note_id = note_data["key"]

    try:
        # Test add_tags
        add_tags_args = {"note_id": note_id, "tags": "added1,added2"}

        add_result = await handle_call_tool("add_tags", add_tags_args)
        text_result = next((item for item in add_result if item.type == "text"), None)
        add_data = json.loads(text_result.text)

        assert "tags" in add_data, "Result should include tags"
        assert "added1" in add_data["tags"], "Tag 'added1' should be added"
        assert "added2" in add_data["tags"], "Tag 'added2' should be added"
        assert "initial" in add_data["tags"], (
            "Original tag 'initial' should be preserved"
        )

        # Test remove_tags
        remove_tags_args = {"note_id": note_id, "tags": "initial,added1"}

        remove_result = await handle_call_tool("remove_tags", remove_tags_args)
        text_result = next(
            (item for item in remove_result if item.type == "text"), None
        )
        remove_data = json.loads(text_result.text)

        assert "tags" in remove_data, "Result should include tags"
        assert "initial" not in remove_data["tags"], "Tag 'initial' should be removed"
        assert "added1" not in remove_data["tags"], "Tag 'added1' should be removed"
        assert "added2" in remove_data["tags"], "Tag 'added2' should be preserved"

        # Test replace_tags
        replace_tags_args = {
            "note_id": note_id,
            "tags": "replaced1,replaced2,replaced3",
        }

        replace_result = await handle_call_tool("replace_tags", replace_tags_args)
        text_result = next(
            (item for item in replace_result if item.type == "text"), None
        )
        replace_data = json.loads(text_result.text)

        assert "tags" in replace_data, "Result should include tags"
        expected_tags = {"replaced1", "replaced2", "replaced3"}
        actual_tags = set(replace_data["tags"])
        assert actual_tags == expected_tags, (
            f"Tags should be exactly {expected_tags}, got {actual_tags}"
        )

    finally:
        # Clean up - delete the test note
        delete_args = {"note_id": note_id}
        await handle_call_tool("delete_note", delete_args)


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in server capabilities."""
    # Test invalid tool name - the server returns an error response but doesn't raise
    result = await handle_call_tool("nonexistent_tool", {})

    # Check for error in the response
    assert any("error" in str(getattr(item, "text", "")) for item in result), (
        "Error should be in response"
    )
    assert any("Unknown tool" in str(getattr(item, "text", "")) for item in result), (
        "Should indicate unknown tool"
    )

    # Test missing required arguments
    result = await handle_call_tool("get_note", {})

    # Check for error message about required fields
    assert any(
        "required" in str(getattr(item, "text", "")).lower() for item in result
    ), "Should indicate missing required argument"

    # Test invalid resource URI
    try:
        await handle_read_resource("invalid://uri")
        raise AssertionError("Should have raised an exception")
    except ValidationError as exc:
        assert "invalid" in str(exc).lower(), "Should indicate invalid URI"


# Run the tests if called directly
if __name__ == "__main__":
    # Use pytest to run the tests
    import pytest

    sys.exit(pytest.main(["-xvs", __file__]))
