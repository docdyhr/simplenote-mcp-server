"""The search_notes tool handler."""

import json
from typing import Any

import mcp.types as types

from ..config import get_config
from ..decorators import (
    validate_query_required,
    with_input_validation,
)
from ..error_helpers import (
    empty_field_error,
)
from ..errors import (
    NetworkError,
)
from ..logging import logger
from ..security import validate_tool_security
from ..utils.common import (
    safe_get,
)
from ..vault import (
    VAULT_TAG,
)
from .base import (
    FAILED_RETRIEVE_NOTES,
    ToolHandlerBase,
    extract_title_from_content,
)


class SearchNotesHandler(ToolHandlerBase):
    """Handler for search_notes tool."""

    @validate_tool_security("search_notes")
    @with_input_validation(validate_query_required)
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
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
            from ..search.date_parser import parse_natural_date

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

    def _handle_search_error(self, e: Exception, query: str) -> types.CallToolResult:
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
                    "encrypted": VAULT_TAG in (note.get("tags") or []),
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
        from ..search.engine import SearchEngine

        api_search_engine = SearchEngine(fuzzy=fuzzy)

        # Get all notes from the API
        all_notes, status = self.sn.get_note_list()

        if status != 0:
            logger.error(FAILED_RETRIEVE_NOTES)
            raise NetworkError(FAILED_RETRIEVE_NOTES)

        # Convert list to dictionary for search engine. Vault-encrypted note
        # bodies are ciphertext, never searchable — substitute title-only
        # content for such notes before handing them to the engine, mirroring
        # NoteCache.search_notes()'s snapshot substitution (this API fallback
        # path bypasses the cache entirely, so it needs its own copy of the
        # same guard).
        notes_dict = {
            note.get("key"): (
                {**note, "content": (note.get("content") or "").split("\n", 1)[0]}
                if VAULT_TAG in (note.get("tags") or [])
                else note
            )
            for note in all_notes
            if note.get("key")
        }

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
                    "encrypted": VAULT_TAG in (note.get("tags") or []),
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
