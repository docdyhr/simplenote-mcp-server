"""Tests for server context management."""

import pytest

from simplenote_mcp.server.cache import NoteCache
from simplenote_mcp.server.config import Config
from simplenote_mcp.server.context import ContextManager, ServerContext


class TestServerContext:
    """Test the ServerContext class."""

    def test_server_context_creation(self):
        """Test creating a ServerContext with valid config."""
        config = Config()
        context = ServerContext(config=config)

        assert context.config is config
        assert context.simplenote_client is None
        assert context.note_cache is None

    def test_server_context_invalid_config(self):
        """Test ServerContext raises error with invalid config."""
        with pytest.raises(TypeError, match="config must be an instance of Config"):
            ServerContext(config="invalid")  # type: ignore

    def test_is_authenticated_false(self):
        """Test is_authenticated returns False when no client."""
        config = Config()
        context = ServerContext(config=config)

        assert not context.is_authenticated()

    def test_is_authenticated_true(self, mock_simplenote_client):
        """Test is_authenticated returns True when client exists."""
        config = Config()
        context = ServerContext(config=config, simplenote_client=mock_simplenote_client)

        assert context.is_authenticated()

    def test_has_cache_false(self):
        """Test has_cache returns False when no cache."""
        config = Config()
        context = ServerContext(config=config)

        assert not context.has_cache()

    def test_has_cache_true(self, mock_simplenote_client):
        """Test has_cache returns True when cache exists."""
        config = Config()
        note_cache = NoteCache(mock_simplenote_client)
        context = ServerContext(config=config, note_cache=note_cache)

        assert context.has_cache()

    def test_server_context_str_representation(self):
        """Test string representation includes class name."""
        config = Config()
        context = ServerContext(config=config)

        str_repr = str(context)
        assert "ServerContext" in str_repr

    def test_server_context_with_none_config(self):
        """Test ServerContext raises error with None config."""
        with pytest.raises(TypeError, match="config must be an instance of Config"):
            ServerContext(config=None)  # type: ignore

    def test_server_context_state_consistency(self, mock_simplenote_client):
        """Test that context state remains consistent after modifications."""
        config = Config()
        context = ServerContext(config=config)

        # Initial state
        assert not context.is_authenticated()
        assert not context.has_cache()

        # Add client directly (simulating authentication)
        context.simplenote_client = mock_simplenote_client
        assert context.is_authenticated()
        assert not context.has_cache()  # Still no cache

        # Add cache
        context.note_cache = NoteCache(mock_simplenote_client)
        assert context.is_authenticated()
        assert context.has_cache()

        # Remove client
        context.simplenote_client = None
        assert not context.is_authenticated()
        assert context.has_cache()  # Cache still exists

    def test_server_context_with_cache_no_client(self, mock_simplenote_client):
        """Test ServerContext handles cache without client gracefully."""
        config = Config()
        note_cache = NoteCache(mock_simplenote_client)
        context = ServerContext(config=config, note_cache=note_cache)

        assert context.has_cache()
        assert not context.is_authenticated()  # No client set


class TestContextManager:
    """Test the ContextManager class."""

    def test_create_context_with_defaults(self):
        """Test creating context with default config."""
        context = ContextManager.create_context()

        assert isinstance(context.config, Config)
        assert context.simplenote_client is None
        assert context.note_cache is None

    def test_create_context_with_config(self):
        """Test creating context with provided config."""
        config = Config()
        context = ContextManager.create_context(config=config)

        assert context.config is config
        assert context.simplenote_client is None
        assert context.note_cache is None

    def test_create_context_with_all_params(self, mock_simplenote_client):
        """Test creating context with all parameters."""
        config = Config()
        note_cache = NoteCache(mock_simplenote_client)

        context = ContextManager.create_context(
            config=config,
            simplenote_client=mock_simplenote_client,
            note_cache=note_cache,
        )

        assert context.config is config
        assert context.simplenote_client is mock_simplenote_client
        assert context.note_cache is note_cache
        assert context.is_authenticated()
        assert context.has_cache()

    def test_create_context_with_none_config(self):
        """Test creating context with None config creates default."""
        context = ContextManager.create_context(config=None)

        assert isinstance(context.config, Config)
        assert context.simplenote_client is None
        assert context.note_cache is None

    def test_create_context_invalid_config_handled(self):
        """Test ContextManager handles invalid config gracefully."""
        # Since ContextManager.create_context accepts None and creates Config(),
        # invalid configs would be caught by ServerContext.__post_init__
        with pytest.raises(TypeError, match="config must be an instance of Config"):
            # This will fail in ServerContext.__post_init__
            ContextManager.create_context(config="invalid")  # type: ignore


class TestContextIntegration:
    """Integration tests for context management."""

    def test_full_context_lifecycle(self, mock_simplenote_client):
        """Test complete context lifecycle from creation to full setup."""
        # Start with empty context
        context = ContextManager.create_context()
        assert not context.is_authenticated()
        assert not context.has_cache()

        # Add authentication
        context.simplenote_client = mock_simplenote_client
        assert context.is_authenticated()
        assert not context.has_cache()

        # Add cache
        context.note_cache = NoteCache(mock_simplenote_client)
        assert context.is_authenticated()
        assert context.has_cache()

        # Verify consistency
        assert context.config is not None
        assert isinstance(context.config, Config)

    def test_context_with_pre_configured_components(self, mock_simplenote_client):
        """Test creating context with all components pre-configured."""
        config = Config()
        note_cache = NoteCache(mock_simplenote_client)

        context = ContextManager.create_context(
            config=config,
            simplenote_client=mock_simplenote_client,
            note_cache=note_cache,
        )

        # Verify all components are properly set
        assert context.config is config
        assert context.simplenote_client is mock_simplenote_client
        assert context.note_cache is note_cache
        assert context.is_authenticated()
        assert context.has_cache()

    def test_context_manager_factory_pattern(self, mock_simplenote_client):
        """Test ContextManager as a factory for different context configurations."""
        # Basic context
        basic_context = ContextManager.create_context()
        assert not basic_context.is_authenticated()
        assert not basic_context.has_cache()

        # Authenticated context
        auth_context = ContextManager.create_context(
            simplenote_client=mock_simplenote_client
        )
        assert auth_context.is_authenticated()
        assert not auth_context.has_cache()

        # Fully configured context
        config = Config()
        note_cache = NoteCache(mock_simplenote_client)
        full_context = ContextManager.create_context(
            config=config,
            simplenote_client=mock_simplenote_client,
            note_cache=note_cache,
        )
        assert full_context.is_authenticated()
        assert full_context.has_cache()

        # All contexts should be independent
        assert basic_context.config is not auth_context.config
        assert auth_context.config is not full_context.config
