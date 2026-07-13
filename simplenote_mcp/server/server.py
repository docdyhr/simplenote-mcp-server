"""Main Simplenote MCP server implementation."""

# Import standard libraries
import asyncio
import atexit
import hmac
import json
import os
import signal
import sys
import tempfile
import threading
import time
from collections import deque
from collections.abc import Iterable
from typing import Any, cast

# MCP imports
import mcp.server.stdio  # type: ignore  # noqa: E402
import mcp.server.streamable_http  # type: ignore  # noqa: E402
import mcp.types as types  # type: ignore  # noqa: E402
from mcp.server import NotificationOptions, Server  # type: ignore  # noqa: E402
from mcp.server.lowlevel.helper_types import (  # type: ignore  # noqa: E402
    ReadResourceContents,
)
from mcp.server.models import InitializationOptions  # type: ignore  # noqa: E402
from mcp.server.transport_security import (  # type: ignore  # noqa: E402
    TransportSecuritySettings,
)

# External imports
from pydantic import AnyUrl  # type: ignore  # noqa: E402
from simplenote import Simplenote  # type: ignore  # noqa: E402

from .cache import BackgroundSync, NoteCache  # noqa: E402

# Use our compatibility module for cross-version support
from .compat import Path  # noqa: E402
from .config import LogLevel, get_config  # noqa: E402
from .decorators import rate_limit
from .error_helpers import (
    format_error,
)
from .errors import (  # noqa: E402
    AuthenticationError,
    ConfigurationError,
    ResourceNotFoundError,
    ServerError,
    ValidationError,
    handle_exception,
)
from .logging import logger  # noqa: E402
from .middleware import (
    sanitize_arguments_for_logging,
    with_rate_limiting,
    with_request_validation,
    with_security_monitoring,
)
from .monitoring.metrics import (  # noqa: E402
    record_api_call,
    record_response_time,
    record_tool_call,
    start_metrics_collection,
    update_cache_size,
)
from .utils.common import (  # noqa: E402
    extract_title_from_content as extract_title_common,
)
from .utils.common import (
    safe_get,
)


def extract_title_from_content(content: str, fallback: str = "") -> str:
    """Extract the first non-empty line from content as title, limited to 30 chars.

    Args:
        content: The note content
        fallback: Fallback value if no non-empty line found

    Returns:
        First non-empty line (up to 30 chars) or fallback
    """
    title = extract_title_common(content)
    if title:
        return title[:30]  # Limit to 30 chars as per original behavior
    return fallback


# Utility functions imported from common module for consistency


# Remove this function since we're not using it

# Error messages for better maintainability and reusability
AUTH_ERROR_MSG = "SIMPLENOTE_EMAIL (or SIMPLENOTE_USERNAME) and SIMPLENOTE_PASSWORD environment variables must be set"
NOTE_CONTENT_REQUIRED = "Note content is required"
NOTE_ID_REQUIRED = "Note ID is required"
TAGS_REQUIRED = "Tags are required"
QUERY_REQUIRED = "Search query is required"
UNKNOWN_TOOL_ERROR = "Unknown tool: {name}"
UNKNOWN_PROMPT_ERROR = "Unknown prompt: {name}"
CACHE_INIT_FAILED = "Note cache initialization failed"
FAILED_GET_NOTE = "Failed to find note with ID {note_id}"
FAILED_UPDATE_TAGS = "Failed to update note tags"
FAILED_TRASH_NOTE = "Failed to move note to trash"
FAILED_RETRIEVE_NOTES = "Failed to retrieve notes for search"

# Tools that mutate Simplenote data. Only exposed when write_mode is enabled,
# and counted against the per-session write budget.
WRITE_TOOLS: frozenset[str] = frozenset(
    {
        "create_note",
        "update_note",
        "delete_note",
        "add_tags",
        "remove_tags",
        "replace_tags",
        "add_text",
        "restore_version",
        "replace_section",
        "append_to_daily_note",
        "get_or_create_note",
        "rename_tag",
        "bulk_tag",
        "restore_note",
        "publish_note",
        "unpublish_note",
        "permanent_delete_note",
        "empty_trash",
        "find_and_merge_duplicates",
        "encrypt_note",
        "decrypt_note",
    }
)

# Per-session rolling write-budget tracker (not reset across reconnects —
# intentional: keeps the guard effective during a single server process).
_write_timestamps: deque[float] = deque()
_write_budget_lock = threading.Lock()


def _check_write_budget() -> None:
    """Raise ValidationError if the session write budget is exhausted.

    Uses a rolling window defined by config write_budget_max /
    write_budget_window_seconds.  Called immediately before each write tool
    dispatch so idempotency short-circuits (no-ops) don't consume budget.
    """
    config = get_config()
    now = time.monotonic()
    window_start = now - config.write_budget_window_seconds
    with _write_budget_lock:
        while _write_timestamps and _write_timestamps[0] < window_start:
            _write_timestamps.popleft()
        if len(_write_timestamps) >= config.write_budget_max:
            raise ValidationError(
                f"Write budget exhausted: {config.write_budget_max} writes in "
                f"{config.write_budget_window_seconds}s. "
                "Confirm with the user that this bulk operation should continue before retrying.",
                subcategory="rate_limited",
            )


def _record_write() -> None:
    """Record a successful write operation against the session budget."""
    with _write_budget_lock:
        _write_timestamps.append(time.monotonic())


# Create a server instance
try:
    logger.info("Creating MCP server instance")
    server = Server("simplenote-mcp-server")
    logger.info("MCP server instance created successfully")
except Exception as e:
    logger.error(f"Error creating MCP server: {str(e)}", exc_info=True)
    record_api_call("create_note", success=False, error_type=type(e).__name__)
    raise

# Initialize Simplenote client
simplenote_client = None


def get_simplenote_client() -> Simplenote:
    """Get or create the Simplenote client.

    Returns:
        The Simplenote client instance

    Raises:
        AuthenticationError: If Simplenote credentials are not configured

    """
    global simplenote_client
    if simplenote_client is None:
        try:
            logger.info("Initializing Simplenote client")

            # Get credentials from config
            config = get_config()

            # Check if running in offline mode
            if config.offline_mode:
                logger.info("Running in offline mode - using mock Simplenote client")
                from unittest.mock import MagicMock

                # Create a mock client for offline mode
                mock_client = MagicMock()
                mock_client.get_note_list.return_value = ([], 0)
                mock_client.get_note.return_value = ({}, 0)
                mock_client.add_note.return_value = ({}, 0)
                mock_client.update_note.return_value = ({}, 0)
                mock_client.trash_note.return_value = 0

                simplenote_client = mock_client
                logger.info("Mock Simplenote client created for offline mode")
                return simplenote_client

            if not config.has_credentials:
                logger.error("Missing Simplenote credentials in environment variables")
                raise AuthenticationError(AUTH_ERROR_MSG)

            logger.info(
                f"Creating Simplenote client with username: {config.simplenote_email[:3] if config.simplenote_email else ''}***"
            )
            simplenote_client = Simplenote(
                config.simplenote_email, config.simplenote_password
            )
            logger.info("Simplenote client created successfully")

        except Exception as e:
            if isinstance(e, ServerError):
                raise
            logger.error(
                f"Error initializing Simplenote client: {str(e)}", exc_info=True
            )
            error = handle_exception(e, "initializing Simplenote client")
            raise error from e

    return simplenote_client


def clear_client_cache() -> None:
    """Clear the global Simplenote client cache.

    This is primarily used for testing to ensure fresh client instances.
    """
    global simplenote_client
    simplenote_client = None
    logger.debug("Simplenote client cache cleared")


# PID file for process management
PID_FILE_PATH = Path(tempfile.gettempdir()) / "simplenote_mcp_server.pid"
# Use same temp directory for consistency
ALT_PID_FILE_PATH = Path(tempfile.gettempdir()) / "simplenote_mcp_server_alt.pid"

# Initialize note cache and background sync
note_cache: NoteCache | None = None
background_sync: BackgroundSync | None = None

# Last authentication error message, set by background cache init when auth fails.
_last_auth_error: str | None = None


def get_last_auth_error() -> str | None:
    """Return the most recent authentication error, or None if auth succeeded."""
    return _last_auth_error


def write_pid_file() -> None:
    """Write PID to file for process management."""
    try:
        pid = os.getpid()
        PID_FILE_PATH.write_text(str(pid))

        # Also write to the alternative location in /tmp for compatibility
        try:
            ALT_PID_FILE_PATH.write_text(str(pid))
            logger.info(f"PID {pid} written to {PID_FILE_PATH} and {ALT_PID_FILE_PATH}")
        except (OSError, PermissionError):
            logger.info(f"PID {pid} written to {PID_FILE_PATH}")
    except (OSError, PermissionError) as e:
        logger.error(f"Error writing PID file: {str(e)}", exc_info=True)


def cleanup_pid_file() -> None:
    """Remove PID file on exit."""
    try:
        if PID_FILE_PATH.exists():
            PID_FILE_PATH.unlink()

        # Also remove the alternative PID file if it exists
        if ALT_PID_FILE_PATH.exists():
            ALT_PID_FILE_PATH.unlink()
    except (OSError, FileNotFoundError, PermissionError):
        # Silently ignore errors during cleanup to avoid logging issues during shutdown
        pass


# Global flag to indicate shutdown is in progress
shutdown_requested = False


def setup_signal_handlers() -> None:
    """Set up signal handlers for graceful shutdown."""

    def signal_handler(
        sig: int, _: object
    ) -> None:  # Frame argument is unused but required by signal API
        """Handle termination signals."""
        global shutdown_requested
        signal_name = signal.Signals(sig).name
        logger.info(f"Received {signal_name} signal, shutting down...")

        # Set the shutdown flag
        shutdown_requested = True

        # Stop log pattern monitoring
        try:
            from .log_monitor import stop_log_monitoring

            stop_log_monitoring()
            logger.info("Stopped log pattern monitoring")
        except Exception as e:
            logger.error(f"Error stopping log pattern monitoring: {e}")

        # Stop HTTP endpoints
        try:
            from .http_endpoints import stop_http_endpoints

            stop_http_endpoints()
            logger.info("Stopped HTTP endpoints")
        except Exception as e:
            logger.error(f"Error stopping HTTP endpoints: {e}")

        # If we're not in the main thread or inside an async function,
        # we need to exit immediately
        current_thread = threading.current_thread()
        if current_thread != threading.main_thread():
            logger.info("Signal received in non-main thread, exiting immediately")
            # Cleanup will be handled by atexit
            sys.exit(0)

        # In the main thread, we'll let the async loops check the flag
        # and exit gracefully via the shutdown_requested flag

    # Register handlers for common termination signals
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Register cleanup function to run at exit
    atexit.register(cleanup_pid_file)


async def _test_simplenote_connection(sn: Any) -> None:
    """Test Simplenote API connection.

    Explicitly verifies the auth token before making any API request so that a
    failed login produces a clear AuthenticationError at startup instead of a
    cryptic TypeError 75 seconds later deep inside urllib's putheader().

    Token acquisition order:
    1. SIMPLENOTE_TOKEN env var — user-supplied pre-authenticated token.
    2. macOS keychain entry stored by the Simplenote desktop app (darwin only).
       The Simplenote app keeps this token current; we piggyback on it when
       auth.simperium.com is unreachable (decommissioned as of 2025).
    3. simplenote.authenticate() — classic password auth, kept as fallback.
    """
    logger.debug("Testing Simplenote client connection...")
    loop = asyncio.get_running_loop()

    # --- Step 1: acquire a token from the fastest available source ---

    token: str | None = None

    # 1a. Explicit env-var override (highest priority).
    env_token = os.environ.get("SIMPLENOTE_TOKEN", "").strip()
    if env_token:
        token = env_token
        logger.debug(
            "Using Simplenote token from SIMPLENOTE_TOKEN environment variable"
        )

    # 1b. macOS keychain — prompt-free MCP cache first, Simplenote Desktop as fallback.
    if not token:
        from .keychain import get_simperium_token

        kc_token = await loop.run_in_executor(
            None, lambda: get_simperium_token(sn.username)
        )
        if kc_token:
            token = kc_token
            logger.debug("Using Simplenote token from macOS keychain")

    # 1c. Classic password auth via auth.simperium.com (may be decommissioned).
    if not token:
        try:
            token = await loop.run_in_executor(
                None,
                lambda: sn.authenticate(sn.username, sn.password),
            )
        except Exception as auth_exc:
            msg = (
                f"Simplenote authentication failed — check SIMPLENOTE_EMAIL / "
                f"SIMPLENOTE_PASSWORD or the Simplenote account/API status. "
                f"({type(auth_exc).__name__}: {auth_exc})"
            )
            logger.error(msg)
            raise AuthenticationError(msg) from auth_exc

    if not token:
        msg = (
            "Simplenote authentication returned no token — check SIMPLENOTE_EMAIL / "
            "SIMPLENOTE_PASSWORD or the Simplenote account/API status. "
            "Tip: set SIMPLENOTE_TOKEN to a pre-authenticated token, or ensure "
            "the Simplenote desktop app is installed and signed in."
        )
        logger.error(msg)
        raise AuthenticationError(msg)

    # Cache the token so subsequent starts are prompt-free regardless of which
    # auth path succeeded (keychain, password, or env-var via SIMPLENOTE_TOKEN).
    if token and not env_token:
        from .keychain import cache_token

        await loop.run_in_executor(None, lambda: cache_token(sn.username, token))

    # Cache the token so get_note_list reuses it without re-authenticating.
    sn.token = token
    logger.debug("Simplenote authentication successful, token acquired")

    # Step 2: verify the API is reachable with the fresh token.
    try:
        test_notes, status = await loop.run_in_executor(None, sn.get_note_list)
        if status == 0:
            logger.debug(
                f"Simplenote API connection successful, received "
                f"{len(test_notes) if isinstance(test_notes, list) else 'data'} items"
            )
        else:
            logger.error(f"Simplenote API connection test failed with status {status}")
            from .keychain import invalidate_cached_token

            invalidate_cached_token(sn.username)
            raise AuthenticationError("Failed to authenticate with Simplenote API")
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Error testing Simplenote API connection: {str(e)}")
        raise


async def _create_minimal_cache(sn: Any) -> NoteCache:
    """Create a minimal cache for immediate use."""
    logger.debug("Cache is uninitialized; initializing cache now.")
    cache = NoteCache(sn)
    logger.debug("Cache initialization complete.")
    cache._initialized = True
    cache._notes = {}
    cache._last_sync = time.time()
    cache._tags = set()
    logger.debug(f"Created empty note cache with client: {sn}")
    return cache


async def _populate_cache_direct(cache: NoteCache, sn: Any) -> None:
    """Populate cache directly with API call.

    Runs the blocking API call in a thread pool to avoid blocking the event loop.
    """
    try:
        logger.debug("Attempting direct API call to get notes...")
        # Run blocking API call in thread pool
        loop = asyncio.get_running_loop()
        all_notes, status = await loop.run_in_executor(
            None,  # Use default executor
            sn.get_note_list,
        )
        if status == 0 and isinstance(all_notes, list) and all_notes:
            # Success! Update the cache directly
            try:
                await cache._lock.acquire()
                for note in all_notes:
                    note_id = note.get("key")
                    if note_id:
                        cache._notes[note_id] = note
                # Build tag, title, and word indexes for every note — matching
                # NoteCache.initialize()'s indexing. cache._initialized is
                # already True by the time this runs (set in
                # _create_minimal_cache for non-blocking startup), which
                # means initialize()'s own re-entrancy guard makes it a no-op
                # later, so this direct-load path is the only place the
                # initial note set gets indexed. Without this, only the tag
                # index was built — title/word search were blind to every
                # note until it was individually touched by a create/update
                # tool call.
                cache._build_all_indexes()
            finally:
                cache._lock.release()
            logger.info(f"Direct API load successful, loaded {len(all_notes)} notes")
            cache._last_sync_cursor = sn.current
    except Exception as e:
        logger.warning(
            f"Direct API load failed, falling back to cache initialize: {str(e)}"
        )


async def _run_full_cache_initialization(cache: NoteCache, timeout: int) -> None:
    """Run full cache initialization with timeout."""
    init_task = asyncio.create_task(cache.initialize())
    try:
        await asyncio.wait_for(init_task, timeout=timeout)
        logger.info(
            f"Note cache initialization completed successfully with {len(cache._notes)} notes"
        )
        # Mark cache as ready for HTTP endpoints
        try:
            from .http_endpoints import set_component_ready

            set_component_ready("note_cache", True)
        except ImportError:
            pass  # HTTP endpoints not available
    except TimeoutError:
        logger.warning(
            f"Note cache initialization timed out after {timeout}s, cache has {len(cache._notes)} notes"
        )


async def _background_cache_initialization(
    cache: NoteCache, sn: Any, timeout: int
) -> None:
    """Perform background cache initialization."""
    if cache is None:
        logger.error("Background initialization called but cache is None.")
        return

    try:
        # First try direct API population
        await _populate_cache_direct(cache, sn)

        # Then run full initialization
        await _run_full_cache_initialization(cache, timeout)

    except Exception as e:
        logger.error(f"Error during background initialization: {str(e)}", exc_info=True)


async def initialize_cache() -> None:
    """Initialize the note cache and start background sync.

    This is now truly non-blocking - it creates a minimal cache immediately
    and loads notes in the background without awaiting.
    """
    global note_cache, background_sync
    logger.debug("Initializing note cache (non-blocking)")

    try:
        logger.info("Starting non-blocking cache initialization")

        # Get Simplenote client (don't test connection yet - do it async)
        sn = get_simplenote_client()

        # Create minimal empty cache immediately if needed
        if note_cache is None:
            note_cache = await _create_minimal_cache(sn)
            logger.info("Created minimal cache, will populate in background")

        # Start background sync immediately (it handles its own initialization)
        if background_sync is None:
            background_sync = BackgroundSync(note_cache)
            await background_sync.start()
            logger.info("Background sync started")

        # Kick off background initialization WITHOUT awaiting
        # This allows the MCP server to start serving requests immediately
        config = get_config()
        asyncio.create_task(
            _background_cache_initialization_safe(
                note_cache, sn, config.cache_initialization_timeout
            )
        )
        logger.info("Cache initialization task started in background")

    except Exception as e:
        if isinstance(e, ServerError):
            raise
        logger.error(f"Error initializing cache: {str(e)}", exc_info=True)
        error = handle_exception(e, "initializing cache")
        raise error from e


async def _background_cache_initialization_safe(
    cache: NoteCache, client: Simplenote, timeout: int
) -> None:
    """Safely initialize cache in background with error handling.

    This runs completely asynchronously and won't block server startup.

    Args:
        cache: The note cache to initialize
        client: The Simplenote client
        timeout: Timeout for initialization in seconds
    """
    global _last_auth_error
    try:
        logger.info("Background cache initialization starting...")

        # Test connection first (async, non-blocking)
        await _test_simplenote_connection(client)

        # Clear any previous auth error on success
        _last_auth_error = None

        # Now do the full initialization
        await _background_cache_initialization(cache, client, timeout)

        logger.info("Background cache initialization completed successfully")
    except asyncio.CancelledError:
        logger.info("Background cache initialization cancelled")
    except AuthenticationError as e:
        _last_auth_error = str(e)
        logger.error(f"Background cache initialization failed: {str(e)}", exc_info=True)
    except Exception as e:
        logger.error(f"Background cache initialization failed: {str(e)}", exc_info=True)
        # Don't raise - we don't want to crash the server
        # The cache will retry on next background sync


# ===== RESOURCE CAPABILITIES =====


@server.list_resources()
async def handle_list_resources(
    tag: str | None = None,
    limit: int | None = None,
    offset: int = 0,
    sort_by: str = "modifydate",
    sort_direction: str = "desc",
) -> list[types.Resource]:
    """Handle the list_resources capability with pagination support.

    Args:
        tag: Optional tag to filter notes by. Use 'untagged' to find notes without tags.
        limit: Optional limit for the number of notes to return
        offset: Number of notes to skip (pagination offset, 0-based)
        sort_by: Field to sort by (modifydate, createdate, title)
        sort_direction: Sort direction (asc or desc)

    Returns:
        List of Simplenote note resources with pagination metadata.
        The first resource in the list contains pagination metadata in its meta field:
        - total: Total number of matching notes
        - offset: Current offset (0-based)
        - limit: Number of notes per page
        - has_more: Whether there are more notes after this page
        - next_offset: Offset for next page (null if no next page)
        - prev_offset: Offset for previous page (null if first page)
        - page: Current page number (1-based)
        - total_pages: Total number of pages

    """
    logger.debug(
        f"list_resources called with tag={tag}, limit={limit}, offset={offset}, sort_by={sort_by}, sort_direction={sort_direction}"
    )

    try:
        from .cache_utils import get_cache_or_create_minimal

        # Check for cache initialization, but don't block waiting for it
        global note_cache
        note_cache = get_cache_or_create_minimal(note_cache, get_simplenote_client)

        # Start initialization in the background if not already initialized
        if not note_cache.is_initialized:
            asyncio.create_task(initialize_cache())

        # Use the cache to get notes with filtering
        config = get_config()

        # Use provided limit or fall back to default
        actual_limit = limit if limit is not None else config.default_resource_limit

        # Apply tag filtering if specified and pagination
        logger.debug(
            "Fetching notes from cache with limit: %d, offset: %d, sort_by: %s, sort_direction: %s, tag_filter: %s",
            actual_limit,
            offset,
            sort_by,
            sort_direction,
            tag,
        )

        # Get total notes count for pagination info
        total_matching_notes = len(note_cache.get_all_notes(tag_filter=tag))

        # Get the paginated notes
        notes = note_cache.get_all_notes(
            limit=actual_limit,
            tag_filter=tag,
            offset=offset,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )
        # Ensure each note has tags key for default tags list
        for note in notes:
            note.setdefault("tags", [])

        pagination_info = note_cache.get_pagination_info(
            total_items=total_matching_notes, limit=actual_limit, offset=offset
        )

        logger.debug(
            f"Listing resources, found {len(notes)} notes"
            + (f" with tag '{tag}'" if tag else "")
            + f" (page {pagination_info.get('page', 1)} of {pagination_info.get('total_pages', 1)})"
        )

        resources = []
        for index, note in enumerate(notes):
            note.setdefault("tags", [])
            tags = note["tags"]
            content = note.get("content", "")
            modifydate = note.get("modifydate", "unknown date")
            description = f"Note from {modifydate}"
            if tags:
                description += f" — tags: {', '.join(tags)}"

            # Tags/dates and (on the first resource) pagination info are
            # attached via the MCP spec's `_meta` extension field — the only
            # part of the Resource schema clients are guaranteed to preserve.
            # Bare dynamic attributes (the previous approach) aren't part of
            # the schema, so a spec-compliant client has no obligation to
            # keep them even though this server's own Pydantic models are
            # permissive enough to hold them locally.
            meta: dict[str, Any] = {
                "tags": tags,
                "modifydate": note.get("modifydate", ""),
                "createdate": note.get("createdate", ""),
            }
            if index == 0:
                meta["pagination"] = pagination_info

            resource = types.Resource(
                uri=cast(Any, f"simplenote://note/{note['key']}"),
                name=extract_title_from_content(content, note.get("key", "")),
                description=description,
                _meta=meta,
            )
            resources.append(resource)

        return resources

    except Exception as e:
        if isinstance(e, ServerError):
            logger.error(f"Error listing resources: {str(e)}")
        else:
            logger.error(f"Error listing resources: {str(e)}", exc_info=True)

        # Return empty list instead of raising an exception
        # to avoid breaking the client experience
        return []


@server.read_resource()  # type: ignore
async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
    """Handle the read_resource capability.

    Args:
        uri: The URI of the resource to read

    Returns:
        The contents and metadata of the resource

    Raises:
        ValidationError: If the URI is invalid
        ResourceNotFoundError: If the note is not found

    """
    logger.debug(f"read_resource called for URI: {uri}")

    # Parse the URI to get the note ID
    uri_str = str(uri)
    if not uri_str.startswith("simplenote://note/"):
        logger.error(f"Invalid Simplenote URI: {uri}")
        raise format_error("uri", "simplenote://note/[note_id] format")

    note_id = uri_str.replace("simplenote://note/", "")

    try:
        from .cache_utils import get_cache_or_create_minimal

        # Check for cache initialization, but don't block waiting for it
        global note_cache
        note_cache = get_cache_or_create_minimal(note_cache, get_simplenote_client)

        # Start initialization in the background if not already initialized
        if not note_cache.is_initialized:
            asyncio.create_task(initialize_cache())

        # Try to get the note from cache first if cache is initialized
        note = None
        if note_cache is not None:
            logger.debug("Attempting to fetch note with ID: %s from cache", note_id)
            try:
                note = note_cache.get_note(note_id)
                logger.debug(f"Found note {note_id} in cache")
            except ResourceNotFoundError:
                # If not in cache, we'll try the API directly
                logger.debug(f"Note {note_id} not found in cache, trying API")
                # Get the note from Simplenote API
                sn = get_simplenote_client()
                note, status = sn.get_note(note_id)

                if status != 0 or not isinstance(note, dict):
                    error_msg = f"Failed to get note with ID {note_id}"
                    logger.error(error_msg)
                    raise ResourceNotFoundError(error_msg) from None

                # Update the cache if it's initialized
                if note_cache is not None and note_cache.is_initialized:
                    note_cache.update_cache_after_update(note)

        # Extract note data - only process the note once
        note_content = safe_get(note, "content", "")
        note_tags = safe_get(note, "tags", [])
        note_modifydate = safe_get(note, "modifydate", "")
        note_createdate = safe_get(note, "createdate", "")

        # Tags/dates are attached via the MCP spec's `_meta` extension field —
        # see the matching comment in handle_list_resources for why this
        # replaces the previous non-schema dynamic-attribute approach.
        # The @server.read_resource() decorator wraps whatever this function
        # returns into ReadResourceResult itself — it expects
        # Iterable[ReadResourceContents], not a pre-built ReadResourceResult
        # (returning the latter gets misidentified as the Iterable case,
        # since pydantic BaseModel defines __iter__, and iterating it yields
        # (field_name, value) tuples instead of resource-content objects).
        return [
            ReadResourceContents(
                content=note_content,
                mime_type="text/plain",
                meta={
                    "tags": note_tags,
                    "modifydate": note_modifydate,
                    "createdate": note_createdate,
                },
            )
        ]

    except Exception as e:
        if isinstance(e, ServerError):
            raise
        logger.error(f"Error reading resource: {str(e)}", exc_info=True)
        error = handle_exception(e, f"reading note {note_id}")
        raise error from e


# ===== TOOL CAPABILITIES =====


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Handle the list_tools capability.

    Returns:
        List of available tools

    """
    # Annotation presets
    _READ = types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
    _ADD = types.ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
    _ADD_IDEM = types.ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
    _WRITE = types.ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=True,
    )
    _WRITE_IDEM = types.ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
        openWorldHint=True,
    )

    try:
        config = get_config()
        logger.info("Listing available tools")

        read_tools = [
            types.Tool(
                name="list_notes",
                description=(
                    "List recent notes, optionally filtered by tag. "
                    "Use search_notes for full-text or boolean queries. "
                    "Use list_tags first to discover available tag names."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tag": {
                            "type": "string",
                            "description": "Filter by tag name (exact match)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of notes to return (default: 20, max: 100)",
                        },
                        "include_deleted": {
                            "type": "boolean",
                            "description": "Include trashed notes (default: false)",
                        },
                    },
                    "required": [],
                },
                annotations=_READ,
            ),
            types.Tool(
                name="search_notes",
                description=(
                    "Search for notes in Simplenote with advanced capabilities including "
                    "fuzzy matching, pagination, and sorting support. "
                    "To find the most recently updated note on a topic, use "
                    "sort_by='modifydate' with sort_direction='desc' and limit=1. "
                    "Use list_tags first if you need to discover available tags before filtering."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query (supports boolean operators AND, OR, NOT; phrase matching with quotes; tag filters like tag:work; date filters like from:2023-01-01 to:2023-12-31 or natural language dates like from:last_week to:yesterday)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return per page (default: 20)",
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Number of results to skip for pagination (default: 0)",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags to filter by — all must be present (array of strings; a comma-separated string is also accepted). Use 'untagged' to find notes without tags.",
                        },
                        "from_date": {
                            "type": "string",
                            "description": "Filter notes modified after this date (ISO format e.g. 2023-01-01, or natural language e.g. yesterday, last_week, 3_days_ago)",
                        },
                        "to_date": {
                            "type": "string",
                            "description": "Filter notes modified before this date (ISO format e.g. 2023-12-31, or natural language e.g. today, yesterday)",
                        },
                        "fuzzy": {
                            "type": "boolean",
                            "description": "Enable fuzzy matching to handle typos and approximate matches (default: false)",
                        },
                        "sort_by": {
                            "type": "string",
                            "enum": ["relevance", "modifydate", "createdate"],
                            "description": (
                                "Sort results by field. Default: 'relevance' (by match quality). "
                                "Use 'modifydate' to get the most recently updated notes first. "
                                "Use 'createdate' to get the newest-created notes first."
                            ),
                        },
                        "sort_direction": {
                            "type": "string",
                            "enum": ["asc", "desc"],
                            "description": "Sort direction: 'desc' (newest/highest first, default) or 'asc' (oldest/lowest first).",
                        },
                        "pinned": {
                            "type": "boolean",
                            "description": "Filter by pin status: true = only pinned notes, false = only unpinned notes, omit = all notes",
                        },
                        "created_after": {
                            "type": "string",
                            "description": "Filter notes created after this date (ISO format e.g. 2023-01-01)",
                        },
                        "modified_after": {
                            "type": "string",
                            "description": "Filter notes modified after this date (ISO format e.g. 2023-06-01)",
                        },
                    },
                    "required": ["query"],
                },
                annotations=_READ,
            ),
            types.Tool(
                name="get_note",
                description=(
                    "Retrieves the full content of a note by ID from Simplenote. "
                    "Use search_notes when you don't know the exact note ID."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to retrieve",
                        }
                    },
                    "required": ["note_id"],
                },
                annotations=_READ,
            ),
            types.Tool(
                name="list_tags",
                description=(
                    "List all tags used across notes with note counts. "
                    "Use this before creating or searching by tags to discover existing tags "
                    "and avoid fragmentation."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sort_by": {
                            "type": "string",
                            "enum": ["alpha", "count"],
                            "description": "Sort order: 'alpha' (alphabetical, default) or 'count' (by note count descending)",
                        },
                    },
                    "required": [],
                },
                annotations=_READ,
            ),
            types.Tool(
                name="get_note_versions",
                description="Retrieve the version history of a note (up to 10 most recent versions).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note",
                        },
                    },
                    "required": ["note_id"],
                },
                annotations=_READ,
            ),
            types.Tool(
                name="find_untagged_notes",
                description=(
                    "List notes that have no tags. "
                    "Useful for tag housekeeping — find notes that need to be organized."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of notes to return (default: 50)",
                        },
                    },
                },
                annotations=_READ,
            ),
            types.Tool(
                name="export_notes",
                description="Export one or more notes to Markdown or JSON format",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_ids": {
                            "type": "string",
                            "description": "Note IDs to export (comma-separated)",
                        },
                        "format": {
                            "type": "string",
                            "description": "Export format: 'markdown' (with YAML front matter) or 'json' (default: markdown)",
                            "enum": ["markdown", "json"],
                        },
                        "include_metadata": {
                            "type": "boolean",
                            "description": "Include metadata like dates, tags, and ID (default: true)",
                        },
                    },
                    "required": ["note_ids"],
                },
                annotations=_READ,
            ),
            types.Tool(
                name="get_server_info",
                description=(
                    "Return version, author, and debug information about this MCP server. "
                    "Use this to confirm which version is running, check whether the cache "
                    "is initialized, and see runtime settings (log level, sync interval, "
                    "offline mode). No parameters required."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
                annotations=_READ,
            ),
            types.Tool(
                name="vault_status",
                description=(
                    "Check the Vault encryption key status: whether a key is available "
                    "this session, which provider it came from (keyring or "
                    "SIMPLENOTE_VAULT_KEY_FILE), and how many notes are currently "
                    "Vault-encrypted. Call this before encrypt_note/decrypt_note or "
                    "create_note/update_note with encrypt=true if you're unsure whether "
                    "a key is provisioned. No parameters required."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
                annotations=_READ,
            ),
        ]

        write_tools = [
            types.Tool(
                name="create_note",
                description=(
                    "Create a new note in Simplenote. "
                    "Use get_or_create_note if you need to avoid duplicate notes."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The content of the note",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags for the note (array of strings; a comma-separated string is also accepted)",
                        },
                        "encrypt": {
                            "type": "boolean",
                            "description": "Encrypt the note body locally before it reaches Simplenote (default: false). Simplenote has no encryption at rest — use this for sensitive content. The title (first line) stays readable; only the OS holding the Vault key can decrypt the rest. See vault_status.",
                        },
                    },
                    "required": ["content"],
                },
                annotations=_ADD,
            ),
            types.Tool(
                name="update_note",
                description=(
                    "Replaces the full note content in Simplenote. "
                    "IMPORTANT: content replaces the entire note — call get_note first when "
                    "changing only part of it. "
                    "Use add_text to append or prepend without overwriting."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to update",
                        },
                        "content": {
                            "type": "string",
                            "description": "The new content of the note",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags for the note (array of strings; a comma-separated string is also accepted)",
                        },
                        "encrypt": {
                            "type": "boolean",
                            "description": "Encrypt the new content locally before it reaches Simplenote (default: false). Required to be true when replacing a note that's already Vault-encrypted — otherwise update_note refuses rather than silently overwriting encrypted content with plaintext.",
                        },
                    },
                    "required": ["note_id", "content"],
                },
                annotations=_WRITE,
            ),
            types.Tool(
                name="delete_note",
                description=(
                    "Soft-deletes a note from Simplenote (moves to Trash). "
                    "Use restore_note to undo. The note is not permanently deleted."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to delete",
                        }
                    },
                    "required": ["note_id"],
                },
                annotations=_WRITE_IDEM,
            ),
            types.Tool(
                name="add_tags",
                description=(
                    "Add tags to an existing note without replacing existing ones. "
                    "Use replace_tags to set the complete tag list from scratch."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to modify",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags to add (array of strings; a comma-separated string is also accepted)",
                        },
                    },
                    "required": ["note_id", "tags"],
                },
                annotations=_ADD_IDEM,
            ),
            types.Tool(
                name="remove_tags",
                description=(
                    "Remove specific tags from an existing note. "
                    "Use replace_tags to set an entirely new tag list."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to modify",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags to remove (array of strings; a comma-separated string is also accepted)",
                        },
                    },
                    "required": ["note_id", "tags"],
                },
                annotations=_WRITE_IDEM,
            ),
            types.Tool(
                name="replace_tags",
                description=(
                    "Replace ALL tags on an existing note. "
                    "Use add_tags or remove_tags for partial changes."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to modify",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "New tags — replaces the full tag list (array of strings; a comma-separated string is also accepted)",
                        },
                    },
                    "required": ["note_id", "tags"],
                },
                annotations=_WRITE,
            ),
            types.Tool(
                name="add_text",
                description=(
                    "Append or prepend text to an existing note without overwriting the full note. "
                    "Use this instead of update_note when you only want to append or prepend content "
                    "without overwriting the full note."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to modify",
                        },
                        "text": {
                            "type": "string",
                            "description": "The text to add to the note",
                        },
                        "position": {
                            "type": "string",
                            "enum": ["end", "beginning"],
                            "description": "Where to add the text: 'end' (default) or 'beginning'",
                        },
                    },
                    "required": ["note_id", "text"],
                },
                annotations=_ADD,
            ),
            types.Tool(
                name="replace_section",
                description="Replace the content of a Markdown section (## heading) in a note without touching other sections.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to update",
                        },
                        "header": {
                            "type": "string",
                            "description": "The section header text (without ## prefix)",
                        },
                        "new_content": {
                            "type": "string",
                            "description": "The new content to replace the section body with",
                        },
                    },
                    "required": ["note_id", "header", "new_content"],
                },
                annotations=_WRITE,
            ),
            types.Tool(
                name="restore_version",
                description=(
                    "Restore a note to a specific earlier version. "
                    "Use get_note_versions first to see available versions. "
                    "No-op (returns no_op=true) if the target version is identical to current."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to restore",
                        },
                        "version": {
                            "type": "integer",
                            "description": "The version number to restore to",
                        },
                    },
                    "required": ["note_id", "version"],
                },
                annotations=_WRITE_IDEM,
            ),
            types.Tool(
                name="append_to_daily_note",
                description="Append a timestamped entry to today's daily note. Creates it if it doesn't exist.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The text to append to today's daily note",
                        },
                    },
                    "required": ["text"],
                },
                annotations=_ADD,
            ),
            types.Tool(
                name="get_or_create_note",
                description=(
                    "Find an existing note by title or create it if not found. "
                    "Use this for atomic find-or-create to avoid duplicate notes."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "The title (first line) to search for or use when creating",
                        },
                        "content": {
                            "type": "string",
                            "description": "Default content when creating (defaults to '# <title>')",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags to apply when creating the note",
                        },
                    },
                    "required": ["title"],
                },
                annotations=_ADD,
            ),
            types.Tool(
                name="rename_tag",
                description="Rename a tag across all notes that use it. Supports dry_run to preview changes.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "old_tag": {
                            "type": "string",
                            "description": "The current tag name to rename",
                        },
                        "new_tag": {
                            "type": "string",
                            "description": "The new tag name",
                        },
                        "dry_run": {
                            "type": "boolean",
                            "description": "If true, preview changes without writing (default: false)",
                        },
                    },
                    "required": ["old_tag", "new_tag"],
                },
                annotations=_WRITE,
            ),
            types.Tool(
                name="bulk_tag",
                description=(
                    "Add, remove, or set tags on multiple notes in one operation. "
                    "Actions: 'add' appends tags, 'remove' strips tags, 'set' replaces all tags."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of note IDs to operate on",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["add", "remove", "set"],
                            "description": "Tag action: add, remove, or set",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags to apply",
                        },
                    },
                    "required": ["note_ids", "action", "tags"],
                },
                annotations=_WRITE,
            ),
            types.Tool(
                name="restore_note",
                description=(
                    "Restore a note from the trash. "
                    "Reverses a delete_note operation — un-trashes the note."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to restore",
                        },
                    },
                    "required": ["note_id"],
                },
                annotations=_ADD_IDEM,
            ),
            types.Tool(
                name="publish_note",
                description=(
                    "Publish a note to a public URL accessible without login. "
                    "Sets the 'published' system tag and returns the public_url. "
                    "Use unpublish_note to reverse."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to publish",
                        },
                    },
                    "required": ["note_id"],
                },
                annotations=_ADD_IDEM,
            ),
            types.Tool(
                name="unpublish_note",
                description=(
                    "Remove a note from public access by clearing its 'published' system tag. "
                    "Reverses publish_note. No-op if the note is already unpublished."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to unpublish",
                        },
                    },
                    "required": ["note_id"],
                },
                annotations=_WRITE_IDEM,
            ),
            types.Tool(
                name="find_and_merge_duplicates",
                description="Find duplicate or near-duplicate notes and optionally merge them",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "threshold": {
                            "type": "number",
                            "description": "Similarity threshold from 0.0 to 1.0 (default: 0.8). Higher values require more similarity.",
                        },
                        "dry_run": {
                            "type": "boolean",
                            "description": "If true (default), only report duplicates without merging. Set to false to actually merge.",
                        },
                        "tag_filter": {
                            "type": "string",
                            "description": "Only check notes with this tag (optional, helps narrow scope)",
                        },
                    },
                    "required": [],
                },
                annotations=_WRITE,
            ),
            types.Tool(
                name="permanent_delete_note",
                description=(
                    "Permanently and irreversibly delete a single note. "
                    "Unlike delete_note (which moves to trash), this operation CANNOT be undone. "
                    "Requires confirm=true to execute; omit or pass confirm=false for a dry-run preview. "
                    "Use empty_trash to permanently delete all trashed notes at once."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to permanently delete",
                        },
                        "confirm": {
                            "type": "boolean",
                            "description": (
                                "Safety guard — must be true to execute deletion. "
                                "Pass false (or omit) for a dry-run that describes "
                                "what would happen without making any changes."
                            ),
                        },
                    },
                    "required": ["note_id", "confirm"],
                },
                annotations=_WRITE_IDEM,
            ),
            types.Tool(
                name="empty_trash",
                description=(
                    "Permanently delete all notes currently in the trash. "
                    "This operation CANNOT be undone. "
                    "By default (dry_run=true) returns a list of trashed notes without deleting them. "
                    "Pass dry_run=false AND confirm=true to actually empty the trash."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dry_run": {
                            "type": "boolean",
                            "description": (
                                "When true (default), list trashed notes without deleting them. "
                                "Set to false (combined with confirm=true) to permanently delete."
                            ),
                        },
                        "confirm": {
                            "type": "boolean",
                            "description": (
                                "Safety guard — must be true to execute deletion. "
                                "Has no effect when dry_run=true."
                            ),
                        },
                    },
                },
                annotations=_WRITE_IDEM,
            ),
            types.Tool(
                name="encrypt_note",
                description=(
                    "Encrypt an existing note's body locally (AES-256-GCM) so Simplenote's "
                    "servers only ever store ciphertext — use for notes containing sensitive "
                    "data, since Simplenote itself has no encryption at rest. The title "
                    "(first line) stays readable; only the OS holding the Vault key can "
                    "decrypt the rest. Idempotent — a no-op if the note is already encrypted. "
                    "Use decrypt_note to reverse, or create_note/update_note with encrypt=true "
                    "to write pre-encrypted content in one call."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to encrypt",
                        },
                    },
                    "required": ["note_id"],
                },
                annotations=_ADD_IDEM,
            ),
            types.Tool(
                name="decrypt_note",
                description=(
                    "Reverse encrypt_note: decrypt a Vault-encrypted note's body and store "
                    "it back in Simplenote as plaintext. Idempotent — a no-op if the note "
                    "isn't currently encrypted. Requires the same Vault key the note was "
                    "encrypted with (see vault_status)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to decrypt",
                        },
                    },
                    "required": ["note_id"],
                },
                annotations=_WRITE_IDEM,
            ),
        ]

        tools = read_tools + (write_tools if config.write_mode else [])
        logger.info(
            f"Returning {len(tools)} tools "
            f"(write_mode={'on' if config.write_mode else 'off'}): "
            f"{', '.join(t.name for t in tools)}"
        )
        return tools

    except Exception as e:
        logger.error(f"Error listing tools: {str(e)}", exc_info=True)
        return [
            types.Tool(
                name="search_notes",
                description=(
                    "Search for notes in Simplenote with advanced capabilities. "
                    "Use sort_by='modifydate', sort_direction='desc' to retrieve the most recently updated note on a topic."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query",
                        },
                    },
                    "required": ["query"],
                },
                annotations=types.ToolAnnotations(readOnlyHint=True),
            ),
        ]


@rate_limit(60, 60)
@server.call_tool()
@with_security_monitoring()
@with_rate_limiting(max_requests=100, window_seconds=300)  # 100 requests per 5 minutes
@with_request_validation()
async def handle_call_tool(
    name: str, arguments: dict
) -> list[types.TextContent] | types.CallToolResult:
    """Handle the call_tool capability using the new tool handler system.

    Args:
        name: The name of the tool to call
        arguments: The arguments to pass to the tool

    Returns:
        The result of the tool call

    """
    if not isinstance(arguments, dict):
        raise ValidationError(
            "Invalid arguments: expected an object", subcategory="type"
        )
    from .cache_utils import get_cache_or_create_minimal
    from .tool_handlers import ToolHandlerRegistry

    logger.info(f"Tool call: {name} (args_count={len(arguments)})")
    logger.debug(
        f"Tool call {name} arguments: "
        f"{json.dumps(sanitize_arguments_for_logging(arguments))}"
    )

    # Record tool call for performance monitoring
    record_tool_call(name)

    try:
        # Record API call
        record_api_call("get_simplenote_client", success=True)
        api_start_time = time.time()
        sn = get_simplenote_client()
        record_response_time("get_simplenote_client", time.time() - api_start_time)

        # Ensure cache is available using utility function
        global note_cache
        note_cache = get_cache_or_create_minimal(note_cache, get_simplenote_client)

        # If cache wasn't initialized, start background initialization
        if not note_cache.is_initialized:
            asyncio.create_task(initialize_cache())

        # Enforce write-mode gate and write budget before dispatch.
        if name in WRITE_TOOLS:
            config = get_config()
            if not config.write_mode:
                error = ValidationError(
                    f"Tool '{name}' requires write mode. "
                    "Set SIMPLENOTE_WRITE_MODE=true to enable write operations.",
                    subcategory="write_mode_disabled",
                )
                return types.CallToolResult(
                    content=[
                        types.TextContent(type="text", text=json.dumps(error.to_dict()))
                    ],
                    isError=True,
                )
            _check_write_budget()

        # Get handler from registry
        registry = ToolHandlerRegistry()
        handler = registry.get_handler(name, sn, note_cache)

        if handler is None:
            error_msg = UNKNOWN_TOOL_ERROR.format(name=name)
            logger.error(error_msg)
            error = ValidationError(error_msg)
            return types.CallToolResult(
                content=[
                    types.TextContent(type="text", text=json.dumps(error.to_dict()))
                ],
                isError=True,
            )

        # Execute the tool handler and record the write only if it succeeded —
        # a handler-level failure (isError=True) must not consume write budget.
        result = await handler.handle(arguments)
        if name in WRITE_TOOLS:
            is_error = isinstance(result, types.CallToolResult) and result.isError
            if not is_error:
                _record_write()
        return result

    except Exception as e:
        if isinstance(e, ServerError):
            error_dict = e.to_dict()
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(error_dict))],
                isError=True,
            )

        logger.error(f"Error in tool call: {str(e)}", exc_info=True)
        error = handle_exception(e, f"calling tool {name}")
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(error.to_dict()))],
            isError=True,
        )


# ===== PROMPT CAPABILITIES =====


@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """Handle the list_prompts capability.

    Returns:
        List of available prompts

    """
    logger.debug("Listing available prompts")

    return [
        types.Prompt(
            name="create_note_prompt",
            description="Create a new note with content",
            arguments=[
                types.PromptArgument(
                    name="content",
                    description="The content of the note",
                    required=True,
                ),
                types.PromptArgument(
                    name="tags",
                    description="Tags for the note (comma-separated)",
                    required=False,
                ),
            ],
        ),
        types.Prompt(
            name="search_notes_prompt",
            description="Search for notes matching a query",
            arguments=[
                types.PromptArgument(
                    name="query", description="The search query", required=True
                )
            ],
        ),
        types.Prompt(
            name="session_handoff_prompt",
            description=(
                "Scaffold a session handoff note so the next Claude session can pick "
                "up where this one left off. Uses get_or_create_note + add_text to "
                "append a structured, timestamped entry to a per-project note — "
                "Simplenote MCP's Session Continuity workflow."
            ),
            arguments=[
                types.PromptArgument(
                    name="project",
                    description="Project or topic name — becomes part of the note title",
                    required=True,
                ),
                types.PromptArgument(
                    name="status",
                    description="What was done / current state this session",
                    required=False,
                ),
                types.PromptArgument(
                    name="next_steps",
                    description="What to do at the start of the next session",
                    required=False,
                ),
                types.PromptArgument(
                    name="blockers",
                    description="Anything blocking progress (default: none)",
                    required=False,
                ),
            ],
        ),
    ]


@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    """Handle the get_prompt capability.

    Args:
        name: The name of the prompt to get
        arguments: The arguments to pass to the prompt

    Returns:
        The prompt result

    Raises:
        ValidationError: If the prompt name is unknown

    """
    logger.debug(f"Getting prompt: {name} with arguments: {arguments}")

    if not arguments:
        arguments = {}

    if name == "create_note_prompt":
        content = arguments.get("content", "")
        tags = arguments.get("tags", "")

        return types.GetPromptResult(
            description="Create a new note in Simplenote",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text="You are creating a new note in Simplenote.",
                    ),
                ),
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Please create a new note with the following content:\n\n{content}\n\nTags: {tags}",
                    ),
                ),
            ],
        )

    elif name == "search_notes_prompt":
        query = arguments.get("query", "")

        return types.GetPromptResult(
            description="Search for notes in Simplenote",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text="You are searching for notes in Simplenote.",
                    ),
                ),
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Please search for notes matching the query: {query}",
                    ),
                ),
            ],
        )

    elif name == "session_handoff_prompt":
        project = arguments.get("project", "")
        status = arguments.get("status", "") or "<what was done / current state>"
        next_steps = arguments.get("next_steps", "") or "<what to do next session>"
        blockers = arguments.get("blockers", "") or "none"

        return types.GetPromptResult(
            description="Write a session handoff note for cross-session continuity",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=(
                            "You are ending a working session and writing a handoff "
                            "note so a future Claude session can pick up where this "
                            "one left off. This is Simplenote MCP's Session "
                            "Continuity workflow: find or create a per-project note, "
                            "then append a timestamped entry."
                        ),
                    ),
                ),
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=(
                            f'1. Call get_or_create_note with title="Project: '
                            f'{project}" and tags=["project-active"] to find or '
                            f"create the project's state note.\n"
                            f'2. Call add_text on that note (position="end") with '
                            f"an entry in this format:\n\n"
                            f"Status: {status}\n"
                            f"Next: {next_steps}\n"
                            f"Blockers: {blockers}\n\n"
                            "Keep each field to one or two sentences — this note is "
                            "read at the start of the next session, not a full log."
                        ),
                    ),
                ),
            ],
        )

    else:
        error_msg = UNKNOWN_PROMPT_ERROR.format(name=name)
        logger.error(error_msg)
        raise ValidationError(error_msg, subcategory="unknown_prompt")


async def _start_server_components() -> None:
    """Start server monitoring and cache initialization.

    This function completes quickly and doesn't block on cache loading.
    """
    logger.info("Starting performance monitoring")
    config = get_config()
    start_metrics_collection(interval=config.metrics_collection_interval)

    # Start log pattern monitoring for suspicious activities
    try:
        from .log_monitor import start_log_monitoring

        start_log_monitoring()
        logger.info("Started log pattern monitoring for security alerts")
    except Exception as e:
        logger.error(f"Failed to start log pattern monitoring: {e}")

    # Start HTTP health/metrics endpoints if enabled
    try:
        from .http_endpoints import set_component_ready, start_http_endpoints

        start_http_endpoints()
        # Mark core server components as ready
        set_component_ready("mcp_server", True)
        set_component_ready("metrics_collection", True)
    except Exception as e:
        logger.error(f"Failed to start HTTP endpoints: {e}")

    # Start cache initialization - this is now truly non-blocking
    # It creates an empty cache immediately and populates it in background
    try:
        await initialize_cache()
        logger.info("Cache initialization started (loading notes in background)")
    except Exception as e:
        logger.error(f"Failed to start cache initialization: {e}", exc_info=True)
        # Continue anyway - server can still start with empty cache


def _get_server_capabilities() -> Any:
    """Get and log server capabilities."""
    capabilities = server.get_capabilities(
        notification_options=NotificationOptions(),
        experimental_capabilities={},
    )
    capabilities_json = json.dumps(
        {
            "has_prompts": bool(capabilities.prompts),
            "has_resources": bool(capabilities.resources),
            "has_tools": bool(capabilities.tools),
        }
    )
    logger.info(f"Server capabilities: {capabilities_json}")
    return capabilities


async def _create_shutdown_monitor() -> asyncio.Future:
    """Create shutdown monitoring task."""
    global shutdown_requested
    shutdown_future = asyncio.get_running_loop().create_future()

    async def monitor_shutdown() -> None:
        while not shutdown_requested:
            await asyncio.sleep(0.1)
        logger.info("Shutdown requested, stopping server gracefully")
        shutdown_future.set_result(None)

    asyncio.create_task(monitor_shutdown())
    return shutdown_future


async def _run_server_task(
    read_stream: Any, write_stream: Any, capabilities: Any
) -> asyncio.Task:
    """Create and start server task."""
    from simplenote_mcp import __version__ as version

    return asyncio.create_task(
        server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="simplenote-mcp-server",
                server_version=version,
                capabilities=capabilities,
            ),
        )
    )


async def _handle_server_completion(
    server_task: asyncio.Task, done: set, pending: set
) -> None:
    """Handle server task completion."""
    # Cancel any pending tasks
    for task in pending:
        task.cancel()

    # Check server task result
    if server_task in done:
        try:
            await server_task
            logger.info("MCP server run completed normally")
        except Exception as e:
            logger.error(f"MCP server run failed: {str(e)}", exc_info=True)
            raise
    else:
        logger.info("MCP server run cancelled due to shutdown request")


async def _stop_background_sync() -> None:
    """Stop background sync gracefully."""
    global background_sync
    if background_sync is not None:
        logger.info("Stopping background sync")
        try:
            # This function is always called from an async context, so await directly.
            asyncio.get_running_loop().create_task(background_sync.stop())
            await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Error stopping background sync: {str(e)}", exc_info=True)


async def run() -> None:
    """Run the server using STDIO transport."""
    import time as time_module

    startup_start = time_module.time()
    logger.info("Starting MCP server STDIO transport")

    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            logger.info("STDIO server created, initializing MCP server")

            try:
                # Start server components (non-blocking)
                components_start = time_module.time()
                await _start_server_components()
                components_time = time_module.time() - components_start
                logger.info(f"Server components started in {components_time:.2f}s")

                # Get server capabilities
                capabilities = _get_server_capabilities()

                # Log total startup time
                startup_time = time_module.time() - startup_start
                logger.info(
                    f"MCP server ready in {startup_time:.2f}s (cache loading in background)"
                )

                # Create shutdown monitoring
                shutdown_future = await _create_shutdown_monitor()

                # Start server task
                server_task = await _run_server_task(
                    read_stream, write_stream, capabilities
                )

                # Wait for completion or shutdown
                done, pending = await asyncio.wait(
                    [server_task, shutdown_future], return_when=asyncio.FIRST_COMPLETED
                )

                # Handle completion
                await _handle_server_completion(server_task, done, pending)

            except Exception as e:
                logger.error(f"Error running MCP server: {str(e)}", exc_info=True)
                raise

    except Exception as e:
        logger.error(f"Error creating STDIO server: {str(e)}", exc_info=True)
        raise

    finally:
        await _stop_background_sync()


def _is_loopback_host(host: str) -> bool:
    """Return True if host is a loopback address (127.0.0.1, localhost, ::1)."""
    return host in ("127.0.0.1", "localhost", "::1")


def _bearer_token_valid(scope: Any, expected_token: str) -> bool:
    """Check the ASGI scope's Authorization header against expected_token.

    Uses constant-time comparison to avoid leaking token length/prefix via
    timing. `scope["headers"]` is a list of (name, value) byte-string pairs
    per the ASGI spec.
    """
    headers = dict(scope.get("headers") or [])
    raw = headers.get(b"authorization", b"").decode("latin-1")
    if not raw.startswith("Bearer "):
        return False
    return hmac.compare_digest(raw[len("Bearer ") :], expected_token)


def _build_http_security_settings(config: Any, host: str) -> TransportSecuritySettings:
    """Build TransportSecuritySettings for the MCP HTTP transport.

    Omitting security_settings entirely leaves DNS-rebinding protection off
    (the SDK's own default). We always pass an explicit value: a safe
    zero-config allowlist for loopback binds, the configured allowlist for
    anything else, or — only if the operator hasn't configured one — a
    logged, explicit opt-out rather than a silent one.
    """
    if config.mcp_http_allowed_hosts:
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=config.mcp_http_allowed_hosts,
            allowed_origins=config.mcp_http_allowed_origins,
        )
    if _is_loopback_host(host):
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=["127.0.0.1:*", "localhost:*"],
            allowed_origins=config.mcp_http_allowed_origins,
        )
    logger.warning(
        "DNS rebinding protection disabled — set MCP_HTTP_ALLOWED_HOSTS to "
        "enable it for non-loopback binds."
    )
    return TransportSecuritySettings(enable_dns_rebinding_protection=False)


async def run_http(host: str, port: int, path: str) -> None:
    """Run the server using streamable HTTP transport."""
    import time as time_module

    import uvicorn
    from starlette.responses import PlainTextResponse

    config = get_config()

    if not _is_loopback_host(host) and not config.mcp_http_auth_token:
        raise ConfigurationError(
            f"Refusing to start MCP_TRANSPORT=http on non-loopback host "
            f"{host!r} without MCP_HTTP_AUTH_TOKEN set. Set a bearer token, "
            "or bind MCP_HTTP_HOST to 127.0.0.1/localhost for same-host-only "
            "access.",
            subcategory="http_auth_required",
        )

    startup_start = time_module.time()
    normalized_path = path if path.startswith("/") else f"/{path}"
    logger.info(
        f"Starting MCP server HTTP transport on http://{host}:{port}{normalized_path}"
    )

    security_settings = _build_http_security_settings(config, host)
    transport = mcp.server.streamable_http.StreamableHTTPServerTransport(
        mcp_session_id=None, security_settings=security_settings
    )

    try:
        async with transport.connect() as (read_stream, write_stream):
            # Start server components (non-blocking)
            components_start = time_module.time()
            await _start_server_components()
            components_time = time_module.time() - components_start
            logger.info(f"Server components started in {components_time:.2f}s")

            capabilities = _get_server_capabilities()

            startup_time = time_module.time() - startup_start
            logger.info(
                f"MCP server ready in {startup_time:.2f}s (cache loading in background)"
            )

            shutdown_future = await _create_shutdown_monitor()
            server_task = await _run_server_task(
                read_stream, write_stream, capabilities
            )

            async def app(scope: Any, receive: Any, send: Any) -> None:
                if scope.get("type") != "http":
                    response = PlainTextResponse(
                        "Unsupported scope type", status_code=500
                    )
                    await response(scope, receive, send)
                    return

                request_path = cast(str, scope.get("path", ""))
                if request_path != normalized_path:
                    response = PlainTextResponse("Not Found", status_code=404)
                    await response(scope, receive, send)
                    return

                if config.mcp_http_auth_token and not _bearer_token_valid(
                    scope, config.mcp_http_auth_token
                ):
                    response = PlainTextResponse(
                        "Unauthorized",
                        status_code=401,
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                    await response(scope, receive, send)
                    return

                await transport.handle_request(scope, receive, send)

            uvicorn_config = uvicorn.Config(
                app=app, host=host, port=port, log_level="info"
            )
            uvicorn_server = uvicorn.Server(uvicorn_config)
            http_task = asyncio.create_task(uvicorn_server.serve())

            done, pending = await asyncio.wait(
                [server_task, shutdown_future, http_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            if shutdown_future in done:
                logger.info("Shutdown requested, stopping HTTP server")
                uvicorn_server.should_exit = True
                # Allow uvicorn to shut down gracefully
                if http_task in pending:
                    try:
                        await asyncio.wait_for(http_task, timeout=10.0)
                        pending.discard(http_task)
                    except asyncio.TimeoutError:
                        logger.warning("HTTP server did not shut down in time")

            if server_task in done:
                await _handle_server_completion(server_task, done, pending)

            if http_task in done:
                try:
                    await http_task
                    logger.info("HTTP transport server stopped")
                except Exception as e:
                    logger.error(
                        f"HTTP transport server failed: {str(e)}", exc_info=True
                    )
                    raise

            for task in pending:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    except Exception as e:
        logger.error(f"Error creating HTTP server: {str(e)}", exc_info=True)
        raise

    finally:
        await _stop_background_sync()


def run_main() -> None:
    """Entry point for the console script."""
    try:
        # Import the version
        from simplenote_mcp import __version__

        # Configure logging from environment variables
        config = get_config()

        # Add debug information for environment variables to a safe debug file
        from .logging import debug_to_file

        if config.log_level == LogLevel.DEBUG:
            # Sensitive keys that should always be masked
            sensitive_patterns = ("PASSWORD", "SECRET", "TOKEN", "KEY", "CREDENTIAL")
            for key, value in os.environ.items():
                if key.startswith("LOG_") or key.startswith("SIMPLENOTE_"):
                    # Mask all SIMPLENOTE_* values except non-sensitive config like EMAIL
                    should_mask = key.startswith("SIMPLENOTE_") and key not in (
                        "SIMPLENOTE_EMAIL",
                        "SIMPLENOTE_USERNAME",
                        "SIMPLENOTE_OFFLINE_MODE",
                    )
                    # Also mask if key contains sensitive patterns
                    should_mask = should_mask or any(
                        p in key.upper() for p in sensitive_patterns
                    )
                    masked_value = "*****" if should_mask else value
                    debug_to_file(f"Environment variable found: {key}={masked_value}")

        logger.info(f"Starting Simplenote MCP Server v{__version__}")
        logger.debug("This is a DEBUG level message to test logging")
        logger.info(f"Python version: {sys.version}")

        # Handle email masking safely
        email_display = "Not set"
        if config.simplenote_email:
            email_display = f"{config.simplenote_email[:3]}***"

        logger.info(
            f"Environment: SIMPLENOTE_EMAIL={email_display} (set: {config.simplenote_email is not None}), "
            f"SIMPLENOTE_PASSWORD={'*****' if config.simplenote_password else 'Not set'}"
        )
        logger.info(f"Running from: {os.path.dirname(os.path.abspath(__file__))}")
        logger.info(f"Sync interval: {config.sync_interval_seconds}s")
        logger.info(f"Log level: {config.log_level.value}")
        logger.debug(
            "Debug logging is ENABLED - this message should appear if log level is DEBUG"
        )

        # Set up process management
        setup_signal_handlers()
        write_pid_file()
        logger.info("Process management initialized")

        # Run the async event loop with graceful shutdown support
        try:
            # Update cache metrics
            if note_cache:
                config = get_config()
                max_size = getattr(note_cache, "_max_size", config.cache_max_size)
                update_cache_size(len(note_cache._notes), max_size)
            if config.mcp_transport == "http":
                asyncio.run(
                    run_http(
                        host=config.mcp_http_host,
                        port=config.mcp_http_port,
                        path=config.mcp_http_path,
                    )
                )
            else:
                asyncio.run(run())
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully - signal handler will set shutdown_requested flag
            logger.info("KeyboardInterrupt received, shutting down gracefully")
        except SystemExit:
            # Normal system exit, handle it gracefully
            logger.info("System exit requested, shutting down gracefully")

    except Exception as e:
        if not isinstance(e, SystemExit):  # Don't log normal exits as errors
            logger.critical(f"Critical error in MCP server: {str(e)}", exc_info=True)
            cleanup_pid_file()  # Ensure PID file is cleaned up even on error
            sys.exit(1)
        else:
            # Normal exit, just ensure PID file is cleaned up
            cleanup_pid_file()
            raise  # Re-raise to preserve exit code


if __name__ == "__main__":
    run_main()
