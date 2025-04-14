# simplenote_mcp/server/server.py

import asyncio
import atexit
import contextlib
import json
import os
import signal
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

import mcp.server.stdio  # type: ignore
import mcp.types as types  # type: ignore

# Direct import from the Python package for additional API functions
from mcp.server import NotificationOptions, Server  # type: ignore # noqa
from mcp.server.models import InitializationOptions  # type: ignore
from simplenote import Simplenote  # type: ignore

from .cache import BackgroundSync, NoteCache
from .config import LogLevel, get_config
from .errors import (
    AuthenticationError,
    NetworkError,
    ResourceNotFoundError,
    ServerError,
    ValidationError,
    handle_exception,
)
from .logging import logger

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
    logger.error(f"Error creating server instance: {str(e)}", exc_info=True)
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
ALT_PID_FILE_PATH = Path("/tmp/simplenote_mcp_server.pid")

# Initialize note cache and background sync
note_cache: Optional[NoteCache] = None
background_sync: Optional[BackgroundSync] = None


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
            logger.info(f"Removed PID file: {PID_FILE_PATH}")

        # Also remove the alternative PID file if it exists
        if ALT_PID_FILE_PATH.exists():
            ALT_PID_FILE_PATH.unlink()
            logger.info(f"Removed PID file: {ALT_PID_FILE_PATH}")
    except Exception as e:
        logger.error(f"Error removing PID file: {str(e)}", exc_info=True)


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


async def initialize_cache() -> None:
    """Initialize the note cache and start background sync."""
    global note_cache, background_sync, shutdown_requested

    try:
        logger.info("Initializing note cache")

        # Test the Simplenote client to make sure it works
        sn = get_simplenote_client()
        logger.debug("Testing Simplenote client connection...")

        # Try a simple API call to validate connection
        try:
            # Get note list to validate connection (no limit parameter in this API)
            test_notes, status = sn.get_note_list()
            if status == 0:
                logger.debug(
                    f"Simplenote API connection successful, received {len(test_notes) if isinstance(test_notes, list) else 'data'} items"
                )
            else:
                logger.error(
                    f"Simplenote API connection test failed with status {status}"
                )
        except Exception as e:
            logger.error(
                f"Simplenote API connection test failed: {str(e)}", exc_info=True
            )

        # Create a minimal cache immediately so we can respond to clients
        if note_cache is None:
            note_cache = NoteCache(sn)
            note_cache._initialized = True
            note_cache._notes = {}
            note_cache._last_sync = time.time()
            note_cache._tags = set()
            logger.debug(f"Created empty note cache with client: {sn}")

        # Start background sync immediately so data will start loading
        if background_sync is None:
            background_sync = BackgroundSync(note_cache)
            await background_sync.start()

        # Now actually load the data in the background without blocking
        # Initialize cache in the background with a timeout
        initialization_timeout = 60  # seconds - increased from 45

        async def background_initialization() -> None:
            try:
                # Try direct API call to get notes synchronously
                try:
                    logger.debug("Attempting direct API call to get notes...")
                    all_notes, status = sn.get_note_list()
                    if status == 0 and isinstance(all_notes, list) and all_notes:
                        # Success! Update the cache directly
                        # Using non-context lock (lock/unlock) since the lock might not be a context manager
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
                    await asyncio.wait_for(init_task, timeout=initialization_timeout)
                    logger.info(
                        f"Note cache initialization completed successfully with {len(note_cache._notes)} notes"
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        f"Note cache initialization timed out after {initialization_timeout}s, cache has {len(note_cache._notes)} notes"
                    )
                    # We already have some notes from direct API call hopefully
            except Exception as e:
                logger.error(
                    f"Error during background initialization: {str(e)}", exc_info=True
                )

        # Start background initialization but don't await it
        asyncio.create_task(background_initialization())

    except Exception as e:
        if isinstance(e, ServerError):
            raise
        logger.error(f"Error initializing cache: {str(e)}", exc_info=True)
        error = handle_exception(e, "initializing cache")
        raise error from e


# ===== RESOURCE CAPABILITIES =====


@server.list_resources()
async def handle_list_resources(
    tag: Optional[str] = None, limit: Optional[int] = None
) -> list[types.Resource]:
    """Handle the list_resources capability.

    Args:
        tag: Optional tag to filter notes by
        limit: Optional limit for the number of notes to return

    Returns:
        List of Simplenote note resources

    """
    logger.debug(f"list_resources called with tag={tag}, limit={limit}")

    try:
        # Check for cache initialization, but don't block waiting for it
        global note_cache
        if note_cache is None:
            logger.info("Cache not initialized, creating empty cache")
            # Create a minimal cache without waiting for initialization
            simplenote_client = get_simplenote_client()
            note_cache = NoteCache(simplenote_client)
            note_cache._initialized = True
            note_cache._notes = {}
            note_cache._last_sync = time.time()
            note_cache._tags = set()

            # Start initialization in the background
            asyncio.create_task(initialize_cache())

        # Use the cache to get notes with filtering
        config = get_config()

        # Use provided limit or fall back to default
        actual_limit = limit if limit is not None else config.default_resource_limit

        # Apply tag filtering if specified
        notes = note_cache.get_all_notes(limit=actual_limit, tag_filter=tag)

        logger.debug(
            f"Listing resources, found {len(notes)} notes"
            + (f" with tag '{tag}'" if tag else "")
        )

        return [
            types.Resource(
                uri=f"simplenote://note/{note['key']}",
                name=(
                    note.get("content", "").splitlines()[0][:30]
                    if note.get("content")
                    else note["key"]
                ),
                description=f"Note from {note.get('modifydate', 'unknown date')}",
                meta={"tags": note.get("tags", [])},
            )
            for note in notes
        ]

    except Exception as e:
        if isinstance(e, ServerError):
            logger.error(f"Error listing resources: {str(e)}")
        else:
            logger.error(f"Error listing resources: {str(e)}", exc_info=True)

        # Return empty list instead of raising an exception
        # to avoid breaking the client experience
        return []


@server.read_resource()
async def handle_read_resource(uri: str) -> types.ReadResourceResult:
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
    if not uri.startswith("simplenote://note/"):
        logger.error(f"Invalid Simplenote URI: {uri}")
        invalid_uri_msg = f"Invalid Simplenote URI: {uri}"
        raise ValidationError(invalid_uri_msg)

    note_id = uri.replace("simplenote://note/", "")

    try:
        # Check for cache initialization, but don't block waiting for it
        global note_cache
        if note_cache is None:
            logger.info("Cache not initialized, creating empty cache")
            # Create a minimal cache without waiting for initialization
            sn = get_simplenote_client()
            note_cache = NoteCache(sn)
            note_cache._initialized = True
            note_cache._notes = {}
            note_cache._last_sync = time.time()
            note_cache._tags = set()

            # Start initialization in the background
            asyncio.create_task(initialize_cache())

        # Try to get the note from cache first if cache is initialized
        if note_cache is not None:
            logger.debug(f"Getting note {note_id} from cache")
            try:
                note = note_cache.get_note(note_id)
                logger.debug(f"Found note {note_id} in cache")
                note_uri = f"simplenote://note/{note_id}"
                # Ensure we have a valid note object before accessing properties
                if note is None:
                    note_content = ""
                    note_tags = []
                    note_modifydate = ""
                    note_createdate = ""
                else:
                    note_content = note.get("content", "")
                    note_tags = note.get("tags", [])
                    note_modifydate = note.get("modifydate", "")
                    note_createdate = note.get("createdate", "")

                text_contents = types.TextResourceContents(
                    text=note_content,
                    uri=note_uri,
                    meta={
                        "tags": note_tags,
                        "modifydate": note_modifydate,
                        "createdate": note_createdate,
                    },
                )
                return types.ReadResourceResult(contents=[text_contents])
            except ResourceNotFoundError:
                # If not in cache, we'll try the API directly
                logger.debug(f"Note {note_id} not found in cache, trying API")
                pass

        # Get the note from Simplenote API if not found in cache
        sn = get_simplenote_client()
        note, status = sn.get_note(note_id)

        if status == 0:
            # Update the cache if it's initialized
            if note_cache is not None and note_cache.is_initialized and note:
                note_cache.update_cache_after_update(note)

            note_uri = f"simplenote://note/{note_id}"
            text_contents = types.TextResourceContents(
                text=note.get("content", "") if note else "",
                uri=note_uri,
                meta={
                    "tags": note.get("tags", []) if note else [],
                    "modifydate": note.get("modifydate", "") if note else "",
                    "createdate": note.get("createdate", "") if note else "",
                },
            )
            return types.ReadResourceResult(contents=[text_contents])
        else:
            error_msg = f"Failed to get note with ID {note_id}"
            logger.error(error_msg)
            raise ResourceNotFoundError(error_msg)

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
                            "description": "Tags to filter by (comma-separated list of tags that must all be present)",
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
                            "description": "Tags to filter by (comma-separated list of tags that must all be present)",
                        },
                    },
                    "required": ["query"],
                },
            ),
        ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle the call_tool capability.

    Args:
        name: The name of the tool to call
        arguments: The arguments to pass to the tool

    Returns:
        The result of the tool call

    """
    logger.info(f"Tool call: {name} with arguments: {json.dumps(arguments)}")

    try:
        sn = get_simplenote_client()

        # Check for cache initialization, but don't block waiting for it
        global note_cache
        if note_cache is None:
            logger.info("Cache not initialized, creating empty cache")
            # Create a minimal cache without waiting for initialization
            note_cache = NoteCache(sn)
            note_cache._initialized = True
            note_cache._notes = {}
            note_cache._last_sync = time.time()
            note_cache._tags = set()

            # Start initialization in the background
            asyncio.create_task(initialize_cache())

        if name == "create_note":
            content = arguments.get("content", "")
            tags_str = arguments.get("tags", "")
            tags = [tag.strip() for tag in tags_str.split(",")] if tags_str else []

            if not content:
                raise ValidationError(NOTE_CONTENT_REQUIRED)

            try:
                note = {"content": content}
                if tags:
                    note["tags"] = tags

                note, status = sn.add_note(note)

                if status == 0:
                    # Update the cache if it's initialized
                    if note_cache is not None and note_cache.is_initialized:
                        note_cache.update_cache_after_create(note)

                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "success": True,
                                    "message": "Note created successfully",
                                    "note_id": note.get("key"),
                                    "first_line": (
                                        content.splitlines()[0][:30] if content else ""
                                    ),
                                    "tags": tags,
                                }
                            ),
                        )
                    ]
                else:
                    error_msg = "Failed to create note"
                    logger.error(error_msg)
                    raise NetworkError(error_msg)

            except Exception as e:
                if isinstance(e, ServerError):
                    error_dict = e.to_dict()
                    return [types.TextContent(type="text", text=json.dumps(error_dict))]

                logger.error(f"Error creating note: {str(e)}", exc_info=True)
                error = handle_exception(e, "creating note")
                return [
                    types.TextContent(type="text", text=json.dumps(error.to_dict()))
                ]

        elif name == "update_note":
            note_id = arguments.get("note_id", "")
            content = arguments.get("content", "")
            tags_str = arguments.get("tags", "")

            if not note_id:
                raise ValidationError(NOTE_ID_REQUIRED)

            if not content:
                raise ValidationError(NOTE_CONTENT_REQUIRED)

            try:
                # Get the existing note first
                existing_note = None

                # Try to get from cache first
                if note_cache is not None and note_cache.is_initialized:
                    with contextlib.suppress(ResourceNotFoundError):
                        existing_note = note_cache.get_note(note_id)
                        # If not found, the API will be used

                # If not found in cache, get from API
                if existing_note is None:
                    existing_note, status = sn.get_note(note_id)
                    if status != 0:
                        error_msg = FAILED_GET_NOTE.format(note_id=note_id)
                        logger.error(error_msg)
                        raise ResourceNotFoundError(error_msg)

                # Update the note content
                existing_note["content"] = content

                # Update tags if provided
                if tags_str:
                    tags = [tag.strip() for tag in tags_str.split(",")]
                    existing_note["tags"] = tags

                updated_note, status = sn.update_note(existing_note)

                if status == 0:
                    # Update the cache if it's initialized
                    if note_cache is not None and note_cache.is_initialized:
                        note_cache.update_cache_after_update(updated_note)

                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "success": True,
                                    "message": "Note updated successfully",
                                    "note_id": updated_note.get("key"),
                                    "tags": updated_note.get("tags", []),
                                }
                            ),
                        )
                    ]
                else:
                    error_msg = "Failed to update note"
                    logger.error(error_msg)
                    raise NetworkError(error_msg)

            except Exception as e:
                if isinstance(e, ServerError):
                    error_dict = e.to_dict()
                    return [types.TextContent(type="text", text=json.dumps(error_dict))]

                logger.error(f"Error updating note: {str(e)}", exc_info=True)
                error = handle_exception(e, f"updating note {note_id}")
                return [
                    types.TextContent(type="text", text=json.dumps(error.to_dict()))
                ]

        elif name == "delete_note":
            note_id = arguments.get("note_id", "")

            if not note_id:
                raise ValidationError(NOTE_ID_REQUIRED)

            try:
                status = sn.trash_note(
                    note_id
                )  # Using trash_note as it's safer than delete_note

                if status == 0:
                    # Update the cache if it's initialized
                    if note_cache is not None and note_cache.is_initialized:
                        note_cache.update_cache_after_delete(note_id)

                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "success": True,
                                    "message": "Note moved to trash successfully",
                                    "note_id": note_id,
                                }
                            ),
                        )
                    ]
                else:
                    logger.error(FAILED_TRASH_NOTE)
                    raise NetworkError(FAILED_TRASH_NOTE)

            except Exception as e:
                if isinstance(e, ServerError):
                    error_dict = e.to_dict()
                    return [types.TextContent(type="text", text=json.dumps(error_dict))]

                logger.error(f"Error deleting note: {str(e)}", exc_info=True)
                error = handle_exception(e, f"deleting note {note_id}")
                return [
                    types.TextContent(type="text", text=json.dumps(error.to_dict()))
                ]

        elif name == "search_notes":
            query = arguments.get("query", "")
            limit = arguments.get("limit")
            tags_str = arguments.get("tags", "")
            from_date_str = arguments.get("from_date")
            to_date_str = arguments.get("to_date")

            logger.debug(
                f"Advanced search called with: query='{query}', limit={limit}, "
                + f"tags='{tags_str}', from_date='{from_date_str}', to_date='{to_date_str}'"
            )

            if not query:
                raise ValidationError(QUERY_REQUIRED)

            # Process limit parameter
            if limit is not None:
                try:
                    limit = int(limit)
                    if limit < 1:
                        limit = None
                except (ValueError, TypeError):
                    limit = None

            # Process tag filters
            tag_filters = None
            if tags_str:
                tag_filters = [
                    tag.strip() for tag in tags_str.split(",") if tag.strip()
                ]
                logger.debug(f"Tag filters: {tag_filters}")

            # Process date range
            from_date = None
            to_date = None
            date_range = None

            if from_date_str:
                try:
                    from datetime import datetime

                    from_date = datetime.fromisoformat(from_date_str)
                    logger.debug(f"From date: {from_date}")
                except ValueError:
                    logger.warning(f"Invalid from_date format: {from_date_str}")

            if to_date_str:
                try:
                    from datetime import datetime

                    to_date = datetime.fromisoformat(to_date_str)
                    logger.debug(f"To date: {to_date}")
                except ValueError:
                    logger.warning(f"Invalid to_date format: {to_date_str}")

            if from_date or to_date:
                date_range = (from_date, to_date)

            try:
                # Check cache status
                cache_initialized = note_cache is not None and note_cache.is_initialized
                logger.debug(
                    f"Cache status for search: available={note_cache is not None}, initialized={cache_initialized}"
                )

                # Use the cache for search if available
                if cache_initialized:
                    logger.debug("Using advanced search with cache")

                    # Use the enhanced search implementation
                    notes = note_cache.search_notes(
                        query=query,
                        limit=limit,
                        tag_filters=tag_filters,
                        date_range=date_range,
                    )

                    # Format results
                    results = []
                    for note in notes:
                        content = note.get("content", "")
                        results.append(
                            {
                                "id": note.get("key"),
                                "title": (
                                    content.splitlines()[0][:30]
                                    if content
                                    else note.get("key")
                                ),
                                "snippet": (
                                    content[:100] + "..."
                                    if len(content) > 100
                                    else content
                                ),
                                "tags": note.get("tags", []),
                                "uri": f"simplenote://note/{note.get('key')}",
                            }
                        )

                    # Add debug logging for troubleshooting
                    logger.debug(
                        f"Search results: {len(results)} matches found for '{query}'"
                    )

                    # Debug log the first few results if available
                    if results:
                        logger.debug(
                            f"First result title: {results[0].get('title', 'No title')}"
                        )

                    # Create response
                    response = {
                        "success": True,
                        "results": results,
                        "count": len(results),
                        "query": query,
                    }

                    # Log the response size
                    response_json = json.dumps(response)
                    logger.debug(f"Response size: {len(response_json)} bytes")

                    return [types.TextContent(type="text", text=response_json)]

                # Fall back to API if cache is not available - create a temporary search engine
                logger.debug(
                    "Cache not available, using API with temporary search engine"
                )
                from .search.engine import SearchEngine

                api_search_engine = SearchEngine()

                # Get all notes from the API
                all_notes, status = sn.get_note_list()

                if status != 0:
                    logger.error(FAILED_RETRIEVE_NOTES)
                    raise NetworkError(FAILED_RETRIEVE_NOTES)

                # Convert list to dictionary for search engine
                notes_dict = {
                    note.get("key"): note for note in all_notes if note.get("key")
                }

                logger.debug(f"API search: Got {len(notes_dict)} notes from API")

                # Use the search engine
                matching_notes = api_search_engine.search(
                    notes=notes_dict,
                    query=query,
                    tag_filters=tag_filters,
                    date_range=date_range,
                    limit=limit,
                )

                # Format results
                results = []
                for note in matching_notes:
                    content = note.get("content", "")
                    results.append(
                        {
                            "id": note.get("key"),
                            "title": content.splitlines()[0][:30]
                            if content
                            else note.get("key"),
                            "snippet": content[:100] + "..."
                            if len(content) > 100
                            else content,
                            "tags": note.get("tags", []),
                            "uri": f"simplenote://note/{note.get('key')}",
                        }
                    )

                # Debug logging
                logger.debug(
                    f"API search results: {len(results)} matches found for '{query}'"
                )
                if results:
                    logger.debug(
                        f"First API result title: {results[0].get('title', 'No title')}"
                    )

                # Create the response
                response = {
                    "success": True,
                    "results": results,
                    "count": len(results),
                    "query": query,
                }

                # Log the response size
                response_json = json.dumps(response)
                logger.debug(f"API response size: {len(response_json)} bytes")

                return [types.TextContent(type="text", text=response_json)]

            except Exception as e:
                if isinstance(e, ServerError):
                    error_dict = e.to_dict()
                    return [types.TextContent(type="text", text=json.dumps(error_dict))]

                logger.error(f"Error searching notes: {str(e)}", exc_info=True)
                error = handle_exception(e, f"searching notes for '{query}'")
                return [
                    types.TextContent(type="text", text=json.dumps(error.to_dict()))
                ]

        elif name == "get_note":
            note_id = arguments.get("note_id", "")

            if not note_id:
                raise ValidationError(NOTE_ID_REQUIRED)

            try:
                # Try to get from cache first
                note = None
                if note_cache is not None and note_cache.is_initialized:
                    with contextlib.suppress(ResourceNotFoundError):
                        note = note_cache.get_note(note_id)
                        # If not found, the API will be used

                # If not found in cache, get from API
                if note is None:
                    note, status = sn.get_note(note_id)
                    if status != 0:
                        error_msg = FAILED_GET_NOTE.format(note_id=note_id)
                        logger.error(error_msg)
                        raise ResourceNotFoundError(error_msg)

                # Prepare response
                content = note.get("content", "")
                first_line = content.splitlines()[0][:30] if content else ""

                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "note_id": note.get("key"),
                                "content": note.get("content", ""),
                                "title": first_line,
                                "tags": note.get("tags", []),
                                "createdate": note.get("createdate", ""),
                                "modifydate": note.get("modifydate", ""),
                                "uri": f"simplenote://note/{note.get('key')}",
                            }
                        ),
                    )
                ]

            except Exception as e:
                if isinstance(e, ServerError):
                    error_dict = e.to_dict()
                    return [types.TextContent(type="text", text=json.dumps(error_dict))]

                logger.error(f"Error getting note: {str(e)}", exc_info=True)
                error = handle_exception(e, f"getting note {note_id}")
                return [
                    types.TextContent(type="text", text=json.dumps(error.to_dict()))
                ]

        elif name == "add_tags":
            note_id = arguments.get("note_id", "")
            tags_str = arguments.get("tags", "")

            if not note_id:
                raise ValidationError(NOTE_ID_REQUIRED)

            if not tags_str:
                raise ValidationError(TAGS_REQUIRED)

            try:
                # Get the existing note first
                existing_note = None

                # Try to get from cache first
                if note_cache is not None and note_cache.is_initialized:
                    with contextlib.suppress(ResourceNotFoundError):
                        existing_note = note_cache.get_note(note_id)
                        # If not found, the API will be used

                # If not found in cache, get from API
                if existing_note is None:
                    existing_note, status = sn.get_note(note_id)
                    if status != 0:
                        error_msg = FAILED_GET_NOTE.format(note_id=note_id)
                        logger.error(error_msg)
                        raise ResourceNotFoundError(error_msg)

                # Parse the tags to add
                tags_to_add = [
                    tag.strip() for tag in tags_str.split(",") if tag.strip()
                ]

                # Get current tags or initialize empty list
                current_tags = existing_note.get("tags", [])
                if current_tags is None:
                    current_tags = []

                # Add new tags that aren't already present
                added_tags = []
                for tag in tags_to_add:
                    if tag not in current_tags:
                        current_tags.append(tag)
                        added_tags.append(tag)

                # Only update if tags were actually added
                if added_tags:
                    # Update the note
                    existing_note["tags"] = current_tags
                    updated_note, status = sn.update_note(existing_note)

                    if status == 0:
                        # Update the cache if it's initialized
                        if note_cache is not None and note_cache.is_initialized:
                            note_cache.update_cache_after_update(updated_note)

                        return [
                            types.TextContent(
                                type="text",
                                text=json.dumps(
                                    {
                                        "success": True,
                                        "message": f"Added tags: {', '.join(added_tags)}",
                                        "note_id": updated_note.get("key"),
                                        "tags": updated_note.get("tags", []),
                                    }
                                ),
                            )
                        ]
                    else:
                        logger.error(FAILED_UPDATE_TAGS)
                        raise NetworkError(FAILED_UPDATE_TAGS)
                else:
                    # No tags were added (all already present)
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "success": True,
                                    "message": "No new tags to add (all tags already present)",
                                    "note_id": note_id,
                                    "tags": current_tags,
                                }
                            ),
                        )
                    ]

            except Exception as e:
                if isinstance(e, ServerError):
                    error_dict = e.to_dict()
                    return [types.TextContent(type="text", text=json.dumps(error_dict))]

                logger.error(f"Error adding tags: {str(e)}", exc_info=True)
                error = handle_exception(e, f"adding tags to note {note_id}")
                return [
                    types.TextContent(type="text", text=json.dumps(error.to_dict()))
                ]

        elif name == "remove_tags":
            note_id = arguments.get("note_id", "")
            tags_str = arguments.get("tags", "")

            if not note_id:
                raise ValidationError(NOTE_ID_REQUIRED)

            if not tags_str:
                raise ValidationError(TAGS_REQUIRED)

            try:
                # Get the existing note first
                existing_note = None

                # Try to get from cache first
                if note_cache is not None and note_cache.is_initialized:
                    with contextlib.suppress(ResourceNotFoundError):
                        existing_note = note_cache.get_note(note_id)
                        # If not found, the API will be used

                # If not found in cache, get from API
                if existing_note is None:
                    existing_note, status = sn.get_note(note_id)
                    if status != 0:
                        error_msg = FAILED_GET_NOTE.format(note_id=note_id)
                        logger.error(error_msg)
                        raise ResourceNotFoundError(error_msg)

                # Parse the tags to remove
                tags_to_remove = [
                    tag.strip() for tag in tags_str.split(",") if tag.strip()
                ]

                # Get current tags or initialize empty list
                current_tags = existing_note.get("tags", [])
                if current_tags is None:
                    current_tags = []

                # If the note has no tags, nothing to do
                if not current_tags:
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "success": True,
                                    "message": "Note had no tags to remove",
                                    "note_id": note_id,
                                    "tags": [],
                                }
                            ),
                        )
                    ]

                # Remove specified tags that are present
                removed_tags = []
                new_tags = []
                for tag in current_tags:
                    if tag in tags_to_remove:
                        removed_tags.append(tag)
                    else:
                        new_tags.append(tag)

                # Only update if tags were actually removed
                if removed_tags:
                    # Update the note
                    existing_note["tags"] = new_tags
                    updated_note, status = sn.update_note(existing_note)

                    if status == 0:
                        # Update the cache if it's initialized
                        if note_cache is not None and note_cache.is_initialized:
                            note_cache.update_cache_after_update(updated_note)

                        return [
                            types.TextContent(
                                type="text",
                                text=json.dumps(
                                    {
                                        "success": True,
                                        "message": f"Removed tags: {', '.join(removed_tags)}",
                                        "note_id": updated_note.get("key"),
                                        "tags": updated_note.get("tags", []),
                                    }
                                ),
                            )
                        ]
                    else:
                        logger.error(FAILED_UPDATE_TAGS)
                        raise NetworkError(FAILED_UPDATE_TAGS)
                else:
                    # No tags were removed (none were present)
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "success": True,
                                    "message": "No tags were removed (specified tags not present on note)",
                                    "note_id": note_id,
                                    "tags": current_tags,
                                }
                            ),
                        )
                    ]

            except Exception as e:
                if isinstance(e, ServerError):
                    error_dict = e.to_dict()
                    return [types.TextContent(type="text", text=json.dumps(error_dict))]

                logger.error(f"Error removing tags: {str(e)}", exc_info=True)
                error = handle_exception(e, f"removing tags from note {note_id}")
                return [
                    types.TextContent(type="text", text=json.dumps(error.to_dict()))
                ]

        elif name == "replace_tags":
            note_id = arguments.get("note_id", "")
            tags_str = arguments.get("tags", "")

            if not note_id:
                raise ValidationError(NOTE_ID_REQUIRED)

            try:
                # Get the existing note first
                existing_note = None

                # Try to get from cache first
                if note_cache is not None and note_cache.is_initialized:
                    with contextlib.suppress(ResourceNotFoundError):
                        existing_note = note_cache.get_note(note_id)
                        # If not found, the API will be used

                # If not found in cache, get from API
                if existing_note is None:
                    existing_note, status = sn.get_note(note_id)
                    if status != 0:
                        error_msg = FAILED_GET_NOTE.format(note_id=note_id)
                        logger.error(error_msg)
                        raise ResourceNotFoundError(error_msg)

                # Parse the new tags
                new_tags = (
                    [tag.strip() for tag in tags_str.split(",") if tag.strip()]
                    if tags_str
                    else []
                )

                # Get current tags
                current_tags = existing_note.get("tags", [])
                if current_tags is None:
                    current_tags = []

                # Update the note with new tags
                existing_note["tags"] = new_tags
                updated_note, status = sn.update_note(existing_note)

                if status == 0:
                    # Update the cache if it's initialized
                    if note_cache is not None and note_cache.is_initialized:
                        note_cache.update_cache_after_update(updated_note)

                    # Generate appropriate message based on whether tags were changed
                    if set(current_tags) == set(new_tags):
                        message = "Tags unchanged (new tags same as existing tags)"
                    else:
                        message = f"Replaced tags: {', '.join(current_tags)} → {', '.join(new_tags)}"

                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "success": True,
                                    "message": message,
                                    "note_id": updated_note.get("key"),
                                    "tags": updated_note.get("tags", []),
                                }
                            ),
                        )
                    ]
                else:
                    error_msg = "Failed to update note tags"
                    logger.error(error_msg)
                    raise NetworkError(error_msg)

            except Exception as e:
                if isinstance(e, ServerError):
                    error_dict = e.to_dict()
                    return [types.TextContent(type="text", text=json.dumps(error_dict))]

                logger.error(f"Error replacing tags: {str(e)}", exc_info=True)
                error = handle_exception(e, f"replacing tags on note {note_id}")
                return [
                    types.TextContent(type="text", text=json.dumps(error.to_dict()))
                ]

        else:
            error_msg = UNKNOWN_TOOL_ERROR.format(name=name)
            logger.error(error_msg)
            error = ValidationError(error_msg)
            return [types.TextContent(type="text", text=json.dumps(error.to_dict()))]

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
    name: str, arguments: Optional[dict[str, str]]
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
                    role="system",
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
                    role="system",
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


async def run() -> None:
    """Run the server using STDIO transport."""
    global shutdown_requested
    logger.info("Starting MCP server STDIO transport")

    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            logger.info("STDIO server created, initializing MCP server")

            try:
                # Start cache initialization in background but don't wait
                asyncio.create_task(initialize_cache())

                # Log that we're continuing without waiting
                logger.info("Started cache initialization in background")

                # Get capabilities and log them
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

                # Get the server version
                from simplenote_mcp import __version__ as version

                # Create a done future that will be set when shutdown is requested
                shutdown_future = asyncio.get_running_loop().create_future()

                # Create a background task to monitor the shutdown flag
                async def monitor_shutdown() -> None:
                    while not shutdown_requested:
                        await asyncio.sleep(0.1)
                    logger.info("Shutdown requested, stopping server gracefully")
                    shutdown_future.set_result(None)

                asyncio.create_task(monitor_shutdown())

                # Run the server with an option to cancel if shutdown is requested
                server_task = asyncio.create_task(
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

                # Wait for either server completion or shutdown
                done, pending = await asyncio.wait(
                    [server_task, shutdown_future], return_when=asyncio.FIRST_COMPLETED
                )

                # Cancel any pending tasks
                for task in pending:
                    task.cancel()

                # If the server task is done, check its result
                if server_task in done:
                    try:
                        await server_task
                        logger.info("MCP server run completed normally")
                    except Exception as e:
                        logger.error(f"MCP server run failed: {str(e)}", exc_info=True)
                        raise
                else:
                    logger.info("MCP server run cancelled due to shutdown request")

            except Exception as e:
                logger.error(f"Error running MCP server: {str(e)}", exc_info=True)
                raise

    except Exception as e:
        logger.error(f"Error creating STDIO server: {str(e)}", exc_info=True)
        raise

    finally:
        # Stop the background sync when the server stops
        global background_sync
        if background_sync is not None:
            logger.info("Stopping background sync")
            try:
                # Create a temporary event loop if necessary
                if not asyncio.get_event_loop().is_running():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(background_sync.stop())
                    loop.close()
                else:
                    # Use the existing event loop
                    asyncio.get_event_loop().create_task(background_sync.stop())
                    # Give it a moment to complete
                    time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error stopping background sync: {str(e)}", exc_info=True)


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
