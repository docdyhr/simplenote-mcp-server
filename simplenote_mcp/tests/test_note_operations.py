#!/usr/bin/env python
"""
Test note operations with pytest-style assertions.

This module tests the basic note operations (create, read, update, delete)
using improved pytest assertions with detailed error messages.
"""

import asyncio
import os
import sys
import time
from typing import Dict, Any, List

import pytest

# Add the parent directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(script_dir, "../../"))
sys.path.insert(0, PROJECT_ROOT)

# Now we can import from our compatibility module
from simplenote_mcp.server.compat import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from simplenote_mcp.server import get_logger
from simplenote_mcp.server.errors import ResourceNotFoundError, ValidationError

# Logger for this test module
logger = get_logger("tests.note_operations")


@pytest.mark.asyncio
async def test_note_creation(simplenote_client, test_note_content: str, test_tags: List[str]):
    """Test creating a new note with improved assertions."""
    # Arrange
    note = {"content": test_note_content, "tags": test_tags}
    
    # Act
    created_note, status = simplenote_client.add_note(note)
    
    # Assert
    assert status == 0, f"Failed to create note: API returned status {status}"
    assert created_note is not None, "Created note should not be None"
    assert "key" in created_note, "Created note should have a 'key' property"
    assert created_note.get("content") == test_note_content, "Note content does not match the input"
    
    # Verify tags were saved correctly
    assert "tags" in created_note, "Created note should have a 'tags' property"
    assert isinstance(created_note["tags"], list), "Tags should be a list"
    assert set(test_tags).issubset(set(created_note["tags"])), "Not all tags were saved correctly"
    
    # Clean up - delete the created note
    delete_status = simplenote_client.trash_note(created_note["key"])
    assert delete_status == 0, f"Failed to delete test note: API returned status {delete_status}"


@pytest.mark.asyncio
async def test_note_retrieval(test_note: Dict[str, Any]):
    """Test retrieving a note with improved assertions."""
    # Arrange
    note_id = test_note["key"]
    original_content = test_note["content"]
    simplenote_client = get_simplenote_client()
    
    # Act
    retrieved_note, status = simplenote_client.get_note(note_id)
    
    # Assert
    assert status == 0, f"Failed to retrieve note: API returned status {status}"
    assert retrieved_note is not None, "Retrieved note should not be None"
    assert retrieved_note["key"] == note_id, "Note ID in retrieved note doesn't match expected ID"
    assert retrieved_note["content"] == original_content, "Note content doesn't match original content"
    
    # Verify metadata
    assert "modifydate" in retrieved_note, "Note should have modification date"
    assert "createdate" in retrieved_note, "Note should have creation date"


@pytest.mark.asyncio
async def test_note_update(test_note: Dict[str, Any]):
    """Test updating a note with improved assertions."""
    # Arrange
    simplenote_client = get_simplenote_client()
    note_id = test_note["key"]
    original_tags = test_note.get("tags", [])
    updated_content = test_note["content"] + "\n\nThis content was added during update test."
    updated_tags = original_tags + ["updated"]
    
    # Update the note
    test_note["content"] = updated_content
    test_note["tags"] = updated_tags
    
    # Act
    updated_note, status = simplenote_client.update_note(test_note)
    
    # Assert
    assert status == 0, f"Failed to update note: API returned status {status}"
    assert updated_note is not None, "Updated note should not be None"
    assert updated_note["key"] == note_id, "Note ID changed after update"
    assert updated_note["content"] == updated_content, "Note content wasn't updated correctly"
    
    # Verify tags were updated
    assert "tags" in updated_note, "Updated note should have tags"
    assert "updated" in updated_note["tags"], "New tag 'updated' not found in updated note"
    assert set(original_tags).issubset(set(updated_note["tags"])), "Original tags not preserved"
    
    # Verify note version was incremented
    if "version" in test_note and "version" in updated_note:
        assert updated_note["version"] > test_note["version"], "Note version should have incremented"


@pytest.mark.asyncio
async def test_note_delete(simplenote_client, test_note_content: str, test_tags: List[str]):
    """Test deleting a note with improved assertions."""
    # Arrange - Create a note to delete
    note = {"content": test_note_content, "tags": test_tags}
    created_note, create_status = simplenote_client.add_note(note)
    
    assert create_status == 0, "Failed to create test note for deletion test"
    note_id = created_note["key"]
    
    # Act - Delete the note
    delete_status = simplenote_client.trash_note(note_id)
    
    # Assert
    assert delete_status == 0, f"Failed to delete note: API returned status {delete_status}"
    
    # Verify the note is no longer retrievable or is marked as deleted
    retrieved_note, get_status = simplenote_client.get_note(note_id)
    if get_status == 0:
        # If we can still get the note, it should be marked as deleted/trashed
        assert retrieved_note.get("deleted", False) is True, "Note should be marked as deleted"
    else:
        # Some API implementations might return an error for trashed notes
        assert get_status != 0, "Retrieving deleted note should not succeed"


@pytest.mark.asyncio
async def test_note_cache_operations(note_cache, test_note: Dict[str, Any]):
    """Test note cache operations with improved assertions."""
    # Arrange
    note_id = test_note["key"]
    
    # Act - Get the note from cache
    cached_note = note_cache.get_note(note_id)
    
    # Assert
    assert cached_note is not None, "Note should be retrievable from cache"
    assert cached_note["key"] == note_id, "Note ID in cache doesn't match expected ID"
    assert cached_note["content"] == test_note["content"], "Cache content doesn't match original content"
    
    # Test cache update after note modification
    updated_content = test_note["content"] + "\n\nUpdated through cache test."
    test_note["content"] = updated_content
    simplenote_client = get_simplenote_client()
    updated_note, status = simplenote_client.update_note(test_note)
    
    assert status == 0, "Failed to update note for cache test"
    
    # Sync the cache
    await note_cache.sync()
    
    # Get the note again from cache
    refreshed_note = note_cache.get_note(note_id)
    
    # Verify cache is updated
    assert refreshed_note["content"] == updated_content, "Cache wasn't updated after sync"


@pytest.mark.asyncio
async def test_invalid_note_operations(simplenote_client):
    """Test handling of invalid note operations with improved assertions."""
    # Test retrieving non-existent note
    non_existent_id = "non_existent_note_id"
    retrieved_note, status = simplenote_client.get_note(non_existent_id)
    
    assert status != 0, "Retrieving non-existent note should fail"
    assert retrieved_note is None, "Retrieved note should be None for non-existent note"
    
    # Test with empty content
    with pytest.raises((ValidationError, Exception)) as exc_info:
        empty_note = {"content": "", "tags": ["test"]}
        simplenote_client.add_note(empty_note)
    
    assert exc_info.value is not None, "Creating note with empty content should raise an exception"


@pytest.mark.asyncio
async def test_note_with_special_characters(simplenote_client):
    """Test notes with special characters."""
    # Arrange
    special_content = """
    # Special Character Test
    
    * Unicode: áéíóúñüÁÉÍÓÚÑÜ
    * Symbols: !@#$%^&*()_+-=[]{}|;:'",.<>/?\\
    * Emojis: 😀 🚀 🌟 🎉 👍
    """
    
    note = {"content": special_content, "tags": ["test", "special-chars"]}
    
    # Act
    created_note, status = simplenote_client.add_note(note)
    
    # Assert
    assert status == 0, "Failed to create note with special characters"
    assert created_note["content"] == special_content, "Special character content wasn't preserved"
    
    # Retrieve and verify
    note_id = created_note["key"]
    retrieved_note, get_status = simplenote_client.get_note(note_id)
    
    assert get_status == 0, "Failed to retrieve note with special characters"
    assert retrieved_note["content"] == special_content, "Special characters weren't preserved after retrieval"
    
    # Clean up
    simplenote_client.trash_note(note_id)


@pytest.mark.asyncio
async def test_tag_operations(simplenote_client, test_note: Dict[str, Any]):
    """Test tag operations with improved assertions."""
    # Arrange
    note_id = test_note["key"]
    original_tags = set(test_note.get("tags", []))
    
    # Add tags
    new_tags = list(original_tags) + ["new-tag-1", "new-tag-2"]
    test_note["tags"] = new_tags
    
    # Act - Update with new tags
    updated_note, status = simplenote_client.update_note(test_note)
    
    # Assert
    assert status == 0, "Failed to update note with new tags"
    assert set(new_tags).issubset(set(updated_note.get("tags", []))), "Not all new tags were added"
    
    # Remove tags
    reduced_tags = [tag for tag in new_tags if tag != "new-tag-1"]
    test_note["tags"] = reduced_tags
    
    # Act - Update with removed tag
    updated_note, status = simplenote_client.update_note(test_note)
    
    # Assert
    assert status == 0, "Failed to update note with removed tag"
    assert "new-tag-1" not in updated_note.get("tags", []), "Tag was not removed"
    assert set(reduced_tags).issubset(set(updated_note.get("tags", []))), "Remaining tags were affected"


@pytest.mark.asyncio
async def test_concurrent_note_operations(simplenote_client, test_note_content: str):
    """Test concurrent note operations."""
    # Create multiple notes concurrently
    async def create_note(index: int):
        content = f"{test_note_content}\n\nConcurrent note {index}"
        tags = ["concurrent", f"note-{index}"]
        note = {"content": content, "tags": tags}
        created_note, status = simplenote_client.add_note(note)
        assert status == 0, f"Failed to create concurrent note {index}"
        return created_note
    
    # Create 5 notes concurrently
    tasks = [create_note(i) for i in range(5)]
    notes = await asyncio.gather(*tasks)
    
    # Verify all notes were created
    assert len(notes) == 5, "Not all concurrent notes were created"
    
    # Clean up
    for note in notes:
        status = simplenote_client.trash_note(note["key"])
        assert status == 0, f"Failed to delete concurrent note {note['key']}"


# Run the tests if called directly
if __name__ == "__main__":
    # Use pytest to run the tests
    import pytest
    sys.exit(pytest.main(["-xvs", __file__]))