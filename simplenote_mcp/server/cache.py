# simplenote_mcp/server/cache.py

import asyncio
import logging
import time
from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional, Set

from simplenote import Simplenote

from .config import get_config
from .errors import NetworkError, ResourceNotFoundError, handle_exception

logger = logging.getLogger("simplenote_mcp")

class NoteCache:
    """In-memory cache for Simplenote notes.
    
    This class handles caching of notes for faster retrieval and reduced API calls.
    It maintains both a dictionary of notes by ID and a set of cached tag values.
    """

    def __init__(self, simplenote_client: Simplenote):
        """Initialize the note cache.
        
        Args:
            simplenote_client: The Simplenote client to use for API calls
        """
        self._client = simplenote_client
        self._notes: Dict[str, Dict] = {}  # Map of note_id -> note object
        self._tags: Set[str] = set()  # Set of all tags across notes
        self._last_sync: Optional[float] = None
        self._last_index_mark: Optional[str] = None
        self._lock = Lock()  # For thread safety
        self._initialized = False
        self._loading = False
        self._config = get_config()

    @property
    def is_initialized(self) -> bool:
        """Whether the cache has been initialized with data."""
        return self._initialized

    @property
    def is_loading(self) -> bool:
        """Whether the cache is currently loading data."""
        return self._loading

    @property
    def cache_size(self) -> int:
        """The number of notes in the cache."""
        return len(self._notes)

    @property
    def all_tags(self) -> List[str]:
        """Get all tags present in the cache."""
        with self._lock:
            return sorted(self._tags)

    @property
    def last_sync_time(self) -> Optional[datetime]:
        """Get the timestamp of the last sync, or None if never synced."""
        if self._last_sync is None:
            return None
        return datetime.fromtimestamp(self._last_sync)

    async def initialize(self) -> None:
        """Initialize the cache with all notes from Simplenote.
        
        This should be called once during server startup to load the initial set
        of notes from the Simplenote API.
        """
        if self._initialized:
            logger.info("Note cache already initialized")
            return

        if self._loading:
            logger.info("Note cache already loading, waiting...")
            while self._loading:
                await asyncio.sleep(0.5)
            return

        try:
            self._loading = True
            logger.info("Initializing note cache...")
            start_time = time.time()

            # Get all notes from Simplenote
            notes, status = self._client.get_note_list()

            if status != 0:
                error_msg = f"Failed to get notes from Simplenote API (status {status})"
                logger.error(error_msg)
                raise NetworkError(error_msg)

            # Reset the cache and update with the new data
            with self._lock:
                self._notes = {}
                self._tags = set()

                # Process each note
                for note in notes:
                    note_id = note.get("key")
                    if note_id:
                        self._notes[note_id] = note

                        # Extract tags
                        note_tags = note.get("tags", [])
                        if note_tags:
                            self._tags.update(note_tags)

                self._last_sync = time.time()
                self._initialized = True

            elapsed = time.time() - start_time
            logger.info(f"Note cache initialized with {len(self._notes)} notes in {elapsed:.2f}s")

            # Get the latest index mark for future syncs
            data, status = self._client.get_note_list(data=True, since=None, tags=True)
            if status == 0 and 'mark' in data:
                self._last_index_mark = data['mark']
                logger.debug(f"Updated last index mark: {self._last_index_mark}")

        except Exception as e:
            logger.error(f"Error initializing note cache: {str(e)}", exc_info=True)
            raise handle_exception(e, "initializing note cache")

        finally:
            self._loading = False

    async def sync(self) -> int:
        """Synchronize the cache with the Simplenote API.
        
        This fetches only notes that have changed since the last sync using the
        index_since mechanism, which is more efficient than fetching all notes.
        
        Returns:
            The number of notes that were updated in the cache
        """
        logger.debug("Starting cache synchronization...")

        try:
            # Get changes since last sync
            data, status = self._client.get_note_list(
                data=True,
                since=self._last_index_mark,
                tags=True
            )

            if status != 0:
                error_msg = f"Failed to get note updates from Simplenote API (status {status})"
                logger.error(error_msg)
                raise NetworkError(error_msg)

            # Update the index mark for the next sync
            if 'mark' in data:
                self._last_index_mark = data['mark']
                logger.debug(f"Updated last index mark: {self._last_index_mark}")

            # Process the changes
            notes = data.get('notes', [])
            changes = 0

            with self._lock:
                for note in notes:
                    note_id = note.get("key")
                    if not note_id:
                        continue

                    # Handle deleted notes
                    if note.get('deleted', False):
                        if note_id in self._notes:
                            del self._notes[note_id]
                            changes += 1
                        continue

                    # Add or update the note
                    self._notes[note_id] = note

                    # Update tags
                    note_tags = note.get("tags", [])
                    if note_tags:
                        self._tags.update(note_tags)

                    changes += 1

                # Refresh the tag set by scanning all notes
                self._tags = set()
                for note in self._notes.values():
                    note_tags = note.get("tags", [])
                    if note_tags:
                        self._tags.update(note_tags)

                self._last_sync = time.time()

            logger.info(f"Cache sync complete: {changes} notes updated")
            return changes

        except Exception as e:
            logger.error(f"Error synchronizing note cache: {str(e)}", exc_info=True)
            raise handle_exception(e, "synchronizing note cache")

    def get_note(self, note_id: str) -> Dict:
        """Get a note from the cache by ID.
        
        Args:
            note_id: The ID of the note to get
            
        Returns:
            The note object
            
        Raises:
            ResourceNotFoundError: If the note is not in the cache
        """
        with self._lock:
            if note_id in self._notes:
                return self._notes[note_id]

        # Note not in cache, try to get it from the API
        note, status = self._client.get_note(note_id)
        if status == 0:
            # Add it to the cache
            with self._lock:
                self._notes[note_id] = note

                # Update tags
                note_tags = note.get("tags", [])
                if note_tags:
                    self._tags.update(note_tags)

            return note

        raise ResourceNotFoundError(f"Note not found with ID: {note_id}")

    def get_all_notes(self, limit: Optional[int] = None, tag_filter: Optional[str] = None) -> List[Dict]:
        """Get all notes from the cache.
        
        Args:
            limit: Optional maximum number of notes to return
            tag_filter: Optional tag to filter by
            
        Returns:
            List of note objects, ordered by modification date (newest first)
        """
        with self._lock:
            # Start with all notes
            notes = list(self._notes.values())

            # Apply tag filter if specified
            if tag_filter:
                notes = [
                    note for note in notes
                    if "tags" in note and tag_filter in note["tags"]
                ]

            # Sort by modification date (newest first)
            notes.sort(
                key=lambda n: n.get("modifydate", ""),
                reverse=True
            )

            # Apply limit if specified
            if limit is not None and limit > 0:
                notes = notes[:limit]

            return notes

    def search_notes(self, query: str, limit: Optional[int] = None) -> List[Dict]:
        """Search for notes in the cache.
        
        Args:
            query: The search query (case-insensitive)
            limit: Optional maximum number of results to return
            
        Returns:
            List of matching note objects, ordered by relevance
        """
        query_lower = query.lower()
        results = []

        with self._lock:
            for note in self._notes.values():
                content = note.get("content", "").lower()
                if query_lower in content:
                    # Calculate a crude relevance score
                    # (number of occurrences of the query in the content)
                    occurrences = content.count(query_lower)
                    results.append((note, occurrences))

        # Sort by relevance (higher score first)
        results.sort(key=lambda x: x[1], reverse=True)

        # Apply limit if specified
        if limit is not None and limit > 0:
            results = results[:limit]

        # Return just the notes, not the scores
        return [note for note, _ in results]

    def update_cache_after_create(self, note: Dict) -> None:
        """Update the cache after creating a new note.
        
        Args:
            note: The newly created note object
        """
        note_id = note.get("key")
        if not note_id:
            logger.warning("Cannot update cache with note without ID")
            return

        with self._lock:
            self._notes[note_id] = note

            # Update tags
            note_tags = note.get("tags", [])
            if note_tags:
                self._tags.update(note_tags)

    def update_cache_after_update(self, note: Dict) -> None:
        """Update the cache after updating a note.
        
        Args:
            note: The updated note object
        """
        note_id = note.get("key")
        if not note_id:
            logger.warning("Cannot update cache with note without ID")
            return

        with self._lock:
            self._notes[note_id] = note

            # Refresh the tag set by scanning all notes
            self._tags = set()
            for n in self._notes.values():
                note_tags = n.get("tags", [])
                if note_tags:
                    self._tags.update(note_tags)

    def update_cache_after_delete(self, note_id: str) -> None:
        """Update the cache after deleting a note.
        
        Args:
            note_id: The ID of the deleted note
        """
        with self._lock:
            if note_id in self._notes:
                del self._notes[note_id]

                # Refresh the tag set by scanning all notes
                self._tags = set()
                for note in self._notes.values():
                    note_tags = note.get("tags", [])
                    if note_tags:
                        self._tags.update(note_tags)

class BackgroundSync:
    """Background synchronization task for periodically updating the note cache."""

    def __init__(self, note_cache: NoteCache):
        """Initialize the background sync task.
        
        Args:
            note_cache: The note cache to synchronize
        """
        self._cache = note_cache
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._config = get_config()

    async def start(self) -> None:
        """Start the background sync task."""
        if self._running:
            logger.warning("Background sync task is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._sync_loop())
        logger.info(f"Started background sync task (interval: {self._config.sync_interval_seconds}s)")

    async def stop(self) -> None:
        """Stop the background sync task."""
        if not self._running:
            logger.warning("Background sync task is not running")
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Stopped background sync task")

    async def _sync_loop(self) -> None:
        """Run the sync loop until stopped."""
        while self._running:
            try:
                # Wait for the specified interval
                await asyncio.sleep(self._config.sync_interval_seconds)

                # Synchronize the cache
                start_time = time.time()
                changes = await self._cache.sync()
                elapsed = time.time() - start_time

                if changes > 0:
                    logger.info(f"Background sync updated {changes} notes in {elapsed:.2f}s")
                else:
                    logger.debug(f"Background sync completed in {elapsed:.2f}s (no changes)")

            except asyncio.CancelledError:
                # Normal cancellation
                logger.info("Background sync task cancelled")
                break

            except Exception as e:
                # Log the error but keep the task running
                logger.error(f"Error in background sync task: {str(e)}", exc_info=True)

                # Wait a bit before retrying (half the normal interval)
                retry_interval = max(10, self._config.sync_interval_seconds // 2)
                logger.info(f"Retrying background sync in {retry_interval}s")
                await asyncio.sleep(retry_interval)
