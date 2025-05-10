import asyncio
import os
import sys
import uuid
from datetime import datetime

import pytest
import pytest_asyncio

# Attempt to import from the project's installed package first.
# This assumes `pip install -e .` has been run as per CLAUDE.md.
try:
    from simplenote_mcp.server import get_simplenote_client
except ImportError:
    # Fallback for environments where the package might not be installed editable.
    # Adjusting path for pytest discovery when run from project root.
    # simplenote-mcp-server/ (PROJECT_ROOT)
    #  |- simplenote_mcp/
    #     |- tests/
    #        |- test_mcp_client.py (this file)
    # Assuming pytest is run from `simplenote-mcp-server` directory
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    )
    from simplenote_mcp.server import get_simplenote_client


# Marker to skip tests if Simplenote credentials are not available
skip_if_no_creds = pytest.mark.skipif(
    not os.environ.get("SIMPLENOTE_EMAIL") or not os.environ.get("SIMPLENOTE_PASSWORD"),
    reason="SIMPLENOTE_EMAIL and SIMPLENOTE_PASSWORD environment variables are not set.",
)

TEST_TAG = "pytest_mcp_client_test"


@pytest_asyncio.fixture(scope="session")
async def simplenote_client_session():
    """Provides an authenticated Simplenote client instance for the test session."""
    if not os.environ.get("SIMPLENOTE_EMAIL") or not os.environ.get(
        "SIMPLENOTE_PASSWORD"
    ):
        pytest.skip("Skipping tests that require Simplenote credentials.")

    # get_simplenote_client() is synchronous
    client = await asyncio.to_thread(get_simplenote_client)

    # Test connection once for the session by listing notes
    try:
        notes, status = await asyncio.to_thread(client.get_note_list)
        if status != 0:  # simplenote.py uses 0 for success, non-zero for some errors
            # Try to get more error info if available from client object if status indicates error
            error_info = getattr(
                client, "last_error", f"Simplenote API status: {status}"
            )
            pytest.fail(
                f"Failed to connect to Simplenote for initial client setup. Error: {error_info}"
            )
        print(
            f"\nSuccessfully connected to Simplenote for test session. Found {len(notes)} notes."
        )
    except Exception as e:
        pytest.fail(f"Exception during Simplenote client setup: {e}")
    return client


@pytest_asyncio.fixture
async def test_note(simplenote_client_session):
    """
    Creates a unique note for a test and ensures it's cleaned up afterwards.
    Yields the created note object.
    """
    client = simplenote_client_session
    note_content = f"Test note created by pytest_mcp_client_test at {datetime.now()} - {uuid.uuid4()}"
    note_to_create = {"content": note_content, "tags": [TEST_TAG, "temp_test_note"]}

    created_note_data = None
    try:
        # simplenote.py functions are synchronous, run in a thread
        created_note_data, status = await asyncio.to_thread(
            client.add_note, note_to_create
        )
        assert status == 0, (
            f"Failed to create note (status: {status}, error: {getattr(client, 'last_error', 'N/A')})"
        )
        assert "key" in created_note_data, "Created note data does not contain a key."

        # Fetch the note again to get all properties, including 'version'
        fetched_note, fetch_status = await asyncio.to_thread(
            client.get_note, created_note_data["key"]
        )
        assert fetch_status == 0, (
            f"Failed to fetch newly created note (status: {fetch_status})"
        )
        assert fetched_note is not None, "Fetched note is None after creation."
        yield fetched_note  # yield the more complete note object
    finally:
        if created_note_data and "key" in created_note_data:
            note_key = created_note_data["key"]
            print(f"\nCleaning up test note: {note_key}")
            try:
                # Attempt to trash the note first (soft delete)
                # simplenote.py's trash_note(note_id) takes only one argument (note_id)
                _, status_trash = await asyncio.to_thread(client.trash_note, note_key)
                # print(f"Trash status for note {note_key}: {status_trash}")

                # Then, permanently delete the note
                _, status_delete = await asyncio.to_thread(client.delete_note, note_key)
                # print(f"Permanent delete status for note {note_key}: {status_delete}")
            except Exception as e:
                # Log error during cleanup but don't fail the test if the test itself passed
                print(
                    f"WARNING: Error during test note cleanup for {note_key}: {e}. Manual cleanup might be needed for tag '{TEST_TAG}'."
                )


@skip_if_no_creds
@pytest.mark.asyncio
async def test_simplenote_connection_and_list(simplenote_client_session):
    """Tests basic connection and listing of notes."""
    client = simplenote_client_session
    notes, status = await asyncio.to_thread(client.get_note_list)
    assert status == 0, (
        f"Failed to get note list (status: {status}, error: {getattr(client, 'last_error', 'N/A')})"
    )
    assert isinstance(notes, list), "Note list should be a list."
    print(f"Note list retrieval successful. Found {len(notes)} notes.")
    if notes:
        # Make sure note objects have expected keys (content, key)
        assert "content" in notes[0]
        assert "key" in notes[0]
        print(f"First note content snippet: {str(notes[0].get('content', ''))[:50]}...")


@skip_if_no_creds
@pytest.mark.asyncio
async def test_create_and_read_note(simplenote_client_session, test_note):
    """Tests creating a note and then reading it. Relies on test_note fixture for creation and cleanup."""
    client = simplenote_client_session
    created_note_key = test_note["key"]
    original_content = test_note["content"]  # Content from the fixture's created note

    # Read the note back (test_note already did one fetch, this is to re-verify)
    retrieved_note, status = await asyncio.to_thread(client.get_note, created_note_key)
    assert status == 0, (
        f"Failed to retrieve note {created_note_key} (status: {status}, error: {getattr(client, 'last_error', 'N/A')})"
    )
    assert retrieved_note is not None, "Retrieved note should not be None."
    assert retrieved_note["key"] == created_note_key
    assert retrieved_note["content"] == original_content
    assert TEST_TAG in retrieved_note.get("tags", []), (
        f"Test tag '{TEST_TAG}' not found in retrieved note."
    )
    print(f"Successfully created and read note: {created_note_key}")


@skip_if_no_creds
@pytest.mark.asyncio
async def test_update_note(simplenote_client_session, test_note):
    """Tests updating an existing note."""
    client = simplenote_client_session
    note_key = test_note["key"]
    initial_version = test_note.get("version")
    assert initial_version is not None, "Note version is missing, required for update."

    updated_content = f"Updated content at {datetime.now()} - {uuid.uuid4()}"
    updated_tags = [TEST_TAG, "updated_tag_pytest"]

    note_to_update = {
        "key": note_key,
        "content": updated_content,
        "tags": updated_tags,
        "version": initial_version,
    }

    updated_note_data, status = await asyncio.to_thread(
        client.add_note, note_to_update
    )  # add_note for updates
    assert status == 0, (
        f"Failed to update note {note_key} (status: {status}, error: {getattr(client, 'last_error', 'N/A')})"
    )
    assert updated_note_data["key"] == note_key
    assert updated_note_data["content"] == updated_content
    # Tags are usually replaced or set as provided by simplenote.py's add_note for updates
    assert sorted(updated_note_data.get("tags", [])) == sorted(updated_tags)
    assert updated_note_data.get("version") != initial_version, (
        "Note version should change after update."
    )

    # Verify by fetching again
    refetched_note, status_fetch = await asyncio.to_thread(client.get_note, note_key)
    assert status_fetch == 0, (
        f"Failed to fetch note after update (status: {status_fetch})"
    )
    assert refetched_note["content"] == updated_content
    assert sorted(refetched_note.get("tags", [])) == sorted(updated_tags)
    print(f"Successfully updated note: {note_key}")


@skip_if_no_creds
@pytest.mark.asyncio
async def test_trash_and_verify_note(simplenote_client_session, test_note):
    """
    Tests trashing a note (soft delete).
    The `test_note` fixture will handle permanent deletion afterwards.
    """
    client = simplenote_client_session
    note_key = test_note["key"]

    # Trash the note
    # simplenote.py's trash_note(note_id) takes only one argument (note_id)
    _, status = await asyncio.to_thread(client.trash_note, note_key)
    assert status == 0, (
        f"Failed to trash note {note_key} (status: {status}, error: {getattr(client, 'last_error', 'N/A')})"
    )

    # Verify it's marked as deleted (trashed)
    # simplenote.py's get_note might return trashed notes with a 'deleted': True flag.
    fetched_note_after_trash, fetch_status = await asyncio.to_thread(
        client.get_note, note_key
    )

    assert fetch_status == 0, (
        "Fetching a trashed note should still succeed (to see its 'deleted' status)."
    )
    assert fetched_note_after_trash is not None, (
        "Trashed note data should not be None when fetched directly."
    )
    assert fetched_note_after_trash.get("deleted") == True, (
        "Note was not marked as 'deleted: True' after trashing."
    )

    # Additionally, ensure it doesn't appear in the main list of active notes.
    # This might take a moment for Simplenote's index to update.
    await asyncio.sleep(2)  # Short delay for consistency
    notes, list_status = await asyncio.to_thread(
        client.get_note_list
    )  # Gets active notes
    assert list_status == 0

    found_in_active_list = any(
        n["key"] == note_key and not n.get("deleted") for n in notes
    )
    assert not found_in_active_list, (
        "Trashed note still appears as active in the main note list."
    )
    print(f"Successfully trashed note and verified: {note_key}")


@skip_if_no_creds
@pytest.mark.asyncio
async def test_search_notes(simplenote_client_session, test_note):
    """
    Tests if a created note's unique content can be found by fetching notes
    (potentially filtered by a common test tag) and then manually checking content.
    This adapts to Simplenote clients that may not have a direct search API method.
    """
    client = simplenote_client_session
    note_key_to_find = test_note["key"]
    unique_content_part = test_note["content"].split(" - ")[-1]

    # Allow some time for note propagation/indexing if necessary, though direct fetch is usually immediate.
    await asyncio.sleep(1)

    # Attempt to fetch notes, possibly filtered by the TEST_TAG if the client supports it.
    # If client.get_note_list doesn't support `tags`, this will need adjustment (e.g. TypeError).
    # For now, assume it might, or it ignores unknown kwargs gracefully.
    # A more robust solution would be to check client capabilities or try/except.
    # Based on dir() output, get_note_list likely takes no/few args. We'll fetch all.

    all_notes, status = await asyncio.to_thread(client.get_note_list)
    assert status == 0, (
        f"Failed to get note list for manual search (status: {status}, error: {getattr(client, 'last_error', 'N/A')})"
    )

    found_note_manually = False
    for note_data in all_notes:
        if note_data.get("key") == note_key_to_find:
            if unique_content_part in note_data.get("content", ""):
                found_note_manually = True
                break
            else:
                # This case should ideally not happen if test_note fixture worked correctly
                pytest.fail(
                    f"Found note by key {note_key_to_find}, but unique content '{unique_content_part}' not in its content: '{note_data.get('content', '')}'"
                )

    assert found_note_manually, (
        f"Created test note (key: {note_key_to_find}, unique_content: '{unique_content_part}') not found by manual content check in fetched notes."
    )
    print(
        f"Successfully found note {note_key_to_find} by manually checking content in note list."
    )


# To run these tests from the project root (`simplenote-mcp-server`):
# 1. Ensure SIMPLENOTE_EMAIL and SIMPLENOTE_PASSWORD are set as environment variables.
# 2. Install pytest and pytest-asyncio: `pip install pytest pytest-asyncio` (if not already in dev dependencies)
# 3. Run: `pytest simplenote_mcp/tests/test_mcp_client.py` or `pytest`
