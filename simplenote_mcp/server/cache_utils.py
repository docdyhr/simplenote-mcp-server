"""Cache utilities for Simplenote MCP server.

This module contains utility functions for common cache access patterns
that were duplicated throughout the codebase. These utilities provide:

- Safe cache initialization with fallback handling
- Background cache warming and population
- Standardized cache access patterns
- Pagination parameter extraction
- Cache manager class for centralized cache operations

This eliminates the repetitive cache initialization and fallback logic
that was duplicated 8+ times across the original codebase.
"""

import asyncio
import time
from collections.abc import Callable
from typing import Any

from .cache import NoteCache
from .config import get_config
from .errors import handle_exception
from .logging import logger


async def ensure_cache_initialized(
    note_cache: NoteCache | None,
    get_simplenote_client: Callable,
    initialize_cache_func: Callable,
) -> NoteCache:
    """Ensure cache is initialized, creating it if necessary.

    Args:
        note_cache: Current cache instance (may be None)
        get_simplenote_client: Function to get Simplenote client
        initialize_cache_func: Function to initialize cache

    Returns:
        Initialized cache instance
    """
    if note_cache is None:
        logger.info("Cache not initialized, creating empty cache")
        logger.debug("Attempting to create Simplenote client for cache initialization")

        # Create a minimal cache without waiting for initialization
        simplenote_client = get_simplenote_client()
        note_cache = NoteCache(simplenote_client)
        note_cache._initialized = True
        note_cache._notes = {}
        note_cache._last_sync = time.time()
        note_cache._tags = set()

        # Start initialization in the background
        asyncio.create_task(initialize_cache_func())

    return note_cache


def get_cache_or_create_minimal(
    note_cache: NoteCache | None,
    get_simplenote_client: Callable,
) -> NoteCache:
    """Get existing cache or create a minimal one for immediate use.

    Args:
        note_cache: Current cache instance (may be None)
        get_simplenote_client: Function to get Simplenote client

    Returns:
        Cache instance ready for use
    """
    if note_cache is None:
        logger.info("Cache not initialized, creating minimal cache")

        # Create a minimal cache without waiting for initialization
        simplenote_client = get_simplenote_client()
        note_cache = NoteCache(simplenote_client)
        note_cache._initialized = True
        note_cache._notes = {}
        note_cache._last_sync = time.time()
        note_cache._tags = set()

    return note_cache


async def initialize_cache_background(
    note_cache: NoteCache,
    timeout_seconds: int | None = None,
) -> None:
    """Initialize cache in the background with timeout handling.

    Args:
        note_cache: Cache instance to initialize
        timeout_seconds: Timeout for initialization (uses config default if None)
    """
    if timeout_seconds is None:
        config = get_config()
        timeout_seconds = config.cache_initialization_timeout
    try:
        logger.debug("Starting background cache initialization")

        # Get Simplenote client from cache
        sn = note_cache._client

        # Try direct API call to get notes synchronously first
        try:
            logger.debug("Attempting direct API call to get notes...")
            all_notes, status = sn.get_note_list()
            if status == 0 and isinstance(all_notes, list) and all_notes:
                # Success! Update the cache directly
                try:
                    await note_cache._lock.acquire()
                    for note in all_notes:
                        note_id = note.get("key")
                        if note_id:
                            note_cache._notes[note_id] = note
                            if "tags" in note and note["tags"]:
                                note_cache._tags.update(note["tags"])
                finally:
                    note_cache._lock.release()
                logger.info(
                    f"Direct API load successful, loaded {len(all_notes)} notes"
                )
        except Exception as e:
            logger.warning(
                f"Direct API load failed, falling back to cache initialize: {str(e)}"
            )

        # Start real initialization in background
        init_task = asyncio.create_task(note_cache.initialize())
        try:
            await asyncio.wait_for(init_task, timeout=timeout_seconds)
            logger.info(
                f"Note cache initialization completed successfully with {len(note_cache._notes)} notes"
            )
        except TimeoutError:
            logger.warning(
                f"Note cache initialization timed out after {timeout_seconds}s, "
                f"cache has {len(note_cache._notes)} notes"
            )
            # We already have some notes from direct API call hopefully

    except Exception as e:
        logger.error(f"Error during background initialization: {str(e)}", exc_info=True)


def get_cache_with_fallback(
    note_cache: NoteCache | None,
    get_simplenote_client: Callable,
    operation_name: str = "operation",
) -> tuple[NoteCache, bool]:
    """Get cache with fallback logic and initialization state.

    Args:
        note_cache: Current cache instance (may be None)
        get_simplenote_client: Function to get Simplenote client
        operation_name: Name of operation for logging

    Returns:
        Tuple of (cache_instance, is_initialized)
    """
    try:
        if note_cache is None:
            logger.info(
                f"Cache not available for {operation_name}, creating minimal cache"
            )
            cache = get_cache_or_create_minimal(note_cache, get_simplenote_client)
            return cache, False

        return note_cache, note_cache.is_initialized

    except Exception as e:
        logger.error(
            f"Error getting cache for {operation_name}: {str(e)}", exc_info=True
        )
        # Return a minimal cache as fallback
        try:
            cache = get_cache_or_create_minimal(None, get_simplenote_client)
            return cache, False
        except Exception as fallback_error:
            logger.error(
                f"Failed to create fallback cache: {str(fallback_error)}", exc_info=True
            )
            raise handle_exception(e, f"initializing cache for {operation_name}") from e


async def cache_warmup_background(
    note_cache: NoteCache,
    get_simplenote_client: Callable,
) -> None:
    """Warm up cache in the background by pre-loading data.

    Args:
        note_cache: Cache instance to warm up
        get_simplenote_client: Function to get Simplenote client
    """
    try:
        logger.debug("Starting cache warmup")

        # Get fresh client
        sn = get_simplenote_client()

        # Test connection first
        try:
            test_notes, status = sn.get_note_list()
            if status == 0:
                logger.debug(
                    f"Cache warmup: API connection successful, received {len(test_notes) if isinstance(test_notes, list) else 'data'} items"
                )
            else:
                logger.warning(
                    f"Cache warmup: API connection test failed with status {status}"
                )
                return
        except Exception as e:
            logger.warning(f"Cache warmup: API connection test failed: {str(e)}")
            return

        # Perform background initialization
        await initialize_cache_background(note_cache)

    except Exception as e:
        logger.error(f"Error during cache warmup: {str(e)}", exc_info=True)


def create_cache_with_client(simplenote_client: Any) -> NoteCache:
    """Create a new cache instance with the given client.

    Args:
        simplenote_client: The Simplenote API client

    Returns:
        New cache instance
    """
    cache = NoteCache(simplenote_client)
    cache._initialized = True
    cache._notes = {}
    cache._last_sync = time.time()
    cache._tags = set()
    return cache


async def safe_cache_operation(
    operation: Callable,
    operation_name: str,
    *args,
    **kwargs,
) -> Any:
    """Safely execute a cache operation with error handling.

    Args:
        operation: The operation to execute
        operation_name: Name of operation for logging
        *args: Arguments to pass to operation
        **kwargs: Keyword arguments to pass to operation

    Returns:
        Result of operation or None if failed
    """
    try:
        return await operation(*args, **kwargs)
    except Exception as e:
        logger.error(
            f"Error in cache operation '{operation_name}': {str(e)}", exc_info=True
        )
        return None


def get_pagination_params(arguments: dict[str, Any]) -> tuple[int, int]:
    """Extract pagination parameters from arguments.

    Args:
        arguments: Tool arguments dictionary

    Returns:
        Tuple of (limit, offset)
    """
    config = get_config()

    # Get limit parameter
    limit = arguments.get("limit")
    if limit is not None:
        try:
            limit = int(limit)
            if limit < 1:
                limit = config.default_resource_limit
        except (ValueError, TypeError):
            limit = config.default_resource_limit
    else:
        limit = config.default_resource_limit

    # Get offset parameter
    offset = arguments.get("offset", 0)
    try:
        offset = int(offset)
        if offset < 0:
            offset = 0
    except (ValueError, TypeError):
        offset = 0

    return limit, offset


class CacheManager:
    """Manager class for cache operations with common patterns."""

    def __init__(self, get_simplenote_client: Callable) -> None:
        """Initialize the cache manager.

        Args:
            get_simplenote_client: Function to get Simplenote client
        """
        self._get_simplenote_client = get_simplenote_client
        self._cache: NoteCache | None = None

    @property
    def cache(self) -> NoteCache | None:
        """Get the current cache instance."""
        return self._cache

    async def ensure_cache(self) -> NoteCache:
        """Ensure cache is available and initialized."""
        if self._cache is None:
            self._cache = get_cache_or_create_minimal(None, self._get_simplenote_client)
            # Start background initialization
            asyncio.create_task(self._background_init())

        return self._cache

    async def _background_init(self) -> None:
        """Initialize cache in background."""
        if self._cache is not None:
            await initialize_cache_background(self._cache)

    def is_cache_ready(self) -> bool:
        """Check if cache is available and initialized."""
        return self._cache is not None and self._cache.is_initialized

    async def get_or_create_note(self, note_id: str) -> dict[str, Any] | None:
        """Get note from cache or API."""
        cache = await self.ensure_cache()

        # Try cache first
        if self.is_cache_ready():
            try:
                return cache.get_note(note_id)
            except Exception:
                pass  # Fall through to API

        # Fall back to API
        try:
            sn = self._get_simplenote_client()
            note, status = sn.get_note(note_id)
            if status == 0 and isinstance(note, dict):
                # Update cache if available
                if self.is_cache_ready():
                    cache.update_cache_after_update(note)
                return note
        except Exception as e:
            logger.error(f"Error getting note {note_id}: {str(e)}", exc_info=True)

        return None
