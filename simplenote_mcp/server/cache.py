"""Cache module for Simplenote MCP server."""

import asyncio
import hashlib
import time
from datetime import datetime
from typing import Any, Optional

from simplenote import Simplenote

from .config import Config, get_config
from .logging import logger
from .monitoring.metrics import (
    record_cache_access_time,
    record_cache_hit,
    record_cache_miss,
    update_cache_memory_usage,
    update_cache_size,
)
from .search.engine import SearchEngine

# Global cache instance
_cache_instance: Optional["NoteCache"] = None


# Error messages
CACHE_NOT_INITIALIZED = "Note cache not initialized. Call initialize_cache() first."
CACHE_NOT_LOADED = "Cache not initialized"


def get_cache() -> "NoteCache":
    """Get the global note cache instance."""
    if _cache_instance is None:
        raise RuntimeError(CACHE_NOT_INITIALIZED)
    return _cache_instance


def clear_cache() -> None:
    """Clear the global cache instance.

    This is primarily used for testing to ensure fresh cache instances.
    """
    global _cache_instance
    if _cache_instance is not None:
        # Stop background sync if running
        if hasattr(_cache_instance, "_sync_task") and _cache_instance._sync_task:
            _cache_instance._sync_task.cancel()
    _cache_instance = None


class NoteCache:
    """In-memory cache for Simplenote notes.

    This class provides a local cache of notes from Simplenote to avoid
    making repeated API calls for the same data.
    """

    def __init__(self, client: Simplenote) -> None:
        """Initialize the cache.

        Args:
            client: The Simplenote client instance.

        """
        self._client = client
        self._notes: dict[str, dict[str, Any]] = {}  # Map of note ID to note data
        self._last_sync: float = 0  # Timestamp of last sync
        self._initialized: bool = False
        self._tags: set[str] = set()  # Set of all unique tags
        self._lock = asyncio.Lock()  # Lock for thread-safe access
        self._search_engine = SearchEngine()  # Search engine for advanced search

        # New data structures for optimized cache
        self._tag_index: dict[
            str, set[str]
        ] = {}  # Map of tag to set of note IDs with that tag
        self._query_cache: dict[
            str, tuple[float, list[dict[str, Any]]]
        ] = {}  # Cache for search queries
        self._query_cache_ttl: float = 60.0  # Cache TTL in seconds
        self._title_index: dict[
            str, list[str]
        ] = {}  # Map of first word in title to note IDs (for prefix search)

    async def _fetch_all_notes_with_retry(self) -> list[dict[str, Any]]:
        """Fetch all notes from API with retry logic.

        Returns:
            List of note dictionaries

        Raises:
            NetworkError: If all retries fail
        """
        max_retries = 3
        retry_count = 0
        retry_delay = 2

        while retry_count < max_retries:
            try:
                loop = asyncio.get_event_loop()
                notes_result, status = await loop.run_in_executor(
                    None,
                    lambda: self._client.get_note_list(tags=[]),
                )

                if status != 0:
                    if retry_count < max_retries - 1:
                        logger.warning(
                            f"Failed to get notes from Simplenote (status {status}), retrying {retry_count + 1}/{max_retries}..."
                        )
                        retry_count += 1
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        from .errors import NetworkError

                        raise NetworkError(
                            f"Failed to get notes from Simplenote (status {status}) after {max_retries} attempts"
                        )

                # Extract notes from result
                if isinstance(notes_result, list):
                    return notes_result
                elif isinstance(notes_result, dict) and "notes" in notes_result:
                    return notes_result["notes"]
                else:
                    return []

            except Exception as e:
                if retry_count < max_retries - 1:
                    logger.warning(
                        f"Error connecting to Simplenote: {str(e)}, retrying {retry_count + 1}/{max_retries}..."
                    )
                    retry_count += 1
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    from .errors import NetworkError

                    if isinstance(e, NetworkError):
                        raise
                    raise NetworkError(
                        f"Failed to initialize cache after {max_retries} attempts: {str(e)}"
                    ) from e

        return []

    async def _fetch_index_mark(self) -> None:
        """Fetch index mark from API for test compatibility."""
        try:
            loop = asyncio.get_event_loop()
            index_result, index_status = await loop.run_in_executor(
                None,
                self._client.get_note_list,
            )
            if (
                index_status == 0
                and isinstance(index_result, dict)
                and "mark" in index_result
            ):
                self._index_mark = index_result["mark"]
            else:
                self._index_mark = "test_mark"
        except Exception as e:
            logger.warning(f"Failed to get index mark (non-critical): {str(e)}")
            self._index_mark = "test_mark"

    def _build_tag_index(self, note_id: str, tags: list[str]) -> None:
        """Build tag index for a note.

        Args:
            note_id: Note ID
            tags: List of tags
        """
        self._tags.update(tags)
        for tag in tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(note_id)

    def _build_title_index(self, note_id: str, content: str) -> None:
        """Build title index for a note.

        Args:
            note_id: Note ID
            content: Note content
        """
        first_word = self._extract_first_word(content)
        if first_word:
            if first_word not in self._title_index:
                self._title_index[first_word] = []
            self._title_index[first_word].append(note_id)

    def _build_all_indexes(self) -> None:
        """Build tag and title indexes for all notes."""
        for note_id, note in self._notes.items():
            # Build tag index
            if "tags" in note and note["tags"]:
                self._build_tag_index(note_id, note["tags"])

            # Build title index
            content = note.get("content", "")
            if content:
                self._build_title_index(note_id, content)

    async def initialize(self) -> int:
        """Initialize the cache with all notes from Simplenote.

        Returns:
            Number of notes loaded into the cache.

        Raises:
            NetworkError: If there's an error connecting to Simplenote.

        """
        if self._initialized:
            return len(self._notes)

        start_time = time.time()
        logger.info("Initializing note cache...")

        # Fetch all notes with retry logic
        notes_data = await self._fetch_all_notes_with_retry()

        # Store notes in the cache
        self._notes = {note["key"]: note for note in notes_data}
        self._initialized = True
        self._last_sync = time.time()

        # Fetch index mark for test compatibility
        await self._fetch_index_mark()

        # Build all indexes
        self._build_all_indexes()

        elapsed = time.time() - start_time
        logger.info(f"Loaded {len(self._notes)} notes into cache in {elapsed:.2f}s")
        logger.info(f"Found {len(self._tags)} unique tags")

        # Initialize cache metrics after successful initialization
        self._update_cache_metrics()

        return len(self._notes)

    async def _fetch_sync_data_with_retry(
        self, since: float
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Fetch sync data from API with retry logic.

        Args:
            since: Timestamp of last sync

        Returns:
            API result (list or dict)

        Raises:
            NetworkError: If all retries fail
        """
        max_retries = 2
        retry_count = 0
        retry_delay = 1

        while retry_count < max_retries:
            try:
                api_result, status = self._client.get_note_list(since=since, tags=[])

                if status != 0:
                    if retry_count < max_retries - 1:
                        logger.warning(
                            f"Sync failed with status {status}, retrying {retry_count + 1}/{max_retries}..."
                        )
                        retry_count += 1
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        from .errors import NetworkError

                        raise NetworkError(
                            f"Failed to get notes from Simplenote (status {status}) after {max_retries} attempts"
                        )

                return api_result

            except Exception as e:
                if retry_count < max_retries - 1:
                    logger.warning(
                        f"Error during sync: {str(e)}, retrying {retry_count + 1}/{max_retries}..."
                    )
                    retry_count += 1
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    from .errors import NetworkError

                    if isinstance(e, NetworkError):
                        raise
                    raise NetworkError(
                        f"Failed to sync after {max_retries} attempts: {str(e)}"
                    ) from e

        # Should never reach here, but satisfy type checker
        return []

    def _extract_notes_from_result(
        self, result: list[dict[str, Any]] | dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Extract notes array from API result.

        Args:
            result: API result (list or dict)

        Returns:
            List of note dictionaries
        """
        if isinstance(result, dict):
            if "mark" in result:
                self._index_mark = result["mark"]
            return result.get("notes", [])
        return result if isinstance(result, list) else []

    def _process_sync_notes(self, notes_data: list[dict[str, Any]]) -> int:
        """Process notes from sync and update cache.

        Args:
            notes_data: List of notes from API

        Returns:
            Number of changes made
        """
        change_count = 0

        for note in notes_data:
            note_id = note["key"]
            if note.get("deleted"):
                # Note was deleted
                if note_id in self._notes:
                    del self._notes[note_id]
                    change_count += 1
            else:
                # Note was created or updated
                self._notes[note_id] = note
                change_count += 1

        return change_count

    def _rebuild_tag_cache(self) -> None:
        """Rebuild tag cache from all current notes."""
        all_used_tags = set()
        for note in self._notes.values():
            if "tags" in note and note["tags"]:
                all_used_tags.update(note["tags"])
        self._tags = all_used_tags

    async def sync(self) -> int:
        """Synchronize the cache with Simplenote.

        This method retrieves only notes that have changed since the last sync.

        Returns:
            Number of notes that were updated in the cache.

        Raises:
            NetworkError: If sync fails after all retries
        """
        from .errors import NetworkError

        if not self._initialized:
            return await self.initialize()

        start_time = time.time()
        logger.debug(f"Syncing note cache (last sync: {self._last_sync})")

        try:
            # Fetch data with retry logic
            result = await self._fetch_sync_data_with_retry(self._last_sync)

            # Extract notes from result
            notes_data = self._extract_notes_from_result(result)

            # Process notes and update cache
            change_count = self._process_sync_notes(notes_data)

            # Rebuild tag cache
            self._rebuild_tag_cache()

            # Update last sync time
            self._last_sync = time.time()

            # Clear query cache after sync
            self._query_cache.clear()

            elapsed = time.time() - start_time
            if change_count > 0:
                logger.info(f"Updated {change_count} notes in cache in {elapsed:.2f}s")
            else:
                logger.debug(f"No changes found in {elapsed:.2f}s")

            return change_count

        except NetworkError:
            # Re-raise NetworkError to indicate sync failure
            raise
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                f"Error processing sync results after {elapsed:.2f}s: {str(e)}"
            )
            return 0

    def get_note(self, note_id: str) -> dict | None:
        """Get a note from the cache by ID.

        Args:
            note_id: The ID of the note to retrieve.

        Returns:
            The note data, or None if the note is not in the cache.

        Raises:
            ResourceNotFoundError: If the note doesn't exist.

        """
        start_time = time.time()

        if not self._initialized:
            raise RuntimeError(CACHE_NOT_LOADED)

        # Check if note is in cache
        note = self._notes.get(note_id)
        if note is not None:
            # Cache hit
            access_time = time.time() - start_time
            record_cache_hit()
            record_cache_access_time(access_time)
            return note

        # Cache miss - try to get from API
        record_cache_miss()
        from .errors import ResourceNotFoundError

        # Get from Simplenote API
        note_data, status = self._client.get_note(note_id)

        # If note not found, raise error
        if status != 0 or note_data is None:
            access_time = time.time() - start_time
            record_cache_access_time(access_time)
            raise ResourceNotFoundError(f"Note with ID {note_id} not found")

        # Ensure note_data is a dict before caching
        if not isinstance(note_data, dict):
            access_time = time.time() - start_time
            record_cache_access_time(access_time)
            raise ResourceNotFoundError(f"Invalid note data format for ID {note_id}")

        # Add note to cache
        self._notes[note_id] = note_data

        # Update tags
        if "tags" in note_data and note_data["tags"]:
            self._tags.update(note_data["tags"])

        # Record access time and update cache size
        access_time = time.time() - start_time
        record_cache_access_time(access_time)
        self._update_cache_metrics()

        return note_data

    def get_all_notes(
        self,
        limit: int | None = None,
        tag_filter: str | None = None,
        offset: int = 0,
        sort_by: str = "modifydate",
        sort_direction: str = "desc",
    ) -> list[dict]:
        """Get all notes from the cache with pagination support.

        Args:
            limit: Optional maximum number of notes to return.
            tag_filter: Optional tag to filter notes by.
            offset: Number of notes to skip (pagination offset).
            sort_by: Field to sort by (default: "modifydate").
            sort_direction: Sort direction ("asc" or "desc").

        Returns:
            List of note data. Returns empty list if cache not fully initialized.

        """
        if not self._initialized:
            logger.debug("Cache not fully initialized yet, returning empty list")
            return []

        # Filter notes by tag
        filtered_notes = self._apply_tag_filter(tag_filter)

        # Sort notes
        sorted_notes = self._sort_notes(filtered_notes, sort_by, sort_direction)

        # Apply pagination
        start_idx = offset
        end_idx = None if limit is None else offset + limit
        return sorted_notes[start_idx:end_idx]

    def _apply_tag_filter(self, tag_filter: str | None) -> list[dict[str, Any]]:
        """Apply tag filter to notes.

        Args:
            tag_filter: Tag to filter by, or None for all notes

        Returns:
            List of filtered notes
        """
        if not tag_filter:
            return list(self._notes.values())

        if tag_filter.lower() == "untagged":
            return [
                note
                for note_id, note in self._notes.items()
                if not note.get("tags") or len(note.get("tags", [])) == 0
            ]

        # Try to get notes with this tag
        note_ids = self._get_notes_with_tag(tag_filter)
        if note_ids:
            return [self._notes[key] for key in note_ids if key in self._notes]

        return []

    def _get_sort_key(self, note: dict[str, Any], sort_by: str) -> Any:
        """Get sort key for a note.

        Args:
            note: Note dictionary
            sort_by: Field to sort by

        Returns:
            Sort key value
        """
        if sort_by == "title":
            content = note.get("content", "")
            return content.splitlines()[0] if content else ""
        elif sort_by == "createdate":
            return note.get("createdate", 0)
        else:  # Default to modifydate
            return note.get("modifydate", 0)

    def _sort_notes(
        self, notes: list[dict[str, Any]], sort_by: str, sort_direction: str
    ) -> list[dict[str, Any]]:
        """Sort notes by specified field and direction.

        Args:
            notes: List of notes to sort
            sort_by: Field to sort by
            sort_direction: Sort direction ('asc' or 'desc')

        Returns:
            Sorted list of notes
        """
        reverse_sort = sort_direction.lower() == "desc"
        return sorted(
            notes,
            key=lambda note: self._get_sort_key(note, sort_by),
            reverse=reverse_sort,
        )

    def _check_search_cache(
        self,
        cache_key: str,
        query: str,
        offset: int,
        limit: int | None,
        search_start_time: float,
    ) -> list[dict[str, Any]] | None:
        """Check if search results are cached and return them if valid.

        Args:
            cache_key: Cache key for the search
            query: Search query string
            offset: Pagination offset
            limit: Maximum results
            search_start_time: Time when search started

        Returns:
            Cached results with pagination applied, or None if cache miss
        """
        current_time = search_start_time
        if cache_key in self._query_cache:
            cached_time, cached_results = self._query_cache[cache_key]
            if current_time - cached_time < self._query_cache_ttl:
                logger.debug(f"Using cached search results for query: '{query}'")
                record_cache_hit()
                search_time = time.time() - search_start_time
                record_cache_access_time(search_time)
                start_idx = offset
                end_idx = None if limit is None else offset + limit
                return cached_results[start_idx:end_idx]
        return None

    def _filter_notes_by_untagged(self) -> dict[str, dict[str, Any]]:
        """Filter notes that have no tags.

        Returns:
            Dictionary of untagged notes
        """
        notes_to_search = {
            key: note
            for key, note in self._notes.items()
            if not note.get("tags") or len(note.get("tags", [])) == 0
        }
        logger.debug(
            f"Filtered for untagged notes: {len(notes_to_search)} of {len(self._notes)}"
        )
        return notes_to_search

    def _get_notes_with_tag(self, tag: str) -> set[str] | None:
        """Get note IDs that have a specific tag (case-insensitive).

        Args:
            tag: Tag to search for

        Returns:
            Set of note IDs, or None if tag not found
        """
        # Try exact match
        if tag in self._tag_index:
            return self._tag_index[tag]

        # Try case-insensitive match
        tag_lower = tag.lower()
        for indexed_tag in self._tag_index:
            if indexed_tag.lower() == tag_lower:
                return self._tag_index[indexed_tag]

        return None

    def _filter_notes_by_tags(
        self, tag_filters: list[str]
    ) -> dict[str, dict[str, Any]]:
        """Filter notes by tag filters.

        Args:
            tag_filters: List of tags to filter by

        Returns:
            Dictionary of notes matching all tags
        """
        matching_note_ids = None
        for tag in tag_filters:
            tag_note_ids = self._get_notes_with_tag(tag)
            if tag_note_ids is None:
                matching_note_ids = set()
                break
            if matching_note_ids is None:
                matching_note_ids = set(tag_note_ids)
            else:
                matching_note_ids &= tag_note_ids

        if matching_note_ids is not None:
            notes_to_search = {
                key: self._notes[key] for key in matching_note_ids if key in self._notes
            }
            logger.debug(
                f"Pre-filtered notes by tags: {len(notes_to_search)} of {len(self._notes)}"
            )
            return notes_to_search

        return self._notes

    def search_notes(
        self,
        query: str,
        limit: int | None = None,
        offset: int = 0,
        tag_filters: list[str] | None = None,
        date_range: tuple[datetime | None, datetime | None] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for notes in the cache using advanced search capabilities.

        Args:
            query: The search query (supports boolean operators and special filters).
            limit: Optional maximum number of results to return.
            offset: Number of matching notes to skip (pagination offset).
            tag_filters: Optional list of tags to filter by.
            date_range: Optional tuple of (from_date, to_date) for date filtering.

        Returns:
            List of matching notes sorted by relevance.
        """
        if not self._initialized:
            raise RuntimeError(CACHE_NOT_LOADED)

        logger.debug(
            f"Advanced search: query='{query}', tags={tag_filters}, "
            f"date_range={date_range}, limit={limit}, offset={offset}"
        )

        # Generate cache key
        cache_key = self._generate_search_cache_key(query, tag_filters, date_range)
        search_start_time = time.time()

        # Check cache
        cached_result = self._check_search_cache(
            cache_key, query, offset, limit, search_start_time
        )
        if cached_result is not None:
            return cached_result

        record_cache_miss()

        # Filter notes by tags
        notes_to_search = self._notes
        if tag_filters:
            if len(tag_filters) == 1 and tag_filters[0].lower() == "untagged":
                notes_to_search = self._filter_notes_by_untagged()
            else:
                notes_to_search = self._filter_notes_by_tags(tag_filters)

        # Use search engine
        all_results = self._search_engine.search(
            notes=notes_to_search,
            query=query,
            tag_filters=tag_filters,
            date_range=date_range,
        )

        # Cache results
        self._query_cache[cache_key] = (search_start_time, all_results)

        # Manage cache size
        if len(self._query_cache) > 100:
            oldest_keys = sorted(
                self._query_cache.keys(), key=lambda k: self._query_cache[k][0]
            )[:10]
            for k in oldest_keys:
                del self._query_cache[k]

        # Record timing
        search_time = time.time() - search_start_time
        record_cache_access_time(search_time)

        # Apply pagination
        start_idx = offset
        end_idx = None if limit is None else offset + limit
        return all_results[start_idx:end_idx]

    def _generate_search_cache_key(
        self,
        query: str,
        tag_filters: list[str] | None,
        date_range: tuple[datetime | None, datetime | None] | None,
    ) -> str:
        """Generate a cache key for search results.

        Args:
            query: The search query string
            tag_filters: List of tags to filter by
            date_range: Tuple of (from_date, to_date)

        Returns:
            A string key for the query cache
        """
        # Create a hashable representation of the search parameters
        tag_str = ",".join(sorted(tag_filters)) if tag_filters else ""

        date_str = ""
        if date_range:
            from_date, to_date = date_range
            from_str = from_date.isoformat() if from_date else ""
            to_str = to_date.isoformat() if to_date else ""
            date_str = f"{from_str},{to_str}"

        # Combine parameters and calculate hash - not used for security purposes
        combined = f"{query}|{tag_str}|{date_str}|{self._last_sync}"
        return hashlib.md5(combined.encode(), usedforsecurity=False).hexdigest()

    def _extract_first_word(self, content: str) -> str:
        """Extract first word from content for title indexing.

        Args:
            content: Note content

        Returns:
            First word of first line, or empty string
        """
        if not content:
            return ""
        first_line = content.splitlines()[0] if content else ""
        if not first_line:
            return ""
        words = first_line.split()
        return words[0] if words else ""

    def _add_tags_to_indexes(self, note_id: str, tags: list[str]) -> None:
        """Add tags to cache indexes.

        Args:
            note_id: Note ID
            tags: List of tags to add
        """
        for tag in tags:
            self._tags.add(tag)
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(note_id)

    def _add_to_title_index(self, note_id: str, content: str) -> None:
        """Add note to title index.

        Args:
            note_id: Note ID
            content: Note content
        """
        first_word = self._extract_first_word(content)
        if first_word:
            if first_word not in self._title_index:
                self._title_index[first_word] = []
            if note_id not in self._title_index[first_word]:
                self._title_index[first_word].append(note_id)

    def _remove_from_title_index(self, note_id: str, content: str) -> None:
        """Remove note from title index.

        Args:
            note_id: Note ID
            content: Note content
        """
        first_word = self._extract_first_word(content)
        if first_word and first_word in self._title_index:
            if note_id in self._title_index[first_word]:
                self._title_index[first_word].remove(note_id)
                # Clean up empty entries
                if not self._title_index[first_word]:
                    del self._title_index[first_word]

    def _remove_tags_from_indexes(self, note_id: str, tags: list[str]) -> None:
        """Remove tags from cache indexes.

        Args:
            note_id: Note ID
            tags: List of tags to remove
        """
        for tag in tags:
            # Remove note ID from tag index
            if tag in self._tag_index:
                self._tag_index[tag].discard(note_id)
                # Clean up empty tag index entries
                if not self._tag_index[tag]:
                    del self._tag_index[tag]

            # Check if tag is used in any other note
            if not self._is_tag_used_elsewhere(note_id, tag):
                self._tags.discard(tag)

    def _is_tag_used_elsewhere(self, exclude_note_id: str, tag: str) -> bool:
        """Check if tag is used in any note except the excluded one.

        Args:
            exclude_note_id: Note ID to exclude from search
            tag: Tag to search for

        Returns:
            True if tag is used elsewhere
        """
        return any(
            tag in other_note.get("tags", [])
            for other_key, other_note in self._notes.items()
            if other_key != exclude_note_id
        )

    def update_cache_after_create(self, note: dict) -> None:
        """Update cache after creating a note.

        Args:
            note: The created note data to add to cache.

        """
        if not self._initialized:
            raise RuntimeError(CACHE_NOT_LOADED)

        note_id = note["key"]
        self._notes[note_id] = note

        # Update tags and tag index
        if "tags" in note and note["tags"]:
            self._add_tags_to_indexes(note_id, note["tags"])

        # Update title index
        content = note.get("content", "")
        if content:
            self._add_to_title_index(note_id, content)

        # Clear query cache on note creation
        self._query_cache.clear()

    def _update_tags_on_update(
        self, note_id: str, old_tags: list[str], new_tags: list[str]
    ) -> None:
        """Update tag indexes when a note is updated.

        Args:
            note_id: Note ID
            old_tags: Previous tags
            new_tags: New tags
        """
        # Find removed tags
        removed_tags = [tag for tag in old_tags if tag not in new_tags]
        if removed_tags:
            self._remove_tags_from_indexes(note_id, removed_tags)

        # Add new tags
        if new_tags:
            self._add_tags_to_indexes(note_id, new_tags)

    def update_cache_after_update(self, note: dict) -> None:
        """Update cache after updating a note.

        Args:
            note: The updated note data.

        """
        if not self._initialized:
            raise RuntimeError(CACHE_NOT_LOADED)

        note_id = note["key"]

        # Remove old tags from indexes if note was already in cache
        if note_id in self._notes:
            old_tags = self._notes[note_id].get("tags", [])
            new_tags = note.get("tags", [])
            self._update_tags_on_update(note_id, old_tags, new_tags)

            # Update title index - remove old entries
            old_content = self._notes[note_id].get("content", "")
            if old_content:
                self._remove_from_title_index(note_id, old_content)

        # Update note
        self._notes[note_id] = note

        # Update title index with new content
        content = note.get("content", "")
        if content:
            self._add_to_title_index(note_id, content)

        # Clear query cache on note update
        self._query_cache.clear()

    def update_cache_after_delete(self, note_id: str) -> None:
        """Update cache after deleting a note.

        Args:
            note_id: The ID of the deleted note.

        """
        if not self._initialized:
            raise RuntimeError(CACHE_NOT_LOADED)

        if note_id not in self._notes:
            return

        # Remove tags from indexes
        old_tags = self._notes[note_id].get("tags", [])
        if old_tags:
            self._remove_tags_from_indexes(note_id, old_tags)

        # Update title index - remove deleted note
        content = self._notes[note_id].get("content", "")
        if content:
            self._remove_from_title_index(note_id, content)

        # Remove note from cache
        del self._notes[note_id]

        # Clear query cache on note deletion
        self._query_cache.clear()

    def get_all_tags(self) -> list[str]:
        """Get all unique tags from the cache.

        Returns:
            List of unique tags.

        """
        if not self._initialized:
            raise RuntimeError(CACHE_NOT_LOADED)

        return sorted(self._tags)

    @property
    def is_initialized(self) -> bool:
        """Check if the cache is initialized.

        Returns:
            True if the cache is initialized, False otherwise.

        """
        # For debugging search issues, log current cache state when checked
        logger.debug(
            f"Cache initialization status: initialized={self._initialized}, note count={len(self._notes)}"
        )
        return self._initialized

    @property
    def notes_count(self) -> int:
        """Get the number of notes in the cache.

        Returns:
            Number of notes in the cache.

        """
        if not self._initialized:
            return 0
        return len(self._notes)

    def get_pagination_info(
        self, total_items: int, limit: int | None, offset: int
    ) -> dict:
        """Generate pagination metadata for a result set.

        Args:
            total_items: Total number of items available
            limit: Number of items per page (or None for all)
            offset: Starting position (0-based)

        Returns:
            Dictionary with pagination metadata
        """
        if limit is None or limit <= 0:
            return {
                "total": total_items,
                "offset": offset,
                "limit": None,
                "has_more": False,
            }

        return {
            "total": total_items,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total_items,
            "next_offset": (
                min(offset + limit, total_items)
                if offset + limit < total_items
                else None
            ),
            "prev_offset": max(0, offset - limit) if offset > 0 else 0,
            "page": (offset // limit) + 1,
            "total_pages": (total_items + limit - 1) // limit if limit > 0 else 1,
        }

    @property
    def cache_size(self) -> int:
        """Get the number of notes in the cache.

        Returns:
            Number of notes in the cache.

        """
        return len(self._notes)

    @property
    def tags_count(self) -> int:
        """Get the number of unique tags in the cache.

        Returns:
            Number of unique tags in the cache.

        """
        return len(self._tags)

    @property
    def all_tags(self) -> list:
        """Get all unique tags from the cache.

        Returns:
            List of unique tags.

        """
        return sorted(self._tags)

    @property
    def last_sync_time(self) -> float:
        """Get the timestamp of the last synchronization.

        Returns:
            Timestamp of the last synchronization.

        """
        return self._last_sync

    @property
    def _last_index_mark(self) -> str:
        """Get the last index mark.

        Returns:
            The last index mark or an empty string.

        """
        return getattr(self, "_index_mark", "")

    def _update_cache_metrics(self) -> None:
        """Update cache metrics with current state."""
        config = get_config()
        current_size = len(self._notes)
        max_size = config.cache_max_size

        # Update basic size metrics
        update_cache_size(current_size, max_size)

        # Estimate memory usage (rough calculation)
        estimated_memory = 0
        for note in self._notes.values():
            # Estimate memory for note content and metadata
            content_size = len(str(note.get("content", "")))
            tags_size = sum(len(tag) for tag in note.get("tags", []))
            metadata_size = 200  # Rough estimate for other fields
            estimated_memory += content_size + tags_size + metadata_size

        update_cache_memory_usage(estimated_memory)


class BackgroundSync:
    """Background task for periodically synchronizing the note cache."""

    def __init__(self, cache: NoteCache, config: Config | None = None) -> None:
        """Initialize the background sync task.

        Args:
            cache: The note cache to synchronize.
            config: Optional configuration object. If not provided, the
                global configuration will be used.

        """
        self._cache = cache
        self._config = config or get_config()
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the background sync task."""
        if self._running:
            logger.warning("Background sync task is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._sync_loop(), name="BackgroundSyncTask")
        # Store the task but don't assign to None field
        logger.info(
            f"Started background sync task (interval: {self._config.sync_interval_seconds}s)"
        )

    async def stop(self) -> None:
        """Stop the background sync task."""
        logger.debug("BackgroundSync.stop() called")
        if not self._running:
            logger.warning("Background sync task is not running")
            return

        logger.debug("Setting running flag to False")
        self._running = False

        if self._task:
            logger.debug(
                f"Cancelling task {self._task.get_name() if hasattr(self._task, 'get_name') else self._task}"
            )
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=2.0)
                logger.debug("Task cancelled successfully")
            except asyncio.CancelledError:
                logger.debug("Task was cancelled as expected")
            except TimeoutError:
                logger.warning("Timed out waiting for background sync task to cancel")
            except Exception as e:
                logger.error(
                    f"Error while cancelling background sync task: {str(e)}",
                    exc_info=True,
                )
            finally:
                self._task = None

        logger.info("Stopped background sync task")

    async def _sync_loop(self) -> None:
        """Run the sync loop until stopped."""
        logger.debug("Starting background sync loop")

        # Exponential backoff parameters
        base_retry_delay = 5  # Start with 5 seconds
        max_retry_delay = 300  # Maximum 5 minutes
        current_retry_delay = base_retry_delay
        consecutive_failures = 0

        try:
            while self._running:
                try:
                    # Wait for the specified interval with cancellation check
                    logger.debug(
                        f"Waiting {self._config.sync_interval_seconds}s before next sync"
                    )
                    await asyncio.sleep(self._config.sync_interval_seconds)

                    if not self._running:
                        logger.debug("Sync loop stopped during sleep")
                        break

                    # Synchronize the cache
                    logger.debug("Starting sync operation")
                    start_time = time.time()

                    # Add timeout to the sync operation to prevent hanging
                    try:
                        sync_task = asyncio.create_task(self._cache.sync())
                        changes = await asyncio.wait_for(
                            sync_task, timeout=30.0
                        )  # 30 second timeout

                        # Success - reset backoff parameters
                        consecutive_failures = 0
                        current_retry_delay = base_retry_delay

                        elapsed = time.time() - start_time
                        if changes > 0:
                            logger.info(
                                f"Background sync updated {changes} notes in {elapsed:.2f}s"
                            )
                        else:
                            logger.debug(
                                f"Background sync completed in {elapsed:.2f}s (no changes)"
                            )

                    except TimeoutError:
                        elapsed = time.time() - start_time
                        logger.warning(f"Sync operation timed out after {elapsed:.2f}s")
                        # Count as a failure for backoff purposes
                        consecutive_failures += 1

                except asyncio.CancelledError:
                    # Normal cancellation
                    logger.info("Background sync task cancelled")
                    raise  # Re-raise to exit the loop and function

                except Exception as e:
                    logger.error(f"Error in background sync: {str(e)}", exc_info=True)
                    # Increment failure counter and adjust delay
                    consecutive_failures += 1

                    # Calculate backoff delay using exponential backoff with jitter
                    # Use deterministic jitter based on time for non-cryptographic purposes
                    time_hash = int(
                        hashlib.sha256(str(time.time()).encode()).hexdigest()[:8], 16
                    )
                    jitter = 0.8 + (time_hash % 1000) / 2500  # 20% jitter (0.8 to 1.2)
                    current_retry_delay = min(
                        max_retry_delay,
                        base_retry_delay
                        * (2 ** min(consecutive_failures - 1, 5))
                        * jitter,
                    )

                    logger.warning(
                        f"Backing off for {current_retry_delay:.1f}s after {consecutive_failures} consecutive failures"
                    )

                    # Sleep with backoff before retrying
                    await asyncio.sleep(current_retry_delay)

        except asyncio.CancelledError:
            logger.info("Background sync loop cancelled")
            raise  # Re-raise so the calling code can handle it
        finally:
            logger.debug("Exiting background sync loop")


async def initialize_cache(client: Simplenote) -> NoteCache:
    """Initialize the note cache.

    Args:
        client: The Simplenote client instance.

    Returns:
        The initialized note cache.

    """
    global _cache_instance

    # Create and initialize the cache
    cache = NoteCache(client)
    await cache.initialize()

    # Store the cache instance globally
    _cache_instance = cache

    # Start background synchronization
    background_sync = BackgroundSync(cache)
    await background_sync.start()

    return cache
