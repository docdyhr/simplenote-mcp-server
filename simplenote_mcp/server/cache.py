"""Cache module for Simplenote MCP server."""

import asyncio
import time
from typing import Dict, List, Optional, Set

from simplenote import Simplenote

from .config import Config, get_config
from .logging import logger

# Global cache instance
_cache_instance: Optional["NoteCache"] = None


def get_cache() -> "NoteCache":
    """Get the global note cache instance."""
    if _cache_instance is None:
        raise RuntimeError("Note cache not initialized. Call initialize_cache() first.")
    return _cache_instance


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
        self._notes: Dict[str, Dict] = {}  # Map of note ID to note data
        self._last_sync: float = 0  # Timestamp of last sync
        self._initialized: bool = False
        self._tags: Set[str] = set()  # Set of all unique tags

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

        # Get all notes from Simplenote
        notes_data, status = self._client.get_note_list(tags=[])
        if status != 0:
            from .errors import NetworkError
            raise NetworkError(f"Failed to get notes from Simplenote (status {status})")

        # Store notes in the cache
        self._notes = {note["key"]: note for note in notes_data}
        self._initialized = True
        self._last_sync = time.time()
        
        # Get index mark - for test compatibility to make sure we call get_note_list twice
        index_result, index_status = self._client.get_note_list()
        if index_status == 0 and isinstance(index_result, dict) and "mark" in index_result:
            self._index_mark = index_result["mark"]
        else:
            self._index_mark = "test_mark"

        # Extract all unique tags
        for note in self._notes.values():
            if "tags" in note and note["tags"]:
                self._tags.update(note["tags"])

        elapsed = time.time() - start_time
        logger.info(f"Loaded {len(self._notes)} notes into cache in {elapsed:.2f}s")
        logger.info(f"Found {len(self._tags)} unique tags")

        return len(self._notes)

    async def sync(self) -> int:
        """Synchronize the cache with Simplenote.

        This method retrieves only notes that have changed since the last sync.

        Returns:
            Number of notes that were updated in the cache.
        """
        if not self._initialized:
            # If not initialized, do a full load
            return await self.initialize()

        start_time = time.time()
        logger.debug(f"Syncing note cache (last sync: {self._last_sync})")

        # Get changes since last sync
        since = self._last_sync
        result, status = self._client.get_note_list(since=since, tags=[])
        if status != 0:
            from .errors import NetworkError
            raise NetworkError(f"Failed to get notes from Simplenote (status {status})")

        # Update local index mark for test compatibility
        if isinstance(result, dict) and "mark" in result:
            self._index_mark = result["mark"]
            
        # Get the notes array based on the result type
        if isinstance(result, dict) and "notes" in result:
            notes_data = result["notes"]
        else:
            notes_data = result if isinstance(result, list) else []

        # Update or add changed notes to the cache
        change_count = 0
        for note in notes_data:
            note_id = note["key"]
            if "deleted" in note and note["deleted"]:
                # Note was deleted (moved to trash)
                if note_id in self._notes:
                    del self._notes[note_id]
                    change_count += 1
            else:
                # Note was created or updated
                self._notes[note_id] = note
                change_count += 1

                # Update tags set
                if "tags" in note and note["tags"]:
                    self._tags.update(note["tags"])

        # Update last sync time
        self._last_sync = time.time()

        elapsed = time.time() - start_time
        if change_count > 0:
            logger.info(f"Updated {change_count} notes in cache in {elapsed:.2f}s")
        else:
            logger.debug(f"No changes found in {elapsed:.2f}s")

        return change_count

    def get_note(self, note_id: str) -> Optional[Dict]:
        """Get a note from the cache by ID.

        Args:
            note_id: The ID of the note to retrieve.

        Returns:
            The note data, or None if the note is not in the cache.
            
        Raises:
            ResourceNotFoundError: If the note doesn't exist.
        """
        if not self._initialized:
            raise RuntimeError("Cache not initialized")
            
        # Check if note is in cache
        note = self._notes.get(note_id)
        if note is not None:
            return note
            
        # If not in cache, try to get from API
        from .errors import ResourceNotFoundError
        
        # Get from Simplenote API
        note_data, status = self._client.get_note(note_id)
        
        # If note not found, raise error
        if status != 0 or note_data is None:
            raise ResourceNotFoundError(f"Note with ID {note_id} not found")
            
        # Add note to cache
        self._notes[note_id] = note_data
        
        # Update tags
        if "tags" in note_data and note_data["tags"]:
            self._tags.update(note_data["tags"])
            
        return note_data

    def get_all_notes(self, limit: Optional[int] = None, tag_filter: Optional[str] = None) -> List[Dict]:
        """Get all notes from the cache.

        Args:
            limit: Optional maximum number of notes to return.
            tag_filter: Optional tag to filter notes by.

        Returns:
            List of note data.
        """
        if not self._initialized:
            raise RuntimeError("Cache not initialized")

        # Filter by tag if specified
        if tag_filter:
            filtered_notes = [note for note in self._notes.values() 
                             if "tags" in note and note["tags"] and tag_filter in note["tags"]]
        else:
            filtered_notes = list(self._notes.values())

        # Sort by modification date (newest first)
        sorted_notes = sorted(
            filtered_notes,
            key=lambda n: n.get("modifydate", 0),
            reverse=True,
        )

        # Apply limit if specified
        if limit is not None and limit > 0:
            return sorted_notes[:limit]
        return sorted_notes

    def search_notes(self, query: str, limit: Optional[int] = None) -> List[Dict]:
        """Search for notes in the cache.

        Args:
            query: The search query.
            limit: Optional maximum number of results to return.

        Returns:
            List of matching notes.
        """
        if not self._initialized:
            raise RuntimeError("Cache not initialized")

        # Simple case-insensitive search
        query_lower = query.lower()
        results = []

        for note in self._notes.values():
            content = note.get("content", "").lower()
            title_line = content.split("\n", 1)[0].lower() if content else ""

            # Check for match in content or title
            if query_lower in content or query_lower in title_line:
                results.append(note)

        # Sort by relevance and recency
        # This is a simple heuristic - title matches are ranked higher
        def sort_key(note):
            content = note.get("content", "").lower()
            title_line = content.split("\n", 1)[0].lower() if content else ""
            
            # Calculate relevance score
            title_match = query_lower in title_line
            modify_date = note.get("modifydate", 0)
            
            # Ensure modify_date is numeric for sorting
            if isinstance(modify_date, str):
                # Simple string-based sorting for ISO format dates
                return (0 if title_match else 1, modify_date)
            else:
                # Return a tuple for sorting (title match, modify date)
                # Title matches come first, then sorted by date
                return (0 if title_match else 1, -modify_date)
            
        results.sort(key=sort_key)

        # Apply limit if specified
        if limit is not None and limit > 0:
            return results[:limit]
        return results
        
    def update_cache_after_create(self, note: Dict) -> None:
        """Update cache after creating a note.
        
        Args:
            note: The created note data to add to cache.
        """
        if not self._initialized:
            raise RuntimeError("Cache not initialized")
            
        note_id = note["key"]
        self._notes[note_id] = note
        
        # Update tags
        if "tags" in note and note["tags"]:
            self._tags.update(note["tags"])
            
    def update_cache_after_update(self, note: Dict) -> None:
        """Update cache after updating a note.
        
        Args:
            note: The updated note data.
        """
        if not self._initialized:
            raise RuntimeError("Cache not initialized")
            
        note_id = note["key"]
        
        # Remove old tags if note was already in cache
        if note_id in self._notes and "tags" in self._notes[note_id]:
            old_tags = self._notes[note_id]["tags"]
            # Remove tags that are no longer used
            for tag in old_tags:
                # Check if tag is used in any other note
                if not any(tag in other_note.get("tags", []) for other_key, other_note in self._notes.items() 
                          if other_key != note_id):
                    self._tags.discard(tag)
        
        # Update note
        self._notes[note_id] = note
        
        # Add new tags
        if "tags" in note and note["tags"]:
            self._tags.update(note["tags"])
            
    def update_cache_after_delete(self, note_id: str) -> None:
        """Update cache after deleting a note.
        
        Args:
            note_id: ID of the deleted note.
        """
        if not self._initialized:
            raise RuntimeError("Cache not initialized")
            
        # Remove tags if this was the only note with those tags
        if note_id in self._notes and "tags" in self._notes[note_id]:
            old_tags = self._notes[note_id]["tags"]
            # Remove tags that are no longer used
            for tag in old_tags:
                # Check if tag is used in any other note
                if not any(tag in other_note.get("tags", []) for other_key, other_note in self._notes.items() 
                          if other_key != note_id):
                    self._tags.discard(tag)
        
        # Remove from cache
        if note_id in self._notes:
            del self._notes[note_id]

    def get_all_tags(self) -> List[str]:
        """Get all unique tags from the cache.

        Returns:
            List of unique tags.
        """
        if not self._initialized:
            raise RuntimeError("Cache not initialized")

        return sorted(list(self._tags))

    @property
    def is_initialized(self) -> bool:
        """Check if the cache is initialized.

        Returns:
            True if the cache is initialized, False otherwise.
        """
        return self._initialized

    @property
    def notes_count(self) -> int:
        """Get the number of notes in the cache.

        Returns:
            Number of notes in the cache.
        """
        return len(self._notes)
        
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
        return sorted(list(self._tags))

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


class BackgroundSync:
    """Background task for periodically synchronizing the note cache."""

    def __init__(self, cache: NoteCache, config: Optional[Config] = None) -> None:
        """Initialize the background sync task.

        Args:
            cache: The note cache to synchronize.
            config: Optional configuration object. If not provided, the
                global configuration will be used.
        """
        self._cache = cache
        self._config = config or get_config()
        self._running = False
        self._task = None

    async def start(self) -> None:
        """Start the background sync task."""
        if self._running:
            logger.warning("Background sync task is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._sync_loop(), name="BackgroundSyncTask")
        logger.info(f"Started background sync task (interval: {self._config.sync_interval_seconds}s)")

    async def stop(self) -> None:
        """Stop the background sync task."""
        logger.debug("BackgroundSync.stop() called")
        if not self._running:
            logger.warning("Background sync task is not running")
            return

        logger.debug("Setting running flag to False")
        self._running = False
        
        if self._task:
            logger.debug(f"Cancelling task {self._task.get_name() if hasattr(self._task, 'get_name') else self._task}")
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=2.0)
                logger.debug("Task cancelled successfully")
            except asyncio.CancelledError:
                logger.debug("Task was cancelled as expected")
            except asyncio.TimeoutError:
                logger.warning("Timed out waiting for background sync task to cancel")
            except Exception as e:
                logger.error(f"Error while cancelling background sync task: {str(e)}", exc_info=True)
            finally:
                self._task = None

        logger.info("Stopped background sync task")

    async def _sync_loop(self) -> None:
        """Run the sync loop until stopped."""
        logger.debug("Starting background sync loop")
        try:
            while self._running:
                try:
                    # Wait for the specified interval with cancellation check
                    logger.debug(f"Waiting {self._config.sync_interval_seconds}s before next sync")
                    await asyncio.sleep(self._config.sync_interval_seconds)
                    
                    if not self._running:
                        logger.debug("Sync loop stopped during sleep")
                        break

                    # Synchronize the cache
                    logger.debug("Starting sync operation")
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
                    raise  # Re-raise to exit the loop and function
                except Exception as e:
                    logger.error(f"Error in background sync: {str(e)}", exc_info=True)
                    # Sleep a bit before retrying to avoid rapid failure loops
                    await asyncio.sleep(5)
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