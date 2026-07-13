"""Tool handlers for Simplenote MCP server.

This module contains separate handler functions for each tool,
extracted from the massive handle_call_tool() function to improve
maintainability and reduce complexity.

Each tool handler is implemented as a separate class that inherits from
ToolHandlerBase and implements the handle() method. The ToolHandlerRegistry
provides a centralized way to manage and dispatch tool calls.
"""

import asyncio
import contextlib
import json
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any

import mcp.types as types

from .cache import NoteCache
from .config import get_config
from .decorators import (
    validate_content_required,
    validate_note_id_required,
    validate_query_required,
    validate_tags_required,
    with_input_validation,
)
from .error_helpers import (
    empty_field_error,
    required_field_error,
)
from .errors import (
    InternalError,
    NetworkError,
    ResourceNotFoundError,
    ServerError,
)
from .logging import logger
from .security import validate_tool_security
from .utils.common import (
    extract_title_from_content as extract_title_common,
)
from .utils.common import (
    safe_get,
    safe_set,
    safe_split,
)

# Utility functions imported from common module


def extract_title_from_content(content: str, fallback: str = "") -> str:
    """Extract the first non-empty line from content as title."""
    from .config import get_config

    title = extract_title_common(content)
    if title:
        config = get_config()
        return title[: config.title_max_length]
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


class ToolHandlerBase(ABC):
    """Base class for tool handlers with common functionality."""

    def __init__(
        self, simplenote_client: Any, note_cache: NoteCache | None = None
    ) -> None:
        """Initialize the handler.

        Args:
            simplenote_client: The Simplenote API client
            note_cache: Optional note cache instance
        """
        self.sn = simplenote_client
        self.note_cache = note_cache

    @abstractmethod
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle the tool call with the given arguments.

        Args:
            arguments: Tool arguments

        Returns:
            List of text content responses
        """

    def _format_error_response(
        self, error: Exception, operation: str, context: dict[str, Any] | None = None
    ) -> list[types.TextContent]:
        """Format an error into a consistent JSON response.

        Args:
            error: The exception that occurred
            operation: Description of the operation that failed
            context: Optional context information (note_id, query, etc.)

        Returns:
            List containing formatted error response
        """
        if isinstance(error, ServerError):
            error_dict = error.to_dict()
        else:
            from .errors import handle_exception

            logger.error(f"Error {operation}: {str(error)}", exc_info=True)
            handled_error = handle_exception(error, operation)
            error_dict = handled_error.to_dict()

        # Add context if provided
        if context:
            error_dict["error"]["context"] = context

        return [types.TextContent(type="text", text=json.dumps(error_dict))]

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
            # Guard: a None token would cause a cryptic TypeError in urllib's
            # putheader() — surface it as a clean not-found error instead.
            if not getattr(self.sn, "token", None):
                raise ResourceNotFoundError(
                    f"Note {note_id} not found — Simplenote is not authenticated; "
                    "API fallback unavailable. Check server logs for auth errors.",
                    resource_id=note_id,
                )
            note, status = self.sn.get_note(note_id)
            if status != 0 or not isinstance(note, dict):
                error_msg = FAILED_GET_NOTE.format(note_id=note_id)
                logger.error(error_msg)
                raise ResourceNotFoundError(error_msg, resource_id=note_id)

        return note

    def _parse_tags(self, tags_input: Any) -> list[str]:
        """Parse tags from various input formats.

        Tags are expected to be comma-separated when provided as a string.
        Spaces within individual tags are converted to hyphens.
        """
        if isinstance(tags_input, list):
            return [tag.strip().replace(" ", "-") for tag in tags_input]
        elif isinstance(tags_input, str):
            return (
                [tag.strip().replace(" ", "-") for tag in safe_split(tags_input, ",")]
                if tags_input
                else []
            )
        else:
            return []

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
                if isinstance(note, dict):
                    note_id = note.get("key")
                    if note_id is not None:
                        self.note_cache.update_cache_after_delete(str(note_id))
                else:
                    self.note_cache.update_cache_after_delete(str(note))


class CreateNoteHandler(ToolHandlerBase):
    """Handler for create_note tool."""

    @validate_tool_security("create_note")
    @with_input_validation(validate_content_required)
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle create_note tool call."""
        content = arguments.get("content", "")
        tags_input = arguments.get("tags", "")

        # Handle tags which can be either a string or a list (comma-separated)
        # Spaces in tags are converted to hyphens via _parse_tags
        tags = self._parse_tags(tags_input) if tags_input else []

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
            return self._format_error_response(e, "creating note")


class UpdateNoteHandler(ToolHandlerBase):
    """Handler for update_note tool."""

    @validate_tool_security("update_note")
    @with_input_validation(validate_note_id_required, validate_content_required)
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle update_note tool call."""
        note_id = arguments.get("note_id", "")
        content = arguments.get("content", "")
        tags_input = arguments.get("tags", "")

        if not note_id:
            raise empty_field_error("note_id")

        if "content" not in arguments:
            raise required_field_error("content")

        try:
            existing_note = self._get_note_from_cache_or_api(note_id)

            # Guard against catastrophic content replacement: refuse when the
            # new content is drastically smaller than the existing note (likely
            # an LLM error rather than a deliberate edit).
            _SHRINK_MIN_CHARS = 200
            _SHRINK_RATIO = 0.2
            existing_content = existing_note.get("content", "") or ""
            if (
                len(existing_content) >= _SHRINK_MIN_CHARS
                and len(content) < len(existing_content) * _SHRINK_RATIO
            ):
                from .errors import ValidationError as _VE

                raise _VE(
                    f"Refusing to replace a {len(existing_content)}-character note "
                    f"with {len(content)} characters "
                    f"({len(content) / max(len(existing_content), 1):.0%} of original). "
                    "Call get_note first, make targeted edits, and pass the full merged "
                    "content. Use add_text or replace_section for partial updates.",
                    subcategory="suspicious_shrink",
                )

            # Update the note content
            safe_set(existing_note, "content", content)

            # Update tags if provided (comma-separated or list); spaces → hyphens,
            # consistent with create_note and every other tag-accepting tool.
            if tags_input:
                tags = self._parse_tags(tags_input)
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
            return self._format_error_response(
                e, f"updating note {note_id}", {"note_id": note_id}
            )


class DeleteNoteHandler(ToolHandlerBase):
    """Handler for delete_note tool."""

    @validate_tool_security("delete_note")
    @with_input_validation(validate_note_id_required)
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle delete_note tool call."""
        note_id = arguments.get("note_id", "")

        if not note_id:
            raise empty_field_error("note_id")

        try:
            result = self.sn.trash_note(note_id)  # Using trash_note as it's safer
            # trash_note returns a tuple (note, status)
            _note, status = result if isinstance(result, tuple) else (None, result)

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
            return self._format_error_response(
                e, f"deleting note {note_id}", {"note_id": note_id}
            )


class GetNoteHandler(ToolHandlerBase):
    """Handler for get_note tool."""

    @validate_tool_security("get_note")
    @with_input_validation(validate_note_id_required)
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle get_note tool call."""
        note_id = arguments.get("note_id", "")

        if not note_id:
            raise empty_field_error("note_id")

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
            return self._format_error_response(
                e, f"getting note {note_id}", {"note_id": note_id}
            )


class SearchNotesHandler(ToolHandlerBase):
    """Handler for search_notes tool."""

    @validate_tool_security("search_notes")
    @with_input_validation(validate_query_required)
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle search_notes tool call."""
        query = arguments.get("query", "")
        if not query:
            raise empty_field_error("query")

        # Extract and process parameters
        # _process_limit returns None for missing/invalid/non-positive input;
        # enforce the documented default (20) and hard cap (100) here so an
        # omitted limit never returns the entire unbounded result set.
        limit = self._process_limit(arguments.get("limit"))
        if limit is None:
            limit = 20
        limit = min(limit, 100)
        tag_filters = self._process_tag_filters(arguments.get("tags", ""))
        date_range = self._process_date_range(
            arguments.get("from_date"), arguments.get("to_date")
        )
        # Also handle typed date aliases: created_after, modified_after
        if date_range is None:
            date_range = self._process_date_range(
                arguments.get("created_after"), arguments.get("modified_after")
            )
        fuzzy = bool(arguments.get("fuzzy", False))
        sort_by = arguments.get("sort_by", "relevance")
        sort_direction = arguments.get("sort_direction", "desc")
        if sort_by not in {"relevance", "modifydate", "createdate"}:
            sort_by = "relevance"

        # Pinned filter: None = no filter, True = only pinned, False = only unpinned
        pinned_raw = arguments.get("pinned")
        pinned_filter: bool | None = None
        if pinned_raw is not None:
            pinned_filter = bool(pinned_raw)

        logger.debug(
            f"Advanced search called with: query='{query}', limit={limit}, "
            + f"tags='{tag_filters}', date_range={date_range}, fuzzy={fuzzy}, "
            + f"sort_by={sort_by}, sort_direction={sort_direction}, pinned={pinned_filter}"
        )

        try:
            return await self._execute_search(
                query,
                limit,
                tag_filters,
                date_range,
                arguments,
                fuzzy,
                sort_by,
                sort_direction,
                pinned_filter=pinned_filter,
            )
        except Exception as e:
            return self._handle_search_error(e, query)

    def _process_limit(self, limit: Any) -> int | None:
        """Process and validate limit parameter."""
        if limit is not None:
            try:
                limit = int(limit)
                if limit < 1:
                    limit = None
            except (ValueError, TypeError):
                limit = None
        return limit

    def _process_tag_filters(self, tags_input: Any) -> list[str] | None:
        """Process tag filters from input (comma-separated or list).

        Spaces are hyphenated the same way create_note/add_tags/etc. sanitize
        tags on write, so a filter like "my tag" matches a stored "my-tag".
        """
        if not tags_input:
            return None

        tag_filters = [tag for tag in self._parse_tags(tags_input) if tag]

        logger.debug(f"Tag filters: {tag_filters}")
        return tag_filters

    def _process_date_range(
        self, from_date_str: str | None, to_date_str: str | None
    ) -> tuple | None:
        """Process date range from string inputs."""
        from_date = self._parse_date(from_date_str, "from_date")
        to_date = self._parse_date(to_date_str, "to_date")

        if from_date or to_date:
            return (from_date, to_date)
        return None

    def _parse_date(self, date_str: str | None, field_name: str) -> Any:
        """Parse a date string, return None if invalid.

        Tries ISO format first, then falls back to natural language parsing
        for expressions like "yesterday", "last_week", "3_days_ago".
        """
        if not date_str:
            return None

        try:
            from datetime import datetime

            parsed_date = datetime.fromisoformat(date_str)
            logger.debug(f"{field_name}: {parsed_date}")
            return parsed_date
        except ValueError:
            # Fallback to natural language date parsing
            from .search.date_parser import parse_natural_date

            nl_text = date_str.replace("_", " ")
            parsed_date = parse_natural_date(nl_text)
            if parsed_date is not None:
                logger.debug(f"{field_name} (natural language): {parsed_date}")
                return parsed_date
            logger.warning(f"Invalid {field_name} format: {date_str}")
            return None

    async def _execute_search(
        self,
        query: str,
        limit: int | None,
        tag_filters: list[str] | None,
        date_range: tuple | None,
        arguments: dict[str, Any],
        fuzzy: bool = False,
        sort_by: str = "relevance",
        sort_direction: str = "desc",
        pinned_filter: bool | None = None,
    ) -> list[types.TextContent]:
        """Execute search using cache or API."""
        cache_initialized = (
            self.note_cache is not None and self.note_cache.is_initialized
        )
        logger.debug(
            f"Cache status for search: available={self.note_cache is not None}, initialized={cache_initialized}"
        )

        if cache_initialized:
            return await self._search_with_cache(
                query,
                limit,
                tag_filters,
                date_range,
                arguments,
                fuzzy,
                sort_by,
                sort_direction,
                pinned_filter=pinned_filter,
            )
        else:
            return await self._search_with_api(
                query,
                limit,
                tag_filters,
                date_range,
                fuzzy,
                sort_by,
                sort_direction,
            )

    def _handle_search_error(self, e: Exception, query: str) -> list[types.TextContent]:
        """Handle search errors and return appropriate response."""
        return self._format_error_response(
            e, f"searching notes for '{query}'", {"query": query}
        )

    async def _search_with_cache(
        self,
        query: str,
        limit: int | None,
        tag_filters: list[str] | None,
        date_range: tuple | None,
        arguments: dict[str, Any],
        fuzzy: bool = False,
        sort_by: str = "relevance",
        sort_direction: str = "desc",
        pinned_filter: bool | None = None,
    ) -> list[types.TextContent]:
        """Search using cache."""
        logger.debug("Using advanced search with cache")

        # Get offset parameter for pagination or default to 0
        offset = safe_get(arguments, "offset", 0)

        # Get total matching notes for pagination info
        if self.note_cache is None:
            return [types.TextContent(type="text", text="Note cache not available")]

        all_matching_notes = await self.note_cache.search_notes(
            query=query,
            tag_filters=tag_filters,
            date_range=date_range,
            fuzzy=fuzzy,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )

        # Apply pinned filter to total count
        if pinned_filter is not None:
            all_matching_notes = [
                n
                for n in all_matching_notes
                if ("pinned" in n.get("systemtags", [])) == pinned_filter
            ]
        total_matching_notes = len(all_matching_notes)

        # Use the enhanced search implementation with pagination
        notes = await self.note_cache.search_notes(
            query=query,
            limit=limit,
            offset=offset,
            tag_filters=tag_filters,
            date_range=date_range,
            fuzzy=fuzzy,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )

        # Apply pinned filter post-search
        if pinned_filter is not None:
            notes = [
                n
                for n in notes
                if ("pinned" in n.get("systemtags", [])) == pinned_filter
            ]

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
        if self.note_cache is None:
            pagination_info = {}
        else:
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
        fuzzy: bool = False,
        sort_by: str = "relevance",
        sort_direction: str = "desc",
    ) -> list[types.TextContent]:
        """Search using API fallback."""
        logger.debug("Cache not available, using API with temporary search engine")
        from .search.engine import SearchEngine

        api_search_engine = SearchEngine(fuzzy=fuzzy)

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

        # Apply date-based sort if requested
        if sort_by in ("modifydate", "createdate"):
            matching_notes.sort(
                key=lambda n: n.get(sort_by, 0) or 0,
                reverse=(sort_direction == "desc"),
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

    # _parse_tags is inherited from ToolHandlerBase


class AddTagsHandler(TagOperationHandler):
    """Handler for add_tags tool."""

    @validate_tool_security("add_tags")
    @with_input_validation(validate_note_id_required, validate_tags_required)
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle add_tags tool call."""
        note_id = arguments.get("note_id", "")
        tags_input = arguments.get("tags", "")

        if not note_id:
            raise empty_field_error("note_id")

        if not tags_input:
            raise empty_field_error("tags")

        try:
            existing_note = self._get_note_from_cache_or_api(note_id)

            # Parse the tags to add (comma-separated or list); spaces → hyphens
            tags_to_add = [tag for tag in self._parse_tags(tags_input) if tag]

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

                    final_tags = updated_note.get("tags", [])
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "success": True,
                                    "message": f"Added tags: {', '.join(added_tags)}",
                                    "note_id": updated_note.get("key"),
                                    "tags_added": added_tags,
                                    "tags_now": final_tags,
                                    "tags": final_tags,
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
                                "tags_added": [],
                                "tags_now": current_tags,
                                "tags": current_tags,
                            }
                        ),
                    )
                ]

        except Exception as e:
            return self._format_error_response(
                e, f"adding tags to note {note_id}", {"note_id": note_id}
            )


class RemoveTagsHandler(TagOperationHandler):
    """Handler for remove_tags tool."""

    @validate_tool_security("remove_tags")
    @with_input_validation(validate_note_id_required, validate_tags_required)
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle remove_tags tool call."""
        note_id = arguments.get("note_id", "")
        tags_input = arguments.get("tags", "")

        if not note_id:
            raise empty_field_error("note_id")

        if not tags_input:
            raise empty_field_error("tags")

        try:
            existing_note = self._get_note_from_cache_or_api(note_id)

            # Parse the tags to remove (comma-separated or list); spaces → hyphens,
            # so this matches the hyphenated form other handlers already stored.
            tags_to_remove = [tag for tag in self._parse_tags(tags_input) if tag]

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
                                "tags_removed": [],
                                "tags_now": [],
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

                    final_tags = updated_note.get("tags", [])
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "success": True,
                                    "message": f"Removed tags: {', '.join(removed_tags)}",
                                    "note_id": updated_note.get("key"),
                                    "tags_removed": removed_tags,
                                    "tags_now": final_tags,
                                    "tags": final_tags,
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
                                "tags_removed": [],
                                "tags_now": current_tags,
                                "tags": current_tags,
                            }
                        ),
                    )
                ]

        except Exception as e:
            return self._format_error_response(
                e, f"removing tags from note {note_id}", {"note_id": note_id}
            )


class ReplaceTagsHandler(TagOperationHandler):
    """Handler for replace_tags tool."""

    @validate_tool_security("replace_tags")
    @with_input_validation(validate_note_id_required, validate_tags_required)
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle replace_tags tool call."""
        note_id = arguments.get("note_id", "")
        tags_input = arguments.get("tags", "")

        if not note_id:
            raise empty_field_error("note_id")

        try:
            existing_note = self._get_note_from_cache_or_api(note_id)

            # Parse the new tags (comma-separated), spaces → hyphens
            new_tags = self._parse_tags(tags_input)

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

                final_tags = updated_note.get("tags", [])
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "message": message,
                                "note_id": updated_note.get("key"),
                                "tags_now": final_tags,
                                "tags": final_tags,
                            }
                        ),
                    )
                ]
            else:
                error_msg = "Failed to update note tags"
                logger.error(error_msg)
                raise NetworkError(error_msg)

        except Exception as e:
            return self._format_error_response(
                e, f"replacing tags on note {note_id}", {"note_id": note_id}
            )


class FindAndMergeDuplicatesHandler(ToolHandlerBase):
    """Handler for find_and_merge_duplicates tool."""

    @validate_tool_security("find_and_merge_duplicates")
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle find_and_merge_duplicates tool call.

        Finds duplicate notes and optionally merges them.
        """
        threshold = arguments.get("threshold", 0.8)
        dry_run = arguments.get("dry_run", True)
        tag_filter = arguments.get("tag_filter", "")

        # Validate threshold
        try:
            threshold = float(threshold)
            threshold = max(0.0, min(1.0, threshold))
        except (ValueError, TypeError):
            threshold = 0.8

        try:
            from .duplicates import DuplicateFinder

            finder = DuplicateFinder(threshold=threshold)

            # Get all notes from cache or API
            all_notes = self._get_all_notes(tag_filter)

            if not all_notes:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "message": "No notes found to check for duplicates",
                                "groups": [],
                                "total_groups": 0,
                            }
                        ),
                    )
                ]

            # Find duplicate groups
            groups = finder.find_duplicates(all_notes)

            if not groups:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "message": f"No duplicates found among {len(all_notes)} notes (threshold: {threshold})",
                                "groups": [],
                                "total_groups": 0,
                                "notes_checked": len(all_notes),
                            }
                        ),
                    )
                ]

            if dry_run:
                return self._format_dry_run_response(groups, len(all_notes), threshold)
            else:
                return await self._perform_merge(
                    groups, finder, len(all_notes), threshold
                )

        except Exception as e:
            return self._format_error_response(e, "finding duplicates")

    def _get_all_notes(self, tag_filter: str) -> list[dict[str, Any]]:
        """Get all notes, optionally filtered by tag.

        Args:
            tag_filter: Tag to filter by, or empty string for all notes.

        Returns:
            List of note dictionaries.
        """
        if self.note_cache is not None and self.note_cache.is_initialized:
            if tag_filter:
                return self.note_cache.get_all_notes(tag_filter=tag_filter)
            return self.note_cache.get_all_notes()
        else:
            # Fallback to API
            all_notes, status = self.sn.get_note_list()
            if status != 0:
                raise NetworkError("Failed to retrieve notes for duplicate check")
            notes = all_notes if isinstance(all_notes, list) else []
            if tag_filter:
                notes = [n for n in notes if tag_filter in n.get("tags", [])]
            return notes

    def _format_dry_run_response(
        self,
        groups: list[list[dict[str, Any]]],
        total_notes: int,
        threshold: float,
    ) -> list[types.TextContent]:
        """Format response for dry run mode.

        Args:
            groups: List of duplicate groups.
            total_notes: Total notes checked.
            threshold: Similarity threshold used.

        Returns:
            Formatted response.
        """
        group_summaries = []
        for i, group in enumerate(groups):
            notes_in_group = []
            for note in group:
                content = note.get("content", "")
                title = content.split("\n", 1)[0].strip()[:80] if content else ""
                notes_in_group.append(
                    {
                        "id": note.get("key", ""),
                        "title": title,
                        "similarity": note.get("_similarity", 0),
                        "tags": note.get("tags", []),
                    }
                )
            group_summaries.append(
                {
                    "group": i + 1,
                    "count": len(group),
                    "notes": notes_in_group,
                }
            )

        total_duplicates = sum(len(g) - 1 for g in groups)
        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": True,
                        "dry_run": True,
                        "message": (
                            f"Found {len(groups)} duplicate group(s) with "
                            f"{total_duplicates} duplicate note(s) that could be merged"
                        ),
                        "groups": group_summaries,
                        "total_groups": len(groups),
                        "total_duplicates": total_duplicates,
                        "notes_checked": total_notes,
                        "threshold": threshold,
                    }
                ),
            )
        ]

    async def _perform_merge(
        self,
        groups: list[list[dict[str, Any]]],
        finder: Any,
        total_notes: int,
        threshold: float,
    ) -> list[types.TextContent]:
        """Perform actual merge of duplicate groups.

        Args:
            groups: List of duplicate groups.
            finder: DuplicateFinder instance.
            total_notes: Total notes checked.
            threshold: Similarity threshold used.

        Returns:
            Formatted response with merge results.
        """
        merged_count = 0
        trashed_count = 0
        errors = []

        for group in groups:
            try:
                # Merge the group
                merged_note = finder.merge_group(group)
                winner_id = merged_note.get("key", "")

                # Update the winning note with merged tags
                updated_note, status = self.sn.update_note(merged_note)
                if status != 0:
                    errors.append(f"Failed to update note {winner_id}")
                    continue

                if isinstance(updated_note, dict):
                    self._update_cache_after_operation(updated_note, "update")

                # Trash the duplicate notes (skip the winner)
                for note in group[1:]:
                    dup_id = note.get("key", "")
                    if dup_id and dup_id != winner_id:
                        trash_result = self.sn.trash_note(dup_id)
                        # trash_note returns a tuple (note, status)
                        _trash_note, trash_status = (
                            trash_result
                            if isinstance(trash_result, tuple)
                            else (None, trash_result)
                        )
                        if trash_status == 0:
                            self._update_cache_after_operation(dup_id, "delete")
                            trashed_count += 1
                        else:
                            errors.append(f"Failed to trash note {dup_id}")

                merged_count += 1
            except Exception as e:
                errors.append(str(e))

        response: dict[str, Any] = {
            "success": True,
            "dry_run": False,
            "message": (
                f"Merged {merged_count} group(s), trashed {trashed_count} duplicate note(s)"
            ),
            "groups_merged": merged_count,
            "notes_trashed": trashed_count,
            "notes_checked": total_notes,
            "threshold": threshold,
        }
        if errors:
            response["errors"] = errors

        return [types.TextContent(type="text", text=json.dumps(response))]


class ExportNotesHandler(ToolHandlerBase):
    """Handler for export_notes tool."""

    @validate_tool_security("export_notes")
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle export_notes tool call.

        Exports one or more notes to Markdown or JSON format.
        """
        note_ids_input = arguments.get("note_ids", "")
        fmt = arguments.get("format", "markdown").lower()
        include_metadata = arguments.get("include_metadata", True)

        if not note_ids_input:
            from .error_helpers import empty_field_error

            raise empty_field_error("note_ids")

        # Parse note IDs (comma-separated)
        if isinstance(note_ids_input, list):
            note_ids = [str(nid).strip() for nid in note_ids_input if str(nid).strip()]
        elif isinstance(note_ids_input, str):
            note_ids = [
                nid.strip() for nid in safe_split(note_ids_input, ",") if nid.strip()
            ]
        else:
            note_ids = []

        if not note_ids:
            from .error_helpers import empty_field_error

            raise empty_field_error("note_ids")

        # Validate format
        if fmt not in ("markdown", "json"):
            fmt = "markdown"

        try:
            from .export import NoteExporter

            exporter = NoteExporter()
            notes = []
            errors = []

            for note_id in note_ids:
                try:
                    note = self._get_note_from_cache_or_api(note_id)
                    notes.append(note)
                except Exception:
                    errors.append(note_id)

            if not notes:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": False,
                                "message": "No notes found for the given IDs",
                                "failed_ids": errors,
                            }
                        ),
                    )
                ]

            exported = exporter.export_batch(notes, fmt, include_metadata)

            response: dict[str, Any] = {
                "success": True,
                "format": fmt,
                "count": len(notes),
                "exported": exported,
            }
            if errors:
                response["failed_ids"] = errors

            return [types.TextContent(type="text", text=json.dumps(response))]

        except Exception as e:
            return self._format_error_response(e, "exporting notes")


class AddTextHandler(ToolHandlerBase):
    """Handler for add_text tool — non-destructive append/prepend to a note."""

    @validate_tool_security("add_text")
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle add_text tool call."""
        from .errors import ValidationError

        note_id = arguments.get("note_id", "")
        text = arguments.get("text", "")
        position = arguments.get("position", "end")

        if not note_id:
            raise ValidationError("note_id is required")
        if not text:
            raise ValidationError("text is required")
        if position not in ("end", "beginning"):
            raise ValidationError(
                f"Invalid position '{position}'. Must be 'end' or 'beginning'."
            )

        try:
            existing_note = self._get_note_from_cache_or_api(note_id)
            existing_content = existing_note.get("content", "")

            if position == "end":
                new_content = (
                    f"{existing_content}\n{text}" if existing_content else text
                )
            else:
                new_content = (
                    f"{text}\n{existing_content}" if existing_content else text
                )

            existing_note["content"] = new_content
            updated_note, status = self.sn.update_note(existing_note)

            if status == 0 and isinstance(updated_note, dict):
                self._update_cache_after_operation(updated_note, "update")
                final_content = updated_note.get("content", new_content)
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "note_id": updated_note.get("key", note_id),
                                "position": position,
                                "content_length": len(final_content),
                                "tags": updated_note.get("tags", []),
                            }
                        ),
                    )
                ]
            else:
                raise NetworkError("Failed to update note after adding text")

        except Exception as e:
            return self._format_error_response(
                e, f"adding text to note {note_id}", {"note_id": note_id}
            )


class GetNoteVersionsHandler(ToolHandlerBase):
    """Handler for get_note_versions tool — retrieve version history of a note."""

    MAX_VERSIONS = 10
    PREVIEW_MAX_LENGTH = 200

    @validate_tool_security("get_note_versions")
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle get_note_versions tool call."""
        from .errors import ValidationError

        note_id = arguments.get("note_id", "")
        if not note_id:
            raise ValidationError("note_id is required")

        try:
            # Guard: a None token causes a cryptic TypeError in urllib's putheader().
            if not getattr(self.sn, "token", None):
                raise ResourceNotFoundError(
                    f"Note {note_id} not found — Simplenote is not authenticated; "
                    "API fallback unavailable. Check server logs for auth errors.",
                    resource_id=note_id,
                )
            # Get the current note to find its version number
            current_note, status = self.sn.get_note(note_id)
            if status != 0 or not isinstance(current_note, dict):
                raise ResourceNotFoundError(
                    FAILED_GET_NOTE.format(note_id=note_id), resource_id=note_id
                )

            current_version = current_note.get("version", 1)
            versions = []

            for v in range(current_version, 0, -1):
                if len(versions) >= self.MAX_VERSIONS:
                    break
                versioned_note, vstatus = self.sn.get_note(note_id, v)
                if vstatus != 0 or not isinstance(versioned_note, dict):
                    break
                content = versioned_note.get("content", "")
                if len(content) > self.PREVIEW_MAX_LENGTH:
                    preview = content[: self.PREVIEW_MAX_LENGTH] + "..."
                else:
                    preview = content
                versions.append(
                    {
                        "version": v,
                        "preview": preview,
                        "modifydate": versioned_note.get("modifydate", ""),
                    }
                )

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "note_id": note_id,
                            "total_versions": len(versions),
                            "versions": versions,
                        }
                    ),
                )
            ]

        except Exception as e:
            return self._format_error_response(
                e, f"getting versions for note {note_id}", {"note_id": note_id}
            )


class RestoreVersionHandler(ToolHandlerBase):
    """Handler for restore_version tool — roll back a note to an earlier version."""

    @validate_tool_security("restore_version")
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle restore_version tool call."""
        from .errors import ValidationError

        note_id = arguments.get("note_id", "")
        version = arguments.get("version")

        if not note_id:
            raise ValidationError("note_id is required")
        if version is None:
            raise ValidationError("version is required")

        try:
            version = int(version)
        except (TypeError, ValueError) as exc:
            from .errors import ValidationError as VE

            raise VE(f"version must be an integer, got: {version}") from exc

        try:
            versioned_note, status = self.sn.get_note(note_id, version)
            if status != 0 or not isinstance(versioned_note, dict):
                raise ResourceNotFoundError(
                    f"Could not fetch version {version} of note {note_id}",
                    resource_id=note_id,
                )

            # No-op detection: use cache only (avoids an extra API round-trip).
            # If the cache has the current content and it matches the target
            # version, skip the write entirely.
            if self.note_cache is not None and self.note_cache.is_initialized:
                cached = self.note_cache._notes.get(note_id)
                if cached is not None and versioned_note.get("content") == cached.get(
                    "content"
                ):
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "success": True,
                                    "no_op": True,
                                    "note_id": note_id,
                                    "restored_version": version,
                                    "message": "Target version is identical to current content — no write performed.",
                                }
                            ),
                        )
                    ]

            # Strip the version field so the API treats this as a new update
            restore_note = {k: v for k, v in versioned_note.items() if k != "version"}

            updated_note, ustatus = self.sn.update_note(restore_note)
            if ustatus != 0:
                raise NetworkError(
                    f"Failed to restore note {note_id} to version {version}"
                )

            if isinstance(updated_note, dict):
                self._update_cache_after_operation(updated_note, "update")

            result_note = (
                updated_note if isinstance(updated_note, dict) else restore_note
            )
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "note_id": result_note.get("key", note_id),
                            "restored_version": version,
                            "content": result_note.get("content", ""),
                            "tags": result_note.get("tags", []),
                        }
                    ),
                )
            ]

        except Exception as e:
            return self._format_error_response(
                e,
                f"restoring note {note_id} to version {version}",
                {"note_id": note_id},
            )


class ReplaceSectionHandler(ToolHandlerBase):
    """Handler for replace_section tool — surgical Markdown section replacement."""

    @validate_tool_security("replace_section")
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle replace_section tool call."""
        from .errors import ValidationError

        note_id = arguments.get("note_id", "")
        header = arguments.get("header", "")
        new_content = arguments.get("new_content", "")

        if not note_id:
            raise ValidationError("note_id is required")
        if not header:
            raise ValidationError("header is required")

        try:
            note = self._get_note_from_cache_or_api(note_id)
            content = note.get("content", "")

            # Split content into lines and find the target section
            lines = content.split("\n")
            section_start = None
            section_end = None

            # Find the section start (line matching ## <header> or # <header>)
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped == f"## {header}" or stripped == f"# {header}":
                    section_start = i
                    break

            if section_start is None:
                return self._format_error_response(
                    ResourceNotFoundError(
                        f"Section '{header}' not found in note {note_id}",
                        resource_id=note_id,
                    ),
                    f"replacing section '{header}' in note {note_id}",
                )

            # Find the end of this section (next ## or # heading or EOF)
            for i in range(section_start + 1, len(lines)):
                if lines[i].startswith("## ") or lines[i].startswith("# "):
                    section_end = i
                    break

            # Rebuild content
            header_line = lines[section_start]
            before = lines[:section_start]
            if section_end is not None:
                after = lines[section_end:]
                new_lines = before + [header_line, new_content, ""] + after
            else:
                new_lines = before + [header_line, new_content]

            updated_content = "\n".join(new_lines).rstrip("\n")

            note["content"] = updated_content
            updated_note, status = self.sn.update_note(note)
            if status != 0:
                raise NetworkError(
                    f"Failed to update note {note_id} after section replacement"
                )

            if isinstance(updated_note, dict):
                self._update_cache_after_operation(updated_note, "update")

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "note_id": note_id,
                            "header": header,
                            "content_length": len(updated_content),
                        }
                    ),
                )
            ]

        except Exception as e:
            return self._format_error_response(
                e,
                f"replacing section '{header}' in note {note_id}",
                {"note_id": note_id},
            )


class AppendToDailyNoteHandler(ToolHandlerBase):
    """Handler for append_to_daily_note tool — timestamped journaling."""

    @validate_tool_security("append_to_daily_note")
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle append_to_daily_note tool call."""
        from .errors import ValidationError

        text = arguments.get("text", "")
        if not text:
            raise ValidationError("text is required")

        today_str = date.today().isoformat()
        time_str = datetime.now().strftime("%H:%M")
        timestamped_entry = f"{time_str} {text}"

        try:
            # Find or create today's daily note
            daily_note = None
            note_id = None

            if self.note_cache is not None and self.note_cache.is_initialized:
                results = await self.note_cache.search_notes(query=today_str)
                for note in results:
                    content = note.get("content", "")
                    first_line = content.split("\n", 1)[0].strip()
                    clean = first_line.lstrip("#").strip()
                    if clean == today_str or first_line == today_str:
                        daily_note = note
                        note_id = note.get("key")
                        break

            if daily_note is None:
                # Create the daily note
                initial_content = f"# {today_str}\n{timestamped_entry}"
                new_note_data: dict[str, Any] = {"content": initial_content}
                created_note, status = self.sn.add_note(new_note_data)
                if status != 0:
                    raise NetworkError("Failed to create daily note")
                if isinstance(created_note, dict):
                    self._update_cache_after_operation(created_note, "create")
                result_note = created_note if isinstance(created_note, dict) else {}
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "note_id": result_note.get("key"),
                                "date": today_str,
                                "created": True,
                                "entry": timestamped_entry,
                            }
                        ),
                    )
                ]
            else:
                # Append to existing daily note
                existing_content = daily_note.get("content", "")
                new_content = f"{existing_content}\n{timestamped_entry}"
                daily_note = dict(daily_note)
                daily_note["content"] = new_content
                updated_note, ustatus = self.sn.update_note(daily_note)
                if ustatus != 0:
                    raise NetworkError("Failed to update daily note")
                if isinstance(updated_note, dict):
                    self._update_cache_after_operation(updated_note, "update")
                result_note = (
                    updated_note if isinstance(updated_note, dict) else daily_note
                )
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "note_id": result_note.get("key", note_id),
                                "date": today_str,
                                "created": False,
                                "entry": timestamped_entry,
                            }
                        ),
                    )
                ]

        except Exception as e:
            return self._format_error_response(
                e, f"appending to daily note for {today_str}"
            )


class GetOrCreateNoteHandler(ToolHandlerBase):
    """Handler for get_or_create_note tool — atomic find-or-create."""

    @validate_tool_security("get_or_create_note")
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle get_or_create_note tool call."""
        from .errors import ValidationError

        title = arguments.get("title", "")
        default_content = arguments.get("content", "")
        tags_input = arguments.get("tags", [])

        if not title:
            raise ValidationError("title is required")

        tags = self._parse_tags(tags_input) if tags_input else []

        try:
            # Search for an existing note with this title
            existing = None
            if self.note_cache is not None and self.note_cache.is_initialized:
                results = await self.note_cache.search_notes(query=title)
                for note in results:
                    content = note.get("content", "")
                    first_line = content.split("\n", 1)[0].strip()
                    # Match by first line (title), strip markdown heading prefix
                    clean_first = first_line.lstrip("#").strip()
                    if clean_first == title or first_line == title:
                        existing = note
                        break

            if existing is not None:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "created": False,
                                "note_id": existing.get("key"),
                                "content": existing.get("content", ""),
                                "tags": existing.get("tags", []),
                            }
                        ),
                    )
                ]

            # Not found — create a new note
            content = default_content if default_content else f"# {title}\n"
            note_data: dict[str, Any] = {"content": content}
            if tags:
                note_data["tags"] = tags

            loop = asyncio.get_running_loop()
            try:
                created_note, status = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: self.sn.add_note(note_data)),
                    timeout=30.0,
                )
            except TimeoutError as exc:
                raise NetworkError(
                    "get_or_create_note timed out waiting for Simplenote API"
                ) from exc
            if status != 0:
                raise NetworkError("Failed to create note in get_or_create_note")

            if isinstance(created_note, dict):
                self._update_cache_after_operation(created_note, "create")

            result_note = created_note if isinstance(created_note, dict) else {}
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "created": True,
                            "note_id": result_note.get("key"),
                            "content": result_note.get("content", content),
                            "tags": result_note.get("tags", tags),
                        }
                    ),
                )
            ]

        except Exception as e:
            return self._format_error_response(e, f"get_or_create_note for '{title}'")


class RenameTagHandler(ToolHandlerBase):
    """Handler for rename_tag tool — atomically rename a tag across all notes."""

    @validate_tool_security("rename_tag")
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle rename_tag tool call."""
        from .errors import ValidationError

        old_tag = arguments.get("old_tag", "")
        new_tag = arguments.get("new_tag", "")
        dry_run = bool(arguments.get("dry_run", False))

        if not old_tag:
            raise ValidationError("old_tag is required")
        if not new_tag:
            raise ValidationError("new_tag is required")

        # Sanitize: spaces to hyphens (shared with every other tag-accepting tool)
        new_tag = self._parse_tags([new_tag])[0]
        old_tag = old_tag.strip()

        try:
            # Find notes that have the old tag
            note_ids: set[str] = set()
            if self.note_cache is not None and self.note_cache.is_initialized:
                note_ids = self.note_cache._tag_index.get(old_tag, set())

            if not note_ids:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "updated_count": 0,
                                "note_ids": [],
                                "dry_run": dry_run,
                                "message": f"Tag '{old_tag}' not found on any notes",
                            }
                        ),
                    )
                ]

            updated_ids = []
            errors = []

            for note_id in note_ids:
                note = None
                if self.note_cache is not None and self.note_cache.is_initialized:
                    note = self.note_cache._notes.get(note_id)
                if note is None:
                    note_data, status = self.sn.get_note(note_id)
                    if status != 0 or not isinstance(note_data, dict):
                        errors.append(note_id)
                        continue
                    note = note_data

                current_tags = list(note.get("tags", []))
                if old_tag not in current_tags:
                    continue

                new_tags = [new_tag if t == old_tag else t for t in current_tags]

                if not dry_run:
                    note_copy = dict(note)
                    note_copy["tags"] = new_tags
                    updated, ustatus = self.sn.update_note(note_copy)
                    if ustatus == 0 and isinstance(updated, dict):
                        self._update_cache_after_operation(updated, "update")
                        updated_ids.append(note_id)
                    else:
                        errors.append(note_id)
                else:
                    updated_ids.append(note_id)

            response: dict[str, Any] = {
                "success": True,
                "updated_count": len(updated_ids),
                "note_ids": sorted(updated_ids),
                "dry_run": dry_run,
                "old_tag": old_tag,
                "new_tag": new_tag,
            }
            if errors:
                response["failed_ids"] = errors

            return [types.TextContent(type="text", text=json.dumps(response))]

        except Exception as e:
            return self._format_error_response(
                e, f"renaming tag '{old_tag}' to '{new_tag}'"
            )


class ListTagsHandler(ToolHandlerBase):
    """Handler for list_tags tool — list all tags with note counts."""

    @validate_tool_security("list_tags")
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle list_tags tool call."""
        sort_by = arguments.get("sort_by", "alpha")

        if self.note_cache is None or not self.note_cache.is_initialized:
            return self._format_error_response(
                InternalError("Note cache is not initialized. Cannot list tags."),
                "listing tags",
            )

        try:
            tag_index = self.note_cache._tag_index
            tags = [
                {"tag": tag, "note_count": len(note_ids)}
                for tag, note_ids in tag_index.items()
            ]

            if sort_by == "count":
                tags.sort(key=lambda t: t["note_count"], reverse=True)
            else:
                tags.sort(key=lambda t: t["tag"])

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "tags": tags,
                            "total_tags": len(tags),
                            "sort_by": sort_by,
                        }
                    ),
                )
            ]

        except Exception as e:
            return self._format_error_response(e, "listing tags")


class FindUntaggedNotesHandler(ToolHandlerBase):
    """Handler for find_untagged_notes tool — list notes with no tags."""

    @validate_tool_security("find_untagged_notes")
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle find_untagged_notes tool call."""
        if self.note_cache is None or not self.note_cache.is_initialized:
            return self._format_error_response(
                InternalError(
                    "Note cache is not initialized. Cannot find untagged notes."
                ),
                "finding untagged notes",
            )

        try:
            limit = arguments.get("limit", 50)
            try:
                limit = int(limit)
                if limit <= 0:
                    limit = 50
            except (TypeError, ValueError):
                limit = 50

            untagged = self.note_cache._filter_notes_by_untagged()
            notes_list = list(untagged.values())[:limit]

            results = []
            for note in notes_list:
                content = note.get("content", "")
                snippet = content[:100].replace("\n", " ") if content else ""
                results.append(
                    {
                        "id": note.get("key", ""),
                        "title": extract_title_from_content(
                            content, note.get("key", "")
                        ),
                        "snippet": snippet,
                        "tags": note.get("tags", []),
                    }
                )

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "notes": results,
                            "count": len(results),
                        }
                    ),
                )
            ]

        except Exception as e:
            return self._format_error_response(e, "finding untagged notes")


class BulkTagHandler(ToolHandlerBase):
    """Handler for bulk_tag tool — add/remove/set tags on multiple notes at once."""

    VALID_ACTIONS = {"add", "remove", "set"}

    @validate_tool_security("bulk_tag")
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle bulk_tag tool call."""
        note_ids = arguments.get("note_ids")
        action = arguments.get("action")
        tags_input = arguments.get("tags", [])

        if not note_ids:
            return self._format_error_response(
                ValueError("note_ids is required"),
                "bulk tagging notes",
            )
        if not action:
            return self._format_error_response(
                ValueError("action is required (add, remove, or set)"),
                "bulk tagging notes",
            )
        if action not in self.VALID_ACTIONS:
            return self._format_error_response(
                ValueError(
                    f"Unknown action '{action}'. Must be one of: "
                    f"{', '.join(sorted(self.VALID_ACTIONS))}"
                ),
                "bulk tagging notes",
            )

        tags = self._parse_tags(tags_input)

        updated = 0
        failed: list[str] = []

        for note_id in note_ids:
            try:
                note_data, status = self.sn.get_note(note_id)
                if status != 0:
                    failed.append(note_id)
                    continue

                current_tags: list[str] = note_data.get("tags") or []

                if action == "add":
                    new_tags = list(dict.fromkeys(current_tags + tags))
                elif action == "remove":
                    new_tags = [t for t in current_tags if t not in tags]
                else:  # set
                    new_tags = tags

                note_data["tags"] = new_tags
                _, upd_status = self.sn.update_note(note_data)
                if upd_status == 0:
                    updated += 1
                    if self.note_cache:
                        self.note_cache._notes[note_id] = note_data
                else:
                    failed.append(note_id)

            except Exception:
                failed.append(note_id)

        response: dict[str, Any] = {
            "success": True,
            "action": action,
            "updated": updated,
            "failed": failed,
        }

        return [types.TextContent(type="text", text=json.dumps(response))]


class RestoreNoteHandler(ToolHandlerBase):
    """Handler for restore_note tool — un-trash a deleted note."""

    @validate_tool_security("restore_note")
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle restore_note tool call."""
        note_id = arguments.get("note_id", "")

        if not note_id:
            return self._format_error_response(
                ValueError("note_id is required"),
                "restoring note",
            )

        try:
            note_data, status = self.sn.get_note(note_id)
            if status != 0:
                raise ResourceNotFoundError(
                    f"Note {note_id} not found", resource_id=note_id
                )

            if not note_data.get("deleted", False):
                # Note is already active — no-op
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "note_id": note_id,
                                "message": "Note was not in trash; no changes made.",
                            }
                        ),
                    )
                ]

            note_data["deleted"] = False
            updated_note, upd_status = self.sn.update_note(note_data)
            if upd_status != 0:
                raise NetworkError(f"Failed to restore note {note_id}")

            if self.note_cache:
                self.note_cache.update_cache_after_update(updated_note)

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "note_id": note_id,
                            "message": "Note restored from trash successfully.",
                        }
                    ),
                )
            ]

        except Exception as e:
            return self._format_error_response(
                e, f"restoring note {note_id}", {"note_id": note_id}
            )


class PublishNoteHandler(ToolHandlerBase):
    """Handler for publish_note tool — publish a note to a public URL."""

    @validate_tool_security("publish_note")
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle publish_note tool call."""
        note_id = arguments.get("note_id", "")

        if not note_id:
            return self._format_error_response(
                ValueError("note_id is required"),
                "publishing note",
            )

        try:
            note_data = self._get_note_from_cache_or_api(note_id)

            system_tags: list[str] = list(note_data.get("systemTags") or [])
            if "published" not in system_tags:
                system_tags.append("published")
            note_data["systemTags"] = system_tags

            updated_note, status = self.sn.update_note(note_data)
            if status != 0:
                raise NetworkError(f"Failed to publish note {note_id}")

            self._update_cache_after_operation(updated_note, "update")

            public_url = updated_note.get("publishURL", "") if updated_note else ""

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "note_id": note_id,
                            "public_url": public_url,
                            "message": "Note published successfully.",
                        }
                    ),
                )
            ]

        except Exception as e:
            return self._format_error_response(
                e, f"publishing note {note_id}", {"note_id": note_id}
            )


class UnpublishNoteHandler(ToolHandlerBase):
    """Handler for unpublish_note tool — remove a note from public access."""

    @validate_tool_security("unpublish_note")
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle unpublish_note tool call."""
        note_id = arguments.get("note_id", "")

        if not note_id:
            return self._format_error_response(
                ValueError("note_id is required"),
                "unpublishing note",
            )

        try:
            note_data = self._get_note_from_cache_or_api(note_id)

            system_tags: list[str] = list(note_data.get("systemTags") or [])
            if "published" not in system_tags:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "note_id": note_id,
                                "message": "Note was not published; no changes made.",
                            }
                        ),
                    )
                ]

            system_tags = [t for t in system_tags if t != "published"]
            note_data["systemTags"] = system_tags

            updated_note, status = self.sn.update_note(note_data)
            if status != 0:
                raise NetworkError(f"Failed to unpublish note {note_id}")

            self._update_cache_after_operation(updated_note, "update")

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "note_id": note_id,
                            "message": "Note unpublished successfully.",
                        }
                    ),
                )
            ]

        except Exception as e:
            return self._format_error_response(
                e, f"unpublishing note {note_id}", {"note_id": note_id}
            )


class GetServerInfoHandler(ToolHandlerBase):
    """Handler for get_server_info tool — returns version, author, and debug info."""

    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle get_server_info tool call."""
        import platform
        import sys

        import simplenote_mcp

        from .server import get_last_auth_error

        config = get_config()
        registry = ToolHandlerRegistry()

        authenticated = bool(getattr(self.sn, "token", None))
        last_sync_error = get_last_auth_error()

        cache_initialized = bool(self.note_cache and self.note_cache.is_initialized)
        note_count: int | None = None
        if cache_initialized and self.note_cache is not None:
            try:
                note_count = len(self.note_cache._notes)
            except Exception:
                note_count = None

        # cache_initialized is honest: True only when auth succeeded and notes loaded.
        cache_healthy = cache_initialized and (note_count is None or note_count > 0)

        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": True,
                        "name": "simplenote-mcp-server",
                        "version": simplenote_mcp.__version__,
                        "author": "Thomas Juul Dyhr",
                        "description": "MCP server integrating Simplenote with Claude Desktop",
                        "tool_count": len(registry.list_tools()),
                        "debug": {
                            "python_version": sys.version,
                            "platform": platform.platform(),
                            "authenticated": authenticated,
                            "cache_initialized": cache_initialized,
                            "cache_healthy": cache_healthy,
                            "note_count": note_count,
                            "last_sync_error": last_sync_error,
                            "sync_interval_seconds": config.sync_interval_seconds,
                            "log_level": config.log_level.value
                            if hasattr(config.log_level, "value")
                            else str(config.log_level),
                            "offline_mode": config.offline_mode,
                            "cache_max_size": config.cache_max_size,
                        },
                    }
                ),
            )
        ]


class PermanentDeleteNoteHandler(ToolHandlerBase):
    """Handler for permanent_delete_note tool — irreversibly destroy a note."""

    @validate_tool_security("permanent_delete_note")
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle permanent_delete_note tool call.

        Args:
            arguments: Must contain ``note_id`` (str) and ``confirm`` (bool).
                       If ``confirm`` is False a dry-run description is returned
                       and no data is modified.
        """
        note_id = arguments.get("note_id", "")
        confirm = bool(arguments.get("confirm", False))

        if not note_id:
            return self._format_error_response(
                ValueError("note_id is required"),
                "permanently deleting note",
            )

        if not confirm:
            # Dry-run: describe what would happen without doing it.
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "dry_run": True,
                            "note_id": note_id,
                            "message": (
                                f"DRY RUN: Note '{note_id}' would be permanently and "
                                "irreversibly deleted. Pass confirm=true to execute. "
                                "This operation CANNOT be undone."
                            ),
                        }
                    ),
                )
            ]

        try:
            # Verify note exists before attempting deletion
            _ = self._get_note_from_cache_or_api(note_id)

            result = self.sn.delete_note(note_id)
            _data, status = result if isinstance(result, tuple) else (None, result)

            if status == 0:
                self._update_cache_after_operation(note_id, "delete")
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "note_id": note_id,
                                "message": "Note permanently deleted.",
                            }
                        ),
                    )
                ]
            else:
                raise NetworkError(f"Failed to permanently delete note {note_id}")

        except Exception as e:
            return self._format_error_response(
                e,
                f"permanently deleting note {note_id}",
                {"note_id": note_id},
            )


class EmptyTrashHandler(ToolHandlerBase):
    """Handler for empty_trash tool — permanently delete all trashed notes."""

    @validate_tool_security("empty_trash")
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle empty_trash tool call.

        Args:
            arguments: Optional ``dry_run`` (bool, default True) and
                       ``confirm`` (bool, default False).
                       The trash is only emptied when ``dry_run=False`` AND
                       ``confirm=True``; otherwise a preview is returned.
        """
        dry_run = bool(arguments.get("dry_run", True))
        confirm = bool(arguments.get("confirm", False))

        try:
            trashed_notes = self._get_trashed_notes()

            if not trashed_notes:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "dry_run": dry_run or not confirm,
                                "trashed_count": 0,
                                "deleted_count": 0,
                                "message": "Trash is already empty.",
                            }
                        ),
                    )
                ]

            note_summaries = [
                {
                    "note_id": n.get("key", ""),
                    "title": extract_title_from_content(
                        n.get("content", ""), n.get("key", "")
                    ),
                }
                for n in trashed_notes
            ]

            if dry_run or not confirm:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "dry_run": True,
                                "trashed_count": len(trashed_notes),
                                "deleted_count": 0,
                                "notes": note_summaries,
                                "message": (
                                    f"DRY RUN: {len(trashed_notes)} note(s) in trash would be "
                                    "permanently deleted. Pass dry_run=false and confirm=true to execute. "
                                    "This operation CANNOT be undone."
                                ),
                            }
                        ),
                    )
                ]

            # Execute: permanently delete every trashed note.
            deleted_count = 0
            failed_ids: list[str] = []

            for note in trashed_notes:
                note_id = note.get("key", "")
                if not note_id:
                    continue
                try:
                    result = self.sn.delete_note(note_id)
                    _data, status = (
                        result if isinstance(result, tuple) else (None, result)
                    )
                    if status == 0:
                        self._update_cache_after_operation(note_id, "delete")
                        deleted_count += 1
                    else:
                        logger.error(
                            f"Failed to permanently delete trashed note {note_id}"
                        )
                        failed_ids.append(note_id)
                except Exception as exc:
                    logger.error(f"Error deleting trashed note {note_id}: {exc}")
                    failed_ids.append(note_id)

            response: dict[str, Any] = {
                "success": True,
                "dry_run": False,
                "trashed_count": len(trashed_notes),
                "deleted_count": deleted_count,
                "message": f"Permanently deleted {deleted_count} note(s) from trash.",
            }
            if failed_ids:
                response["failed_ids"] = failed_ids

            return [types.TextContent(type="text", text=json.dumps(response))]

        except Exception as e:
            return self._format_error_response(e, "emptying trash")

    def _get_trashed_notes(self) -> list[dict[str, Any]]:
        """Return all notes that are currently in the trash.

        Checks the in-memory cache first; falls back to the API.
        A note is considered trashed when ``note.get("deleted")`` is truthy.
        """
        if self.note_cache is not None and self.note_cache.is_initialized:
            return [
                note for note in self.note_cache._notes.values() if note.get("deleted")
            ]

        # Fallback: fetch from API with deleted notes included
        all_notes, status = self.sn.get_note_list()
        if status != 0:
            raise NetworkError("Failed to retrieve note list for empty_trash")
        notes = all_notes if isinstance(all_notes, list) else []
        return [n for n in notes if n.get("deleted")]


class ListNotesHandler(ToolHandlerBase):
    """Handler for list_notes tool — browse recent notes, optionally by tag."""

    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle list_notes tool call."""
        tag: str | None = arguments.get("tag")
        limit = min(int(arguments.get("limit", 20)), 100)
        include_deleted: bool = bool(arguments.get("include_deleted", False))

        try:
            if self.note_cache is not None and self.note_cache.is_initialized:
                notes = list(self.note_cache._notes.values())
            else:
                all_notes, status = self.sn.get_note_list()
                if status != 0:
                    raise NetworkError("Failed to retrieve note list")
                notes = all_notes if isinstance(all_notes, list) else []

            if not include_deleted:
                notes = [n for n in notes if not n.get("deleted")]
            if tag:
                notes = [
                    n
                    for n in notes
                    if tag.lower() in [t.lower() for t in (n.get("tags") or [])]
                ]

            # Sort: pinned first, then by modification date descending.
            notes.sort(
                key=lambda n: (
                    not bool(
                        n.get("systemTags") and "pinned" in n.get("systemTags", [])
                    ),
                    -(float(n.get("modifydate", 0)) if n.get("modifydate") else 0),
                )
            )
            notes = notes[:limit]

            results = []
            for note in notes:
                content = note.get("content", "") or ""
                first_line = content.split("\n")[0].strip()[:60] if content else ""
                results.append(
                    {
                        "id": note.get("key", ""),
                        "title": first_line,
                        "tags": note.get("tags", []),
                        "modified": note.get("modifydate", ""),
                        "deleted": bool(note.get("deleted")),
                    }
                )

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {"notes": results, "count": len(results), "limit": limit}
                    ),
                )
            ]

        except Exception as e:
            return self._format_error_response(e, "listing notes")


class ToolHandlerRegistry:
    """Registry for tool handlers."""

    def __init__(self) -> None:
        """Initialize the registry."""
        self._handlers: dict[str, type[ToolHandlerBase]] = {
            "create_note": CreateNoteHandler,
            "update_note": UpdateNoteHandler,
            "delete_note": DeleteNoteHandler,
            "get_note": GetNoteHandler,
            "list_notes": ListNotesHandler,
            "search_notes": SearchNotesHandler,
            "add_tags": AddTagsHandler,
            "remove_tags": RemoveTagsHandler,
            "replace_tags": ReplaceTagsHandler,
            "export_notes": ExportNotesHandler,
            "find_and_merge_duplicates": FindAndMergeDuplicatesHandler,
            "add_text": AddTextHandler,
            "list_tags": ListTagsHandler,
            "get_note_versions": GetNoteVersionsHandler,
            "restore_version": RestoreVersionHandler,
            "rename_tag": RenameTagHandler,
            "get_or_create_note": GetOrCreateNoteHandler,
            "append_to_daily_note": AppendToDailyNoteHandler,
            "replace_section": ReplaceSectionHandler,
            "find_untagged_notes": FindUntaggedNotesHandler,
            "bulk_tag": BulkTagHandler,
            "restore_note": RestoreNoteHandler,
            "publish_note": PublishNoteHandler,
            "unpublish_note": UnpublishNoteHandler,
            "get_server_info": GetServerInfoHandler,
            "permanent_delete_note": PermanentDeleteNoteHandler,
            "empty_trash": EmptyTrashHandler,
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
