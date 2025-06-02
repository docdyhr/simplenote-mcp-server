"""Tool handlers for Simplenote MCP server.

This module contains separate handler functions for each tool,
extracted from the massive handle_call_tool() function to improve
maintainability and reduce complexity.

Each tool handler is implemented as a separate class that inherits from
ToolHandlerBase and implements the handle() method. The ToolHandlerRegistry
provides a centralized way to manage and dispatch tool calls.
"""

import contextlib
import json
from typing import Any

import mcp.types as types

from .cache import NoteCache
from .config import get_config
from .errors import (
    InternalError,
    NetworkError,
    ResourceNotFoundError,
    ServerError,
    ValidationError,
)
from .logging import logger


def safe_get(obj: Any, key: str, default: Any = None) -> Any:
    """Safely get a value from an object that might be a dict or an exception."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    if hasattr(obj, "get"):
        with contextlib.suppress(Exception):
            return obj.get(key, default)
    if hasattr(obj, "__getitem__"):
        with contextlib.suppress(Exception):
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
        with contextlib.suppress(Exception):
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


def extract_title_from_content(content: str, fallback: str = "") -> str:
    """Extract the first non-empty line from content as title."""
    from .config import get_config

    if not content:
        return fallback

    config = get_config()
    lines = content.splitlines()
    for line in lines:
        stripped_line = line.strip()
        if stripped_line:
            return stripped_line[: config.title_max_length]

    return fallback


# Error messages
NOTE_CONTENT_REQUIRED = "Note content is required"
NOTE_ID_REQUIRED = "Note ID is required"
TAGS_REQUIRED = "Tags are required"
QUERY_REQUIRED = "Search query is required"
FAILED_GET_NOTE = "Failed to find note with ID {note_id}"
FAILED_UPDATE_TAGS = "Failed to update note tags"
FAILED_TRASH_NOTE = "Failed to move note to trash"
FAILED_RETRIEVE_NOTES = "Failed to retrieve notes for search"


class ToolHandlerBase:
    """Base class for tool handlers with common functionality."""

    def __init__(self, simplenote_client: Any, note_cache: NoteCache | None = None) -> None:
        """Initialize the handler.

        Args:
            simplenote_client: The Simplenote API client
            note_cache: Optional note cache instance
        """
        self.sn = simplenote_client
        self.note_cache = note_cache

    def _get_note_from_cache_or_api(self, note_id: str) -> dict[str, Any]:
        """Get a note from cache first, then API if not found.

        Args:
            note_id: The ID of the note to retrieve

        Returns:
            The note dictionary

        Raises:
            ResourceNotFoundError: If the note is not found
        """
        note = None

        # Try cache first
        if self.note_cache is not None and self.note_cache.is_initialized:
            with contextlib.suppress(ResourceNotFoundError):
                note = self.note_cache.get_note(note_id)

        # If not found in cache, get from API
        if note is None:
            note, status = self.sn.get_note(note_id)
            if status != 0 or not isinstance(note, dict):
                error_msg = FAILED_GET_NOTE.format(note_id=note_id)
                logger.error(error_msg)
                raise ResourceNotFoundError(error_msg)

        return note

    def _update_cache_after_operation(
        self, note: dict[str, Any], operation: str
    ) -> None:
        """Update cache after a successful operation.

        Args:
            note: The updated note
            operation: The type of operation (create, update, delete)
        """
        if self.note_cache is not None and self.note_cache.is_initialized:
            if operation == "create":
                self.note_cache.update_cache_after_create(note)
            elif operation == "update":
                self.note_cache.update_cache_after_update(note)
            elif operation == "delete":
                note_id = note.get("key") if isinstance(note, dict) else str(note)
                self.note_cache.update_cache_after_delete(note_id)


class CreateNoteHandler(ToolHandlerBase):
    """Handler for create_note tool."""

    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle create_note tool call."""
        content = arguments.get("content", "")
        tags_input = arguments.get("tags", "")

        # Handle tags which can be either a string or a list
        if isinstance(tags_input, list):
            tags = [str(tag).strip() for tag in tags_input]
        elif isinstance(tags_input, str):
            tags = [tag.strip() for tag in safe_split(tags_input)] if tags_input else []
        else:
            tags = []

        try:
            note = {"content": content}
            if tags:
                note["tags"] = tags

            created_note, status = self.sn.add_note(note)

            if status == 0:
                if isinstance(created_note, dict):
                    self._update_cache_after_operation(created_note, "create")
                else:
                    logger.error(
                        f"API call success status 0, but returned non-dict: {type(created_note)} for create_note"
                    )
                    # Create a safe dictionary to use instead
                    created_note = {"content": "", "key": "unknown", "tags": []}
                    logger.error("Using default note due to unexpected API response")

                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "message": "Note created successfully",
                                "note_id": created_note.get("key"),
                                "key": created_note.get(
                                    "key"
                                ),  # For backward compatibility
                                "first_line": extract_title_from_content(content, ""),
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
                return [types.TextContent(type="text", text=json.dumps(e.to_dict()))]

            logger.error(f"Error creating note: {str(e)}", exc_info=True)
            from .errors import handle_exception

            error = handle_exception(e, "creating note")
            return [types.TextContent(type="text", text=json.dumps(error.to_dict()))]


class UpdateNoteHandler(ToolHandlerBase):
    """Handler for update_note tool."""

    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle update_note tool call."""
        note_id = arguments.get("note_id", "")
        content = arguments.get("content", "")
        tags_input = arguments.get("tags", "")

        if not note_id:
            raise ValidationError(NOTE_ID_REQUIRED)

        if not content:
            raise ValidationError(NOTE_CONTENT_REQUIRED)

        try:
            existing_note = self._get_note_from_cache_or_api(note_id)

            # Update the note content
            safe_set(existing_note, "content", content)

            # Update tags if provided
            if tags_input:
                if isinstance(tags_input, list):
                    tags = [tag.strip() for tag in tags_input]
                elif isinstance(tags_input, str):
                    tags = [tag.strip() for tag in safe_split(tags_input)]
                else:
                    tags = []

                safe_set(existing_note, "tags", tags)

            updated_note, status = self.sn.update_note(existing_note)

            if status == 0:
                if isinstance(updated_note, dict):
                    self._update_cache_after_operation(updated_note, "update")
                else:
                    logger.error(
                        f"API call success status 0, but returned non-dict: {type(updated_note)} for update_note"
                    )
                    # Create a safe dictionary to use instead
                    content = ""
                    if isinstance(existing_note, dict):
                        content = existing_note.get("content", "")
                    updated_note = {"content": content, "key": note_id, "tags": []}
                    logger.error(
                        f"Using default note after update due to unexpected API response for {note_id}"
                    )

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
                return [types.TextContent(type="text", text=json.dumps(e.to_dict()))]

            logger.error(f"Error updating note: {str(e)}", exc_info=True)
            from .errors import handle_exception

            error = handle_exception(e, f"updating note {note_id}")
            return [types.TextContent(type="text", text=json.dumps(error.to_dict()))]


class DeleteNoteHandler(ToolHandlerBase):
    """Handler for delete_note tool."""

    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle delete_note tool call."""
        note_id = arguments.get("note_id", "")

        if not note_id:
            raise ValidationError(NOTE_ID_REQUIRED)

        try:
            status = self.sn.trash_note(note_id)  # Using trash_note as it's safer

            if status == 0:
                self._update_cache_after_operation(note_id, "delete")

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
                return [types.TextContent(type="text", text=json.dumps(e.to_dict()))]

            logger.error(f"Error deleting note: {str(e)}", exc_info=True)
            from .errors import handle_exception

            error = handle_exception(e, f"deleting note {note_id}")
            return [types.TextContent(type="text", text=json.dumps(error.to_dict()))]


class GetNoteHandler(ToolHandlerBase):
    """Handler for get_note tool."""

    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle get_note tool call."""
        note_id = arguments.get("note_id", "")

        if not note_id:
            raise ValidationError(NOTE_ID_REQUIRED)

        try:
            note = self._get_note_from_cache_or_api(note_id)

            # Verify that we have a dictionary before proceeding
            if not isinstance(note, dict):
                error_msg = f"API returned non-dictionary for note {note_id}"
                logger.error(error_msg)
                raise InternalError(error_msg)

            # Prepare response
            content = safe_get(note, "content", "")
            first_line = extract_title_from_content(content, "")

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
                return [types.TextContent(type="text", text=json.dumps(e.to_dict()))]

            logger.error(f"Error getting note: {str(e)}", exc_info=True)
            from .errors import handle_exception

            error = handle_exception(e, f"getting note {note_id}")
            return [types.TextContent(type="text", text=json.dumps(error.to_dict()))]


class SearchNotesHandler(ToolHandlerBase):
    """Handler for search_notes tool."""

    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle search_notes tool call."""
        query = arguments.get("query", "")
        limit = arguments.get("limit")
        tags_input = arguments.get("tags", "")
        from_date_str = arguments.get("from_date")
        to_date_str = arguments.get("to_date")

        logger.debug(
            f"Advanced search called with: query='{query}', limit={limit}, "
            + f"tags='{tags_input}', from_date='{from_date_str}', to_date='{to_date_str}'"
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
        if tags_input:
            if isinstance(tags_input, list):
                tag_filters = [tag.strip() for tag in tags_input if tag.strip()]
            elif isinstance(tags_input, str):
                tag_filters = [
                    tag.strip() for tag in safe_split(tags_input) if tag.strip()
                ]
            else:
                tag_filters = None
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
            cache_initialized = (
                self.note_cache is not None and self.note_cache.is_initialized
            )
            logger.debug(
                f"Cache status for search: available={self.note_cache is not None}, initialized={cache_initialized}"
            )

            # Use the cache for search if available
            if cache_initialized:
                return await self._search_with_cache(
                    query, limit, tag_filters, date_range, arguments
                )
            else:
                return await self._search_with_api(
                    query, limit, tag_filters, date_range
                )

        except Exception as e:
            if isinstance(e, ServerError):
                return [types.TextContent(type="text", text=json.dumps(e.to_dict()))]

            logger.error(f"Error searching notes: {str(e)}", exc_info=True)
            from .errors import handle_exception

            error = handle_exception(e, f"searching notes for '{query}'")
            return [types.TextContent(type="text", text=json.dumps(error.to_dict()))]

    async def _search_with_cache(
        self,
        query: str,
        limit: int | None,
        tag_filters: list[str] | None,
        date_range: tuple | None,
        arguments: dict[str, Any],
    ) -> list[types.TextContent]:
        """Search using cache."""
        logger.debug("Using advanced search with cache")

        # Get offset parameter for pagination or default to 0
        offset = safe_get(arguments, "offset", 0)

        # Get total matching notes for pagination info
        all_matching_notes = self.note_cache.search_notes(
            query=query,
            tag_filters=tag_filters,
            date_range=date_range,
        )
        total_matching_notes = len(all_matching_notes)

        # Use the enhanced search implementation with pagination
        notes = self.note_cache.search_notes(
            query=query,
            limit=limit,
            offset=offset,
            tag_filters=tag_filters,
            date_range=date_range,
        )

        # Format results
        results = []
        config = get_config()
        for note in notes:
            content = note.get("content", "")
            snippet = (
                content[: config.snippet_max_length] + "..."
                if len(content) > config.snippet_max_length
                else content
            )
            results.append(
                {
                    "id": note.get("key"),
                    "title": extract_title_from_content(
                        content, safe_get(note, "key", "")
                    ),
                    "snippet": snippet,
                    "tags": note.get("tags", []),
                    "uri": f"simplenote://note/{note.get('key')}",
                }
            )

        # Add debug logging for troubleshooting
        logger.debug(f"Search results: {len(results)} matches found for '{query}'")

        # Debug log the first few results if available
        if results:
            logger.debug(f"First result title: {results[0].get('title', 'No title')}")

        # Get pagination metadata
        pagination_info = self.note_cache.get_pagination_info(
            total_items=total_matching_notes, limit=limit, offset=offset
        )

        # Create response with pagination info
        response = {
            "success": True,
            "results": results,
            "count": len(results),
            "total": total_matching_notes,
            "pagination": pagination_info,
            "query": query,
            "page": pagination_info.get("page", 1),
            "total_pages": pagination_info.get("total_pages", 1),
            "has_more": pagination_info.get("has_more", False),
            "next_offset": pagination_info.get("next_offset"),
            "prev_offset": pagination_info.get("prev_offset"),
        }

        # Log the response size
        response_json = json.dumps(response)
        logger.debug(f"Response size: {len(response_json)} bytes")

        return [types.TextContent(type="text", text=response_json)]

    async def _search_with_api(
        self,
        query: str,
        limit: int | None,
        tag_filters: list[str] | None,
        date_range: tuple | None,
    ) -> list[types.TextContent]:
        """Search using API fallback."""
        logger.debug("Cache not available, using API with temporary search engine")
        from .search.engine import SearchEngine

        api_search_engine = SearchEngine()

        # Get all notes from the API
        all_notes, status = self.sn.get_note_list()

        if status != 0:
            logger.error(FAILED_RETRIEVE_NOTES)
            raise NetworkError(FAILED_RETRIEVE_NOTES)

        # Convert list to dictionary for search engine
        notes_dict = {note.get("key"): note for note in all_notes if note.get("key")}

        logger.debug(f"API search: Got {len(notes_dict)} notes from API")

        # Use the search engine
        matching_notes = api_search_engine.search(
            notes=notes_dict,
            query=query,
            tag_filters=tag_filters,
            date_range=date_range,
        )
        # Apply limit to results
        if limit is not None and limit > 0:
            matching_notes = matching_notes[:limit]

        # Format results
        results = []
        config = get_config()
        for note in matching_notes:
            content = note.get("content", "")
            snippet = (
                content[: config.snippet_max_length] + "..."
                if len(content) > config.snippet_max_length
                else content
            )
            results.append(
                {
                    "id": note.get("key"),
                    "title": extract_title_from_content(
                        content, safe_get(note, "key", "")
                    ),
                    "snippet": snippet,
                    "tags": note.get("tags", []),
                    "uri": f"simplenote://note/{note.get('key')}",
                }
            )

        # Debug logging
        logger.debug(f"API search results: {len(results)} matches found for '{query}'")
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


class TagOperationHandler(ToolHandlerBase):
    """Base handler for tag operations (add, remove, replace)."""

    def _parse_tags(self, tags_input: Any) -> list[str]:
        """Parse tags from various input formats."""
        if isinstance(tags_input, list):
            return [tag.strip() for tag in tags_input]
        elif isinstance(tags_input, str):
            return [tag.strip() for tag in safe_split(tags_input)] if tags_input else []
        else:
            return []


class AddTagsHandler(TagOperationHandler):
    """Handler for add_tags tool."""

    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle add_tags tool call."""
        note_id = arguments.get("note_id", "")
        tags_input = arguments.get("tags", "")

        if not note_id:
            raise ValidationError(NOTE_ID_REQUIRED)

        if not tags_input:
            raise ValidationError(TAGS_REQUIRED)

        self._parse_tags(tags_input)

        try:
            existing_note = self._get_note_from_cache_or_api(note_id)

            # Parse the tags to add
            tags_to_add = [tag.strip() for tag in safe_split(tags_input) if tag.strip()]

            # Get current tags or initialize empty list
            current_tags = safe_get(existing_note, "tags", [])
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
                updated_note, status = self.sn.update_note(existing_note)

                if status == 0:
                    # Check if the result is actually a dictionary
                    if not isinstance(updated_note, dict):
                        logger.error(
                            f"API call success status 0, but returned non-dict: {type(updated_note)} for add_tags"
                        )
                        raise InternalError(
                            "Unexpected API response type after adding tags."
                        )

                    self._update_cache_after_operation(updated_note, "update")

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
                return [types.TextContent(type="text", text=json.dumps(e.to_dict()))]

            logger.error(f"Error adding tags: {str(e)}", exc_info=True)
            from .errors import handle_exception

            error = handle_exception(e, f"adding tags to note {note_id}")
            return [types.TextContent(type="text", text=json.dumps(error.to_dict()))]


class RemoveTagsHandler(TagOperationHandler):
    """Handler for remove_tags tool."""

    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle remove_tags tool call."""
        note_id = arguments.get("note_id", "")
        tags_input = arguments.get("tags", "")

        if not note_id:
            raise ValidationError(NOTE_ID_REQUIRED)

        if not tags_input:
            raise ValidationError(TAGS_REQUIRED)

        self._parse_tags(tags_input)

        try:
            existing_note = self._get_note_from_cache_or_api(note_id)

            # Parse the tags to remove
            tags_to_remove = [
                tag.strip() for tag in safe_split(tags_input) if tag.strip()
            ]

            # Get current tags or initialize empty list
            current_tags = safe_get(existing_note, "tags", [])
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
                safe_set(existing_note, "tags", new_tags)
                updated_note, status = self.sn.update_note(existing_note)

                if status == 0:
                    # Check if the result is actually a dictionary
                    if not isinstance(updated_note, dict):
                        logger.error(
                            f"API call success status 0, but returned non-dict: {type(updated_note)} for remove_tags"
                        )
                        raise InternalError(
                            "Unexpected API response type after removing tags."
                        )

                    self._update_cache_after_operation(updated_note, "update")

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
                return [types.TextContent(type="text", text=json.dumps(e.to_dict()))]

            logger.error(f"Error removing tags: {str(e)}", exc_info=True)
            from .errors import handle_exception

            error = handle_exception(e, f"removing tags from note {note_id}")
            return [types.TextContent(type="text", text=json.dumps(error.to_dict()))]


class ReplaceTagsHandler(TagOperationHandler):
    """Handler for replace_tags tool."""

    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle replace_tags tool call."""
        note_id = arguments.get("note_id", "")
        tags_input = arguments.get("tags", "")

        if not note_id:
            raise ValidationError(NOTE_ID_REQUIRED)

        try:
            existing_note = self._get_note_from_cache_or_api(note_id)

            # Parse the new tags
            new_tags = self._parse_tags(tags_input)
            if tags_input and isinstance(tags_input, str):
                new_tags = [
                    tag.strip() for tag in safe_split(tags_input) if tag.strip()
                ]

            # Get current tags
            current_tags = safe_get(existing_note, "tags", [])
            if current_tags is None:
                current_tags = []

            # Update the note with new tags
            safe_set(existing_note, "tags", new_tags)
            updated_note, status = self.sn.update_note(existing_note)

            if status == 0:
                # Check if the result is actually a dictionary
                if not isinstance(updated_note, dict):
                    logger.error(
                        f"API call success status 0, but returned non-dict: {type(updated_note)} for replace_tags"
                    )
                    raise InternalError(
                        "Unexpected API response type after replacing tags."
                    )

                self._update_cache_after_operation(updated_note, "update")

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
                return [types.TextContent(type="text", text=json.dumps(e.to_dict()))]

            logger.error(f"Error replacing tags: {str(e)}", exc_info=True)
            from .errors import handle_exception

            error = handle_exception(e, f"replacing tags on note {note_id}")
            return [types.TextContent(type="text", text=json.dumps(error.to_dict()))]


class ToolHandlerRegistry:
    """Registry for tool handlers."""

    def __init__(self) -> None:
        """Initialize the registry."""
        self._handlers: dict[str, type[ToolHandlerBase]] = {
            "create_note": CreateNoteHandler,
            "update_note": UpdateNoteHandler,
            "delete_note": DeleteNoteHandler,
            "get_note": GetNoteHandler,
            "search_notes": SearchNotesHandler,
            "add_tags": AddTagsHandler,
            "remove_tags": RemoveTagsHandler,
            "replace_tags": ReplaceTagsHandler,
        }

    def get_handler(
        self,
        tool_name: str,
        simplenote_client: Any,
        note_cache: NoteCache | None = None,
    ) -> ToolHandlerBase | None:
        """Get a handler for the given tool name.

        Args:
            tool_name: The name of the tool
            simplenote_client: The Simplenote API client
            note_cache: Optional note cache instance

        Returns:
            The handler instance or None if not found
        """
        handler_class = self._handlers.get(tool_name)
        if handler_class:
            return handler_class(simplenote_client, note_cache)
        return None

    def list_tools(self) -> list[str]:
        """List all available tool names."""
        return list(self._handlers.keys())
