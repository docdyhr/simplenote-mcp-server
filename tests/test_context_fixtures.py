"""Tests for context fixtures."""

from simplenote_mcp.server.config import Config
from simplenote_mcp.server.context import ServerContext


class TestContextFixtures:
    """Test the context fixtures defined in conftest.py."""

    def test_server_context_fixture(self, server_context):
        """Test that server_context fixture provides a basic context."""
        assert isinstance(server_context, ServerContext)
        assert isinstance(server_context.config, Config)
        assert server_context.simplenote_client is None
        assert server_context.note_cache is None
        assert not server_context.is_authenticated()
        assert not server_context.has_cache()

    def test_authenticated_context_fixture(self, authenticated_context):
        """Test that authenticated_context fixture provides a fully configured context."""
        assert isinstance(authenticated_context, ServerContext)
        assert isinstance(authenticated_context.config, Config)
        assert authenticated_context.simplenote_client is not None
        assert authenticated_context.note_cache is not None
        assert authenticated_context.is_authenticated()
        assert authenticated_context.has_cache()

    def test_fixtures_independence(self, server_context, authenticated_context):
        """Test that fixtures provide independent context instances."""
        assert server_context is not authenticated_context
        assert server_context.config is not authenticated_context.config

        # Verify they have different states
        assert not server_context.is_authenticated()
        assert authenticated_context.is_authenticated()

    def test_mock_simplenote_client_fixture(self, mock_simplenote_client):
        """Test that mock_simplenote_client fixture works correctly."""
        # Test get_note_list
        notes, status = mock_simplenote_client.get_note_list()
        assert status == 0
        assert len(notes) == 2
        assert notes[0]["key"] == "note1"

        # Test get_note
        note, status = mock_simplenote_client.get_note("note1")
        assert status == 0
        assert note["key"] == "note1"

        # Test add_note
        new_note, status = mock_simplenote_client.add_note("New content")
        assert status == 0
        assert new_note["key"] == "new_note"

        # Test update_note
        updated_note, status = mock_simplenote_client.update_note("note1", "Updated")
        assert status == 0
        assert updated_note["content"] == "Updated test note"

        # Test trash_note
        status = mock_simplenote_client.trash_note("note1")
        assert status == 0
