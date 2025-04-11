# simplenote_mcp/server/server.py

import asyncio
import atexit
import contextlib
import json
import os
import signal
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from simplenote import Simplenote

from .cache import BackgroundSync, NoteCache
from .config import get_config
from .errors import (
    AuthenticationError,
    ErrorCategory,
    NetworkError,
    ResourceNotFoundError,
    ServerError,
    ValidationError,
    handle_exception,
)
from .logging import logger

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
                raise AuthenticationError(
                    "SIMPLENOTE_EMAIL (or SIMPLENOTE_USERNAME) and SIMPLENOTE_PASSWORD environment variables must be set"
                )

            logger.info(f"Creating Simplenote client with username: {config.simplenote_email[:3]}***")
            simplenote_client = Simplenote(config.simplenote_email, config.simplenote_password)
            logger.info("Simplenote client created successfully")

        except Exception as e:
            if isinstance(e, ServerError):
                raise
            logger.error(f"Error initializing Simplenote client: {str(e)}", exc_info=True)
            error = handle_exception(e, "initializing Simplenote client")
            raise error from e

    return simplenote_client


# PID file for process management
PID_FILE_PATH = Path(tempfile.gettempdir()) / "simplenote_mcp_server.pid"

# Initialize note cache and background sync
note_cache: Optional[NoteCache] = None
background_sync: Optional[BackgroundSync] = None


def write_pid_file() -> None:
    """Write PID to file for process management."""
    try:
        pid = os.getpid()
        PID_FILE_PATH.write_text(str(pid))
        logger.info(f"PID {pid} written to {PID_FILE_PATH}")
    except Exception as e:
        logger.error(f"Error writing PID file: {str(e)}", exc_info=True)


def cleanup_pid_file() -> None:
    """Remove PID file on exit."""
    try:
        if PID_FILE_PATH.exists():
            PID_FILE_PATH.unlink()
            logger.info(f"Removed PID file: {PID_FILE_PATH}")
    except Exception as e:
        logger.error(f"Error removing PID file: {str(e)}", exc_info=True)


def setup_signal_handlers() -> None:
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(sig: int, _: object) -> None:  # Frame argument is unused but required by signal API
        """Handle termination signals."""
        signal_name = signal.Signals(sig).name
        logger.info(f"Received {signal_name} signal, shutting down...")
        # Cleanup will be handled by atexit
        sys.exit(0)

    # Register handlers for common termination signals
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Register cleanup function to run at exit
    atexit.register(cleanup_pid_file)


async def initialize_cache() -> None:
    """Initialize the note cache and start background sync."""
    global note_cache, background_sync

    try:
        logger.info("Initializing note cache")
        sn = get_simplenote_client()
        note_cache = NoteCache(sn)
        await note_cache.initialize()

        # Start background sync
        background_sync = BackgroundSync(note_cache)
        await background_sync.start()

    except Exception as e:
        if isinstance(e, ServerError):
            raise
        logger.error(f"Error initializing cache: {str(e)}", exc_info=True)
        error = handle_exception(e, "initializing cache")
        raise error from e


# ===== RESOURCE CAPABILITIES =====


@server.list_resources()
async def handle_list_resources(tag: Optional[str] = None, limit: Optional[int] = None) -> List[types.Resource]:
    """Handle the list_resources capability.

    Args:
        tag: Optional tag to filter notes by
        limit: Optional limit for the number of notes to return

    Returns:
        List of Simplenote note resources
    """
    logger.debug(f"list_resources called with tag={tag}, limit={limit}")

    try:
        # Make sure the cache is initialized
        global note_cache
        if note_cache is None or not note_cache.is_initialized:
            logger.info("Cache not initialized, initializing now")
            await initialize_cache()

        if note_cache is None:
            raise ServerError("Note cache initialization failed", category=ErrorCategory.INTERNAL)

        # Use the cache to get notes with filtering
        config = get_config()

        # Use provided limit or fall back to default
        actual_limit = limit if limit is not None else config.default_resource_limit

        # Apply tag filtering if specified
        notes = note_cache.get_all_notes(limit=actual_limit, tag_filter=tag)

        logger.debug(f"Listing resources, found {len(notes)} notes" +
                    (f" with tag '{tag}'" if tag else ""))

        return [
            types.Resource(
                uri=f"simplenote://note/{note['key']}",
                name=note.get("content", "").splitlines()[0][:30]
                if note.get("content")
                else note["key"],
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
        raise ValidationError(f"Invalid Simplenote URI: {uri}")

    note_id = uri.replace("simplenote://note/", "")

    try:
        # Try to get the note from cache first
        global note_cache
        if note_cache is not None and note_cache.is_initialized:
            logger.debug(f"Getting note {note_id} from cache")
            try:
                note = note_cache.get_note(note_id)
                logger.debug(f"Found note {note_id} in cache")
                note_uri = f"simplenote://note/{note_id}"
                text_contents = types.TextResourceContents(
                    text=note.get("content", ""),
                    uri=note_uri,
                    meta={
                        "tags": note.get("tags", []),
                        "modifydate": note.get("modifydate", ""),
                        "createdate": note.get("createdate", ""),
                    }
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
            if note_cache is not None and note_cache.is_initialized:
                note_cache.update_cache_after_update(note)

            note_uri = f"simplenote://note/{note_id}"
            text_contents = types.TextResourceContents(
                text=note.get("content", ""),
                uri=note_uri,
                meta={
                    "tags": note.get("tags", []),
                    "modifydate": note.get("modifydate", ""),
                    "createdate": note.get("createdate", ""),
                }
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
async def handle_list_tools() -> List[types.Tool]:
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
                            "description": "The content of the note"
                        },
                        "tags": {
                            "type": "string",
                            "description": "Tags for the note (comma-separated)"
                        }
                    },
                    "required": ["content"]
                }
            ),
            types.Tool(
                name="update_note",
                description="Update an existing note in Simplenote",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to update"
                        },
                        "content": {
                            "type": "string",
                            "description": "The new content of the note"
                        },
                        "tags": {
                            "type": "string",
                            "description": "Tags for the note (comma-separated)"
                        }
                    },
                    "required": ["note_id", "content"]
                }
            ),
            types.Tool(
                name="delete_note",
                description="Delete a note from Simplenote",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to delete"
                        }
                    },
                    "required": ["note_id"]
                }
            ),
            types.Tool(
                name="search_notes",
                description="Search for notes in Simplenote",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return"
                        }
                    },
                    "required": ["query"]
                }
            ),
            types.Tool(
                name="get_note",
                description="Get a note by ID from Simplenote",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": "string",
                            "description": "The ID of the note to retrieve"
                        }
                    },
                    "required": ["note_id"]
                }
            ),
        ]
        logger.info(f"Returning {len(tools)} tools: {', '.join([t.name for t in tools])}")
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
                            "description": "The content of the note"
                        }
                    },
                    "required": ["content"]
                }
            ),
            types.Tool(
                name="search_notes",
                description="Search for notes in Simplenote",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query"
                        }
                    },
                    "required": ["query"]
                }
            )
        ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: Dict
) -> List[types.TextContent]:
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

        # Make sure the cache is initialized
        global note_cache
        if note_cache is None or not note_cache.is_initialized:
            logger.info("Cache not initialized, initializing now")
            await initialize_cache()

        if name == "create_note":
            content = arguments.get("content", "")
            tags_str = arguments.get("tags", "")
            tags = [tag.strip() for tag in tags_str.split(",")] if tags_str else []

            if not content:
                raise ValidationError("Note content is required")

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
                                    "first_line": content.splitlines()[0][:30]
                                    if content
                                    else "",
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
                return [types.TextContent(type="text", text=json.dumps(error.to_dict()))]

        elif name == "update_note":
            note_id = arguments.get("note_id", "")
            content = arguments.get("content", "")
            tags_str = arguments.get("tags", "")

            if not note_id:
                raise ValidationError("Note ID is required")

            if not content:
                raise ValidationError("Note content is required")

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
                        error_msg = f"Failed to find note with ID {note_id}"
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
                return [types.TextContent(type="text", text=json.dumps(error.to_dict()))]

        elif name == "delete_note":
            note_id = arguments.get("note_id", "")

            if not note_id:
                raise ValidationError("Note ID is required")

            try:
                status = sn.trash_note(note_id)  # Using trash_note as it's safer than delete_note

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
                    error_msg = "Failed to move note to trash"
                    logger.error(error_msg)
                    raise NetworkError(error_msg)

            except Exception as e:
                if isinstance(e, ServerError):
                    error_dict = e.to_dict()
                    return [types.TextContent(type="text", text=json.dumps(error_dict))]

                logger.error(f"Error deleting note: {str(e)}", exc_info=True)
                error = handle_exception(e, f"deleting note {note_id}")
                return [types.TextContent(type="text", text=json.dumps(error.to_dict()))]

        elif name == "search_notes":
            query = arguments.get("query", "")
            limit = arguments.get("limit")

            if not query:
                raise ValidationError("Search query is required")

            if limit is not None:
                try:
                    limit = int(limit)
                    if limit < 1:
                        limit = None
                except (ValueError, TypeError):
                    limit = None

            try:
                # Use the cache for search if available
                if note_cache is not None and note_cache.is_initialized:
                    logger.debug(f"Searching notes in cache for query: {query}")
                    notes = note_cache.search_notes(query, limit=limit)

                    results = []
                    for note in notes:
                        content = note.get("content", "")
                        results.append({
                            "id": note.get("key"),
                            "title": content.splitlines()[0][:30] if content else note.get("key"),
                            "snippet": content[:100] + "..." if len(content) > 100 else content,
                            "tags": note.get("tags", []),
                            "uri": f"simplenote://note/{note.get('key')}",
                        })

                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "success": True,
                                    "results": results,
                                    "count": len(results),
                                    "query": query,
                                }
                            ),
                        )
                    ]

                # Fall back to API if cache is not available
                logger.debug(f"Cache not available, using API for search: {query}")
                notes, status = sn.get_note_list()

                if status != 0:
                    error_msg = "Failed to retrieve notes for search"
                    logger.error(error_msg)
                    raise NetworkError(error_msg)

                # Simple search in content
                query_lower = query.lower()
                results = []

                for note in notes:
                    content = note.get("content", "").lower()
                    if query_lower in content:
                        # Calculate a crude relevance score (number of occurrences)
                        occurrences = content.count(query_lower)
                        results.append((
                            {
                                "id": note.get("key"),
                                "title": note.get("content", "").splitlines()[0][:30] if note.get("content") else note.get("key"),
                                "snippet": content[:100] + "..." if len(content) > 100 else content,
                                "tags": note.get("tags", []),
                                "uri": f"simplenote://note/{note.get('key')}",
                            },
                            occurrences
                        ))

                # Sort by relevance (higher score first)
                results.sort(key=lambda x: x[1], reverse=True)

                # Apply limit if specified
                if limit is not None:
                    results = results[:limit]

                # Return just the notes, not the scores
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "results": [r[0] for r in results],
                                "count": len(results),
                                "query": query,
                            }
                        ),
                    )
                ]

            except Exception as e:
                if isinstance(e, ServerError):
                    error_dict = e.to_dict()
                    return [types.TextContent(type="text", text=json.dumps(error_dict))]

                logger.error(f"Error searching notes: {str(e)}", exc_info=True)
                error = handle_exception(e, f"searching notes for '{query}'")
                return [types.TextContent(type="text", text=json.dumps(error.to_dict()))]

        elif name == "get_note":
            note_id = arguments.get("note_id", "")

            if not note_id:
                raise ValidationError("Note ID is required")

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
                        error_msg = f"Failed to find note with ID {note_id}"
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
                                "uri": f"simplenote://note/{note.get('key')}"
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
                return [types.TextContent(type="text", text=json.dumps(error.to_dict()))]

        else:
            error_msg = f"Unknown tool: {name}"
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
async def handle_list_prompts() -> List[types.Prompt]:
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
    name: str, arguments: Optional[Dict[str, str]]
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
        error_msg = f"Unknown prompt: {name}"
        logger.error(error_msg)
        raise ValidationError(error_msg)


async def run() -> None:
    """Run the server using STDIO transport."""
    logger.info("Starting MCP server STDIO transport")

    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            logger.info("STDIO server created, initializing MCP server")

            try:
                # Initialize the cache in the background
                asyncio.create_task(initialize_cache())

                # Get capabilities and log them
                capabilities = server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
                capabilities_json = json.dumps({
                    'has_prompts': bool(capabilities.prompts),
                    'has_resources': bool(capabilities.resources),
                    'has_tools': bool(capabilities.tools)
                })
                logger.info(f"Server capabilities: {capabilities_json}")

                # Get the server version
                from simplenote_mcp import __version__ as version

                # Run the server
                await server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="simplenote-mcp-server",
                        server_version=version,
                        capabilities=capabilities,
                    ),
                )
                logger.info("MCP server run completed")

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
        logger.info(f"Starting Simplenote MCP Server v{__version__}")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Environment: SIMPLENOTE_EMAIL={config.simplenote_email[:3]}*** (set: {config.simplenote_email is not None}), SIMPLENOTE_PASSWORD={'*****' if config.simplenote_password else 'Not set'}")
        logger.info(f"Running from: {os.path.dirname(os.path.abspath(__file__))}")
        logger.info(f"Sync interval: {config.sync_interval_seconds}s")
        logger.info(f"Log level: {config.log_level.value}")

        # Set up process management
        setup_signal_handlers()
        write_pid_file()
        logger.info("Process management initialized")

        # Run the async event loop
        asyncio.run(run())

    except Exception as e:
        logger.critical(f"Critical error in MCP server: {str(e)}", exc_info=True)
        cleanup_pid_file()  # Ensure PID file is cleaned up even on error
        sys.exit(1)


if __name__ == "__main__":
    run_main()
