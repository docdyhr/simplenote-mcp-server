"""Main Simplenote MCP server implementation."""

# Import standard libraries
import asyncio
import atexit
import json
import os
import signal
import sys
import tempfile
import threading
import time
from contextlib import suppress
from typing import Any, cast

# Import and apply MCP patch before importing Server
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
import mcp_patch  # type: ignore  # noqa: E402

mcp_patch.apply_patch()

import mcp.server.stdio  # type: ignore  # noqa: E402
import mcp.types as types  # type: ignore  # noqa: E402
from mcp.server import NotificationOptions, Server  # type: ignore  # noqa: E402
from mcp.server.models import InitializationOptions  # type: ignore  # noqa: E402

# External imports
from pydantic import AnyUrl  # type: ignore  # noqa: E402
from simplenote import Simplenote  # type: ignore  # noqa: E402

from .cache import BackgroundSync, NoteCache  # noqa: E402

# Use our compatibility module for cross-version support
from .compat import Path  # noqa: E402
from .config import LogLevel, get_config  # noqa: E402
from .errors import (  # noqa: E402
    AuthenticationError,
    ResourceNotFoundError,
    ServerError,
    ValidationError,
    handle_exception,
)
from .logging import logger  # noqa: E402
from .monitoring.metrics import (  # noqa: E402
    record_api_call,
    record_response_time,
    record_tool_call,
    start_metrics_collection,
    update_cache_size,
)


def extract_title_from_content(content: str, fallback: str = "") -> str:
    """Extract the first non-empty line from content as title, limited to 30 chars.

    Args:
        content: The note content
        fallback: Fallback value if no non-empty line found

    Returns:
        First non-empty line (up to 30 chars) or fallback
    """
    if not content:
        return fallback

    lines = content.splitlines()
    for line in lines:
        stripped_line = line.strip()
        if stripped_line:
            return stripped_line[:30]

    return fallback


# Utility functions for safe access to potentially exception objects
def safe_get(obj: Any, key: str, default: Any = None) -> Any:
    """Safely get a value from an object that might be a dict or an exception."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    if hasattr(obj, "get"):
        with suppress(Exception):
            return obj.get(key, default)
    if hasattr(obj, "__getitem__"):
        with suppress(Exception):
            return obj[key]
    return default


def safe_set(obj: Any, key: str, value: Any) -> None:
    """Safely set a value on an object that might be a dict or an exception."""
    if obj is None:
        return
    if isinstance(obj, dict):
        obj[key] = value
        return
    if hasattr(obj, "__setitem__"):
        with suppress(Exception):
            obj[key] = value
    return


def safe_split(obj: Any, delimiter: str = ",") -> list[str]:
    """Safely split a string or return empty list for other types."""
    if isinstance(obj, str):
        return obj.split(delimiter)
    elif isinstance(obj, list):
        return [str(x) for x in obj]
    else:
        return []


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


# PID file for process management
PID_FILE_PATH = Path(tempfile.gettempdir()) / "simplenote_mcp_server.pid"
# Use same temp directory for consistency
ALT_PID_FILE_PATH = Path(tempfile.gettempdir()) / "simplenote_mcp_server_alt.pid"

# Initialize note cache and background sync
note_cache: NoteCache | None = None
background_sync: BackgroundSync | None = None


def write_pid_file() -> None:
    """Write PID to file for process management."""
    try:
        pid = os.getpid()
        PID_FILE_PATH.write_text(str(pid))

        # Also write to the alternative location in /tmp for compatibility
        try:
            ALT_PID_FILE_PATH.write_text(str(pid))
            logger.info(f"PID {pid} written to {PID_FILE_PATH} and {ALT_PID_FILE_PATH}")
        except Exception:
            logger.info(f"PID {pid} written to {PID_FILE_PATH}")
    except Exception as e:
        logger.error(f"Error writing PID file: {str(e)}", exc_info=True)


def cleanup_pid_file() -> None:
    """Remove PID file on exit."""
    try:
        if PID_FILE_PATH.exists():
            PID_FILE_PATH.unlink()

        # Also remove the alternative PID file if it exists
        if ALT_PID_FILE_PATH.exists():
            ALT_PID_FILE_PATH.unlink()
    except Exception:
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
    """Test Simplenote API connection."""
    logger.debug("Testing Simplenote client connection...")
    try:
        test_notes, status = sn.get_note_list()
        if status == 0:
            logger.debug(
                f"Simplenote API connection successful, received {len(test_notes) if isinstance(test_notes, list) else 'data'} items"
            )
        else:
            logger.error(f"Simplenote API connection test failed with status {status}")
    except Exception as e:
        logger.error(f"Simplenote API connection test failed: {str(e)}", exc_info=True)


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
    """Populate cache directly with API call."""
    try:
        logger.debug("Attempting direct API call to get notes...")
        all_notes, status = sn.get_note_list()
        if status == 0 and isinstance(all_notes, list) and all_notes:
            # Success! Update the cache directly
            try:
                await cache._lock.acquire()
                for note in all_notes:
                    note_id = note.get("key")
                    if note_id:
                        cache._notes[note_id] = note
                        if "tags" in note and note["tags"]:
                            cache._tags.update(note["tags"])
            finally:
                cache._lock.release()
            logger.info(f"Direct API load successful, loaded {len(all_notes)} notes")
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
    """Initialize the note cache and start background sync."""
    global note_cache, background_sync
    logger.debug("Initializing note cache")

    try:
        logger.info("Initializing note cache")

        # Get and test Simplenote client
        sn = get_simplenote_client()
        await _test_simplenote_connection(sn)

        # Create minimal cache if needed
        if note_cache is None:
            note_cache = await _create_minimal_cache(sn)

        # Start background sync
        if background_sync is None:
            background_sync = BackgroundSync(note_cache)
            await background_sync.start()

        # Start background initialization
        config = get_config()
        asyncio.create_task(
            _background_cache_initialization(
                note_cache, sn, config.cache_initialization_timeout
            )
        )

    except Exception as e:
        if isinstance(e, ServerError):
            raise
        logger.error(f"Error initializing cache: {str(e)}", exc_info=True)
        error = handle_exception(e, "initializing cache")
        raise error from e


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
        for note in notes:
            note.setdefault("tags", [])
            tags = note["tags"]
            content = note.get("content", "")
            resource = types.Resource(
                uri=cast(Any, f"simplenote://note/{note['key']}"),
                name=extract_title_from_content(content, note.get("key", "")),
                description=f"Note from {note.get('modifydate', 'unknown date')}",
            )
            # Store additional metadata as dynamic attributes (ignore type checking)
            resource.key = note.get("key")  # type: ignore
            resource.content = content  # type: ignore
            resource.tags = tags  # type: ignore
            resources.append(resource)

        # Note: Pagination info is available in pagination_info variable
        # but cannot be attached to Resource objects directly

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
async def handle_read_resource(uri: AnyUrl) -> types.ReadResourceResult:
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
        invalid_uri_msg = f"Invalid Simplenote URI: {uri_str}"
        raise ValidationError(invalid_uri_msg)

    note_id = uri_str.replace("simplenote://note/", "")
    note_uri = f"simplenote://note/{note_id}"

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
        safe_get(note, "tags", [])
        safe_get(note, "modifydate", "")
        safe_get(note, "createdate", "")

        # Create the resource contents object
        text_contents = types.TextResourceContents(
            text=note_content,
            uri=cast(Any, note_uri),
        )

        # Note: Metadata like tags, dates available in local variables
        # but cannot be attached to TextResourceContents objects directly

        return types.ReadResourceResult(contents=[text_contents])

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
    try:
        logger.info("Listing available tools")
        tools = [
            types.Tool(
                name="create_note",
                description="Create a new note in Simplenote",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The content of the note",
                        },
                        "tags": {
                            "type": "string",
                            "description": "Tags for the note (comma-separated)",
                        },
                    },
                    "required": ["content"],
                },
            ),
            types.Tool(
                name="update_note",
                description="Update an existing note in Simplenote",
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
                            "type": "string",
                            "description": "Tags for the note (comma-separated)",
                        },
                    },
                    "required": ["note_id", "content"],
                },
            ),
            types.Tool(
                name="delete_note",
                description="Delete a note from Simplenote",
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
            ),
            types.Tool(
                name="search_notes",
                description="Search for notes in Simplenote with advanced capabilities",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query (supports boolean operators AND, OR, NOT; phrase matching with quotes; tag filters like tag:work; date filters like from:2023-01-01 to:2023-12-31)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                        },
                        "tags": {
                            "type": "string",
                            "description": "Tags to filter by (comma-separated list of tags that must all be present). Use 'untagged' to find notes without tags.",
                        },
                        "from_date": {
                            "type": "string",
                            "description": "Filter notes modified after this date (ISO format, e.g., 2023-01-01)",
                        },
                        "to_date": {
                            "type": "string",
                            "description": "Filter notes modified before this date (ISO format, e.g., 2023-12-31)",
                        },
                    },
                    "required": ["query"],
                },
            ),
            types.Tool(
                name="get_note",
                description="Get a note by ID from Simplenote",
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
            ),
            types.Tool(
                name="add_tags",
                description="Add tags to an existing note",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to modify",
                        },
                        "tags": {
                            "type": "string",
                            "description": "Tags to add (comma-separated)",
                        },
                    },
                    "required": ["note_id", "tags"],
                },
            ),
            types.Tool(
                name="remove_tags",
                description="Remove tags from an existing note",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to modify",
                        },
                        "tags": {
                            "type": "string",
                            "description": "Tags to remove (comma-separated)",
                        },
                    },
                    "required": ["note_id", "tags"],
                },
            ),
            types.Tool(
                name="replace_tags",
                description="Replace all tags on an existing note",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to modify",
                        },
                        "tags": {
                            "type": "string",
                            "description": "New tags (comma-separated)",
                        },
                    },
                    "required": ["note_id", "tags"],
                },
            ),
        ]
        logger.info(
            f"Returning {len(tools)} tools: {', '.join([t.name for t in tools])}"
        )
        return tools

    except Exception as e:
        logger.error(f"Error listing tools: {str(e)}", exc_info=True)
        # Return at least the core tools to prevent errors
        return [
            types.Tool(
                name="create_note",
                description="Create a new note in Simplenote",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The content of the note",
                        }
                    },
                    "required": ["content"],
                },
            ),
            types.Tool(
                name="search_notes",
                description="Search for notes in Simplenote with advanced capabilities",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query (supports boolean operators AND, OR, NOT; phrase matching with quotes; tag filters like tag:work; date filters like from:2023-01-01 to:2023-12-31)",
                        },
                        "tags": {
                            "type": "string",
                            "description": "Tags to filter by (comma-separated list of tags that must all be present). Use 'untagged' to find notes without tags.",
                        },
                    },
                    "required": ["query"],
                },
            ),
        ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle the call_tool capability using the new tool handler system.

    Args:
        name: The name of the tool to call
        arguments: The arguments to pass to the tool

    Returns:
        The result of the tool call

    """
    from .cache_utils import get_cache_or_create_minimal
    from .tool_handlers import ToolHandlerRegistry

    logger.info(f"Tool call: {name} with arguments: {json.dumps(arguments)}")

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

        # Get handler from registry
        registry = ToolHandlerRegistry()
        handler = registry.get_handler(name, sn, note_cache)

        if handler is None:
            error_msg = UNKNOWN_TOOL_ERROR.format(name=name)
            logger.error(error_msg)
            error = ValidationError(error_msg)
            return [types.TextContent(type="text", text=json.dumps(error.to_dict()))]

        # Execute the tool handler
        return await handler.handle(arguments)

    except Exception as e:
        if isinstance(e, ServerError):
            error_dict = e.to_dict()
            return [types.TextContent(type="text", text=json.dumps(error_dict))]

        logger.error(f"Error in tool call: {str(e)}", exc_info=True)
        error = handle_exception(e, f"calling tool {name}")
        return [types.TextContent(type="text", text=json.dumps(error.to_dict()))]


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

    else:
        error_msg = UNKNOWN_PROMPT_ERROR.format(name=name)
        logger.error(error_msg)
        raise ValidationError(error_msg)


async def _start_server_components() -> None:
    """Start server monitoring and cache initialization."""
    logger.info("Starting performance monitoring")
    config = get_config()
    start_metrics_collection(interval=config.metrics_collection_interval)

    # Start cache initialization in background but don't wait
    asyncio.create_task(initialize_cache())
    logger.info("Started cache initialization in background")


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
            # Create a temporary event loop if necessary
            if not asyncio.get_event_loop().is_running():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(background_sync.stop())
                if "start_time" in locals():
                    loop.close()
            else:
                # Use the existing event loop
                stop_task = asyncio.get_event_loop().create_task(background_sync.stop())
                # Give it a moment to complete (use asyncio.sleep in async context)
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Error stopping background sync: {str(e)}", exc_info=True)


async def run() -> None:
    """Run the server using STDIO transport."""
    logger.info("Starting MCP server STDIO transport")

    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            logger.info("STDIO server created, initializing MCP server")

            try:
                # Start server components
                await _start_server_components()

                # Get server capabilities
                capabilities = _get_server_capabilities()

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
            for key, value in os.environ.items():
                if key.startswith("LOG_") or key.startswith("SIMPLENOTE_"):
                    masked_value = value if "PASSWORD" not in key else "*****"
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
