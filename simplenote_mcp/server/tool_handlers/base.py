"""Shared base class, constants and helpers for the tool handlers."""

import contextlib
import json
from abc import ABC, abstractmethod
from typing import Any

import mcp.types as types

from ..cache import NoteCache
from ..errors import (
    ConfigurationError,
    ResourceNotFoundError,
    ServerError,
    ValidationError,
)
from ..logging import logger
from ..utils.common import (
    extract_title_from_content as extract_title_common,
)
from ..utils.common import (
    safe_split,
)
from ..vault import (
    VAULT_TAG,
    VaultDecryptionError,
    VaultKeyCorruptedError,
    VaultKeyUnavailableError,
    decrypt_content,
    get_or_create_vault_key,
    has_vault_key,
    is_encrypted,
)


def extract_title_from_content(content: str, fallback: str = "") -> str:
    """Extract the first non-empty line from content as title."""
    from ..config import get_config

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
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle the tool call with the given arguments.

        Args:
            arguments: Tool arguments

        Returns:
            A list of text content on success, or a CallToolResult with
            isError=True (via _format_error_response) on failure.
        """

    def _format_error_response(
        self, error: Exception, operation: str, context: dict[str, Any] | None = None
    ) -> types.CallToolResult:
        """Format an error into a consistent JSON response.

        Args:
            error: The exception that occurred
            operation: Description of the operation that failed
            context: Optional context information (note_id, query, etc.)

        Returns:
            A CallToolResult with isError=True so the MCP protocol layer
            (and callers) can distinguish this from a successful response
            without parsing the JSON payload.
        """
        if isinstance(error, ServerError):
            error_dict = error.to_dict()
        else:
            from ..errors import handle_exception

            logger.error(f"Error {operation}: {str(error)}", exc_info=True)
            handled_error = handle_exception(error, operation)
            error_dict = handled_error.to_dict()

        # Add context if provided
        if context:
            error_dict["error"]["context"] = context

        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(error_dict))],
            isError=True,
        )

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

    def _resolve_vault_key(self) -> bytes:
        """Return the Vault master key, translating provisioning failures
        into a structured, actionable ConfigurationError.

        Raises:
            ConfigurationError: no key is available (see VaultKeyUnavailableError),
                or an existing key is corrupted/wrong-length (see
                VaultKeyCorruptedError) — surfaced clearly rather than
                silently generating a replacement that would orphan any
                already-encrypted notes.
        """
        try:
            return get_or_create_vault_key()
        except VaultKeyUnavailableError as e:
            raise ConfigurationError(
                str(e), subcategory="vault_key_unavailable", recoverable=True
            ) from e
        except VaultKeyCorruptedError as e:
            raise ConfigurationError(
                str(e), subcategory="vault_key_corrupted", recoverable=False
            ) from e

    def _decrypt_for_read(self, content: str) -> tuple[str | None, bool, bool]:
        """Attempt to decrypt content for a read-only response.

        Never provisions a new Vault key as a side effect of a read — only
        decrypts when a key is already available, so calling get_note on an
        encrypted note from a fresh machine never silently generates and
        persists an unrelated local key.

        Returns:
            (content, encrypted, decryptable). `content` is the original
            content unchanged when not encrypted; the decrypted plaintext
            when encrypted and a working key is available; None when
            encrypted but not decryptable (no key, or the wrong key).

        Raises:
            ConfigurationError: the key file/keychain entry exists but is
                corrupted — surfaced rather than silently reported as
                "not decryptable", since that would look identical to
                "no key configured yet" and hide a real problem.
        """
        if not is_encrypted(content):
            return content, False, True
        try:
            key_available = has_vault_key()
        except VaultKeyCorruptedError as e:
            raise ConfigurationError(
                str(e), subcategory="vault_key_corrupted", recoverable=False
            ) from e
        if not key_available:
            return None, True, False
        try:
            return decrypt_content(content, self._resolve_vault_key()), True, True
        except VaultDecryptionError:
            return None, True, False

    def _guard_against_blind_mutation(
        self, note: dict[str, Any], note_id: str, tool_name: str
    ) -> None:
        """Refuse to let a content-mutating tool corrupt a Vault-encrypted note.

        add_text/replace_section (and update_note without encrypt=true) read
        existing content, transform it, and write the result back. Applied
        blindly to Vault ciphertext this would corrupt the envelope beyond
        recovery, or silently persist plaintext over what was encrypted.

        Raises:
            ValidationError: the note is Vault-encrypted.
        """
        if VAULT_TAG in (note.get("tags") or []):
            raise ValidationError(
                f"Note {note_id} is Vault-encrypted; {tool_name} would corrupt "
                "or silently discard the encryption. Call decrypt_note first, "
                "make your edit, then encrypt_note again.",
                subcategory="vault_encrypted_note",
                resource_id=note_id,
            )

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
