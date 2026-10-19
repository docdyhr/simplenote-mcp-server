"""MCP prompt templates: ``list_prompts`` and ``get_prompt`` handlers."""

import mcp.types as types

from .errors import ValidationError
from .logging import logger

UNKNOWN_PROMPT_ERROR = "Unknown prompt: {name}"


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
