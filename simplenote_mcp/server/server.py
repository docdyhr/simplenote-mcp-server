# simplenote_mcp/server/server.py

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from simplenote import Simplenote

# Set the log file path in the logs directory
LOGS_DIR = Path(__file__).parent.parent.parent / "simplenote_mcp" / "logs"
LOG_FILE = LOGS_DIR / "server.log"

# Create logs directory if it doesn't exist
LOGS_DIR.mkdir(parents=True, exist_ok=True)

def log_debug(message):
    """Log debug messages to stderr for Claude Desktop logs."""
    print(f"DEBUG: {message}", file=sys.stderr, flush=True)

    # Also log to a file for debugging
    with open(LOG_FILE, "a") as f:
        from datetime import datetime
        f.write(f"{datetime.now().isoformat()}: {message}\n")

    # For legacy support, also log to the old location
    with open("/tmp/simplenote_mcp_debug.log", "a") as f:
        from datetime import datetime
        f.write(f"{datetime.now().isoformat()}: {message}\n")


# Debug logging
log_debug("Server starting...")
log_debug(f"Python version: {sys.version}")
log_debug(f"Environment vars: SIMPLENOTE_EMAIL={os.environ.get('SIMPLENOTE_EMAIL', 'Not set')}, SIMPLENOTE_PASSWORD={'*****' if os.environ.get('SIMPLENOTE_PASSWORD') else 'Not set'}")
log_debug(f"Running from: {os.path.dirname(os.path.abspath(__file__))}")

# Create a server instance
try:
    log_debug("Creating MCP server instance")
    server = Server("simplenote-mcp-server")
    log_debug("MCP server instance created successfully")
except Exception as e:
    log_debug(f"Error creating server instance: {str(e)}")
    raise

# Initialize Simplenote client
simplenote_client = None


def get_simplenote_client() -> Simplenote:
    global simplenote_client
    if simplenote_client is None:
        try:
            log_debug("Initializing Simplenote client")
            # Get credentials from environment variables
            username = os.environ.get("SIMPLENOTE_EMAIL") or os.environ.get("SIMPLENOTE_USERNAME")
            password = os.environ.get("SIMPLENOTE_PASSWORD")

            if not username or not password:
                log_debug("Missing Simplenote credentials in environment variables")
                raise ValueError(
                    "SIMPLENOTE_EMAIL (or SIMPLENOTE_USERNAME) and SIMPLENOTE_PASSWORD environment variables must be set"
                )

            log_debug(f"Creating Simplenote client with username: {username[:3]}***")
            simplenote_client = Simplenote(username, password)
            log_debug("Simplenote client created successfully")
        except Exception as e:
            log_debug(f"Error initializing Simplenote client: {str(e)}")
            raise
    return simplenote_client


# ===== RESOURCE CAPABILITIES =====


@server.list_resources()
async def handle_list_resources() -> List[types.Resource]:
    # Add stack trace to debug where the call is coming from
    import traceback
    stack_trace = traceback.format_stack()
    log_debug(f"list_resources called from: {stack_trace[-2]}")

    sn = get_simplenote_client()
    try:
        # Get the list of notes from Simplenote
        resp, status = sn.get_note_list()
        if status == 0:
            # Only log every 10th call to reduce log spam
            import random
            if random.random() < 0.1:  # ~10% of calls
                log_debug(f"Listing resources, found {len(resp)} notes")
            return [
                types.Resource(
                    uri=f"simplenote://note/{note['key']}",
                    name=note.get("content", "").splitlines()[0][:30]
                    if note.get("content")
                    else note["key"],
                    description=f"Note from {note.get('modifydate', 'unknown date')}",
                )
                for note in resp
            ]
        else:
            log_debug(f"Failed to list resources, status: {status}")
            return []
    except Exception as e:
        log_debug(f"Error listing resources: {e}")
        return []


@server.read_resource()
async def handle_read_resource(uri: str) -> types.ReadResourceResult:
    sn = get_simplenote_client()

    # Parse the URI to get the note ID
    if not uri.startswith("simplenote://note/"):
        raise ValueError(f"Invalid Simplenote URI: {uri}")

    note_id = uri.replace("simplenote://note/", "")

    try:
        # Get the note from Simplenote
        note, status = sn.get_note(note_id)
        if status == 0:
            return types.ReadResourceResult(
                content=types.TextContent(
                    type="text", text=note.get("content", "")
                ),
                meta={
                    "tags": note.get("tags", []),
                    "modifydate": note.get("modifydate", ""),
                    "createdate": note.get("createdate", ""),
                },
            )
        else:
            raise ValueError(f"Failed to get note with ID {note_id}")
    except Exception as e:
        print(f"Error reading resource: {e}")
        raise ValueError(f"Error reading note: {str(e)}") from e


# ===== TOOL CAPABILITIES =====


@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    try:
        log_debug("Listing available tools")
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
                        }
                    },
                    "required": ["query"]
                }
            ),
        ]
        log_debug(f"Returning {len(tools)} tools: {', '.join([t.name for t in tools])}")
        return tools
    except Exception as e:
        log_debug(f"Error listing tools: {str(e)}")
        # Return at least one tool to prevent errors
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
            )
        ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: Dict
) -> List[types.TextContent]:
    log_debug(f"Tool call: {name} with arguments: {json.dumps(arguments)}")
    sn = get_simplenote_client()

    if name == "create_note":
        content = arguments.get("content", "")
        tags_str = arguments.get("tags", "")
        tags = [tag.strip() for tag in tags_str.split(",")] if tags_str else []

        note = {"content": content}
        if tags:
            note["tags"] = tags

        try:
            note, status = sn.add_note(note)
            if status == 0:
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
                            }
                        ),
                    )
                ]
            else:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": False,
                                "message": "Failed to create note",
                            }
                        ),
                    )
                ]
        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": False,
                            "message": f"Error creating note: {str(e)}",
                        }
                    ),
                )
            ]

    elif name == "update_note":
        note_id = arguments.get("note_id", "")
        content = arguments.get("content", "")
        tags_str = arguments.get("tags", "")

        if not note_id:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {"success": False, "message": "Note ID is required"}
                    ),
                )
            ]

        try:
            # Get the existing note first
            existing_note, status = sn.get_note(note_id)
            if status != 0:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": False,
                                "message": f"Failed to find note with ID {note_id}",
                            }
                        ),
                    )
                ]

            # Update the note content
            existing_note["content"] = content

            # Update tags if provided
            if tags_str:
                tags = [tag.strip() for tag in tags_str.split(",")]
                existing_note["tags"] = tags

            updated_note, status = sn.update_note(existing_note)
            if status == 0:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "message": "Note updated successfully",
                                "note_id": updated_note.get("key"),
                            }
                        ),
                    )
                ]
            else:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": False,
                                "message": "Failed to update note",
                            }
                        ),
                    )
                ]
        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": False,
                            "message": f"Error updating note: {str(e)}",
                        }
                    ),
                )
            ]

    elif name == "delete_note":
        note_id = arguments.get("note_id", "")

        if not note_id:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {"success": False, "message": "Note ID is required"}
                    ),
                )
            ]

        try:
            status = sn.trash_note(
                note_id
            )  # Using trash_note as it's safer than delete_note
            if status == 0:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "message": "Note moved to trash successfully",
                            }
                        ),
                    )
                ]
            else:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": False,
                                "message": "Failed to move note to trash",
                            }
                        ),
                    )
                ]
        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": False,
                            "message": f"Error deleting note: {str(e)}",
                        }
                    ),
                )
            ]

    elif name == "search_notes":
        query = arguments.get("query", "")

        if not query:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": False,
                            "message": "Search query is required",
                        }
                    ),
                )
            ]

        try:
            # Get all notes and filter manually (Simplenote API doesn't have search)
            notes, status = sn.get_note_list()
            if status != 0:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": False,
                                "message": "Failed to retrieve notes",
                            }
                        ),
                    )
                ]

            # Simple search in content
            results = []
            for note in notes:
                content = note.get("content", "").lower()
                if query.lower() in content:
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
                        }
                    )

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "results": results,
                            "count": len(results),
                        }
                    ),
                )
            ]
        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": False,
                            "message": f"Error searching notes: {str(e)}",
                        }
                    ),
                )
            ]

    else:
        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {"success": False, "message": f"Unknown tool: {name}"}
                ),
            )
        ]


# ===== PROMPT CAPABILITIES =====


@server.list_prompts()
async def handle_list_prompts() -> List[types.Prompt]:
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
        raise ValueError(f"Unknown prompt: {name}")


async def run() -> None:
    # Run the server as STDIO
    log_debug("Starting MCP server STDIO transport")
    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            log_debug("STDIO server created, initializing MCP server")
            try:
                # Get capabilities and log them
                capabilities = server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
                log_debug(f"Server capabilities: {json.dumps({
                    'has_prompts': bool(capabilities.prompts),
                    'has_resources': bool(capabilities.resources),
                    'has_tools': bool(capabilities.tools)
                })}")

                # Run the server
                await server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="simplenote-mcp",
                        server_version="0.1.0",
                        capabilities=capabilities,
                    ),
                )
                log_debug("MCP server run completed")
            except Exception as e:
                log_debug(f"Error running MCP server: {str(e)}")
                raise
    except Exception as e:
        log_debug(f"Error creating STDIO server: {str(e)}")
        raise


def run_main():
    """Entry point for the console script."""
    asyncio.run(run())


if __name__ == "__main__":
    run_main()
