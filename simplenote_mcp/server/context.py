"""Application context management using dependency injection.

This module provides a context manager for the Simplenote MCP server
that handles dependencies without relying on global state.
"""

from dataclasses import dataclass

from simplenote import Simplenote

from .cache import NoteCache
from .config import Config


@dataclass
class ServerContext:
    """Server context containing all application dependencies.

    This replaces global state with explicit dependency injection,
    making the code more testable and maintainable.
    """

    config: Config
    simplenote_client: Simplenote | None = None
    note_cache: NoteCache | None = None

    def __post_init__(self) -> None:
        """Validate context after initialization."""
        if not isinstance(self.config, Config):
            raise TypeError("config must be an instance of Config")

    def is_authenticated(self) -> bool:
        """Check if the context has an authenticated Simplenote client."""
        return self.simplenote_client is not None

    def has_cache(self) -> bool:
        """Check if the context has an initialized cache."""
        return self.note_cache is not None


class ContextManager:
    """Manages server context lifecycle.

    This class provides methods to create and manage server contexts
    without relying on global state.
    """

    @staticmethod
    def create_context(
        config: Config | None = None,
        simplenote_client: Simplenote | None = None,
        note_cache: NoteCache | None = None,
    ) -> ServerContext:
        """Create a new server context.

        Args:
            config: Configuration object (creates new if not provided)
            simplenote_client: Authenticated Simplenote client
            note_cache: Initialized note cache

        Returns:
            ServerContext instance
        """
        if config is None:
            config = Config()

        return ServerContext(
            config=config, simplenote_client=simplenote_client, note_cache=note_cache
        )
