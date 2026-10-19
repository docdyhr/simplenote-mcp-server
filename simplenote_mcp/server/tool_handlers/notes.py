"""Core note tools: create, read, update, list, get-or-create."""

import asyncio
import json
from typing import Any

import mcp.types as types

from ..decorators import (
    validate_content_required,
    validate_note_id_required,
    with_input_validation,
)
from ..error_helpers import (
    empty_field_error,
    required_field_error,
)
from ..errors import (
    InternalError,
    NetworkError,
    ValidationError,
)
from ..logging import logger
from ..security import validate_tool_security
from ..utils.common import (
    safe_get,
    safe_set,
)
from ..vault import (
    VAULT_TAG,
    encrypt_content,
)
from .base import (
    ToolHandlerBase,
    extract_title_from_content,
)


class CreateNoteHandler(ToolHandlerBase):
    """Handler for create_note tool."""

    @validate_tool_security("create_note")
    @with_input_validation(validate_content_required)
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle create_note tool call."""
        content = arguments.get("content", "")
        tags_input = arguments.get("tags", "")
        encrypt = bool(arguments.get("encrypt", False))

        # Handle tags which can be either a string or a list (comma-separated)
        # Spaces in tags are converted to hyphens via _parse_tags
        tags = self._parse_tags(tags_input) if tags_input else []

        try:
            if encrypt:
                vault_key = self._resolve_vault_key()
                content = encrypt_content(content, vault_key)
                if VAULT_TAG not in tags:
                    tags = [*tags, VAULT_TAG]

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
                                "encrypted": encrypt,
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
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle update_note tool call."""
        note_id = arguments.get("note_id", "")
        content = arguments.get("content", "")
        tags_input = arguments.get("tags", "")
        encrypt = bool(arguments.get("encrypt", False))

        if not note_id:
            raise empty_field_error("note_id")

        if "content" not in arguments:
            raise required_field_error("content")

        try:
            existing_note = self._get_note_from_cache_or_api(note_id)
            existing_tags = existing_note.get("tags", []) or []

            if VAULT_TAG in existing_tags and not encrypt:
                raise ValidationError(
                    f"Note {note_id} is Vault-encrypted; update_note would overwrite "
                    "the encrypted content with plaintext. Pass encrypt=true to "
                    "replace and re-encrypt in one step, or call decrypt_note first "
                    "if you intentionally want to remove encryption.",
                    subcategory="vault_encrypted_note",
                    resource_id=note_id,
                )

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
                from ..errors import ValidationError as _VE

                raise _VE(
                    f"Refusing to replace a {len(existing_content)}-character note "
                    f"with {len(content)} characters "
                    f"({len(content) / max(len(existing_content), 1):.0%} of original). "
                    "Call get_note first, make targeted edits, and pass the full merged "
                    "content. Use add_text or replace_section for partial updates.",
                    subcategory="suspicious_shrink",
                )

            # Update the note content, encrypting first if requested
            if encrypt:
                vault_key = self._resolve_vault_key()
                safe_set(existing_note, "content", encrypt_content(content, vault_key))
            else:
                safe_set(existing_note, "content", content)

            # Update tags: explicit tags_input replaces the tag list (comma-
            # separated or list; spaces → hyphens, consistent with every other
            # tag-accepting tool). encrypt=true always ensures VAULT_TAG ends up
            # in the final tags, merging with tags_input or preserving existing.
            if encrypt:
                final_tags = (
                    self._parse_tags(tags_input) if tags_input else list(existing_tags)
                )
                if VAULT_TAG not in final_tags:
                    final_tags.append(VAULT_TAG)
                safe_set(existing_note, "tags", final_tags)
            elif tags_input:
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
                                "encrypted": VAULT_TAG
                                in (updated_note.get("tags") or []),
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


class GetNoteHandler(ToolHandlerBase):
    """Handler for get_note tool."""

    @validate_tool_security("get_note")
    @with_input_validation(validate_note_id_required)
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
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

            # Prepare response. The title (first line) stays plaintext even
            # for Vault-encrypted notes, so it's always extracted from the
            # raw content regardless of whether decryption succeeds.
            raw_content = safe_get(note, "content", "")
            first_line = extract_title_from_content(raw_content, "")
            content, encrypted, decryptable = self._decrypt_for_read(raw_content)

            response: dict[str, Any] = {
                "success": True,
                "note_id": note.get("key"),
                "content": content,
                "title": first_line,
                "tags": note.get("tags", []),
                "createdate": note.get("createdate", ""),
                "modifydate": note.get("modifydate", ""),
                "uri": f"simplenote://note/{note.get('key')}",
                "encrypted": encrypted,
            }
            if encrypted:
                response["decryptable"] = decryptable

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(response),
                )
            ]

        except Exception as e:
            return self._format_error_response(
                e, f"getting note {note_id}", {"note_id": note_id}
            )


class GetOrCreateNoteHandler(ToolHandlerBase):
    """Handler for get_or_create_note tool — atomic find-or-create."""

    @validate_tool_security("get_or_create_note")
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle get_or_create_note tool call."""
        from ..errors import ValidationError

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


class ListNotesHandler(ToolHandlerBase):
    """Handler for list_notes tool — browse recent notes, optionally by tag."""

    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
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
                # The title (first line) stays plaintext even for
                # Vault-encrypted notes, so this is always safe to show
                # without decrypting — list_notes never includes full content.
                first_line = content.split("\n")[0].strip()[:60] if content else ""
                results.append(
                    {
                        "id": note.get("key", ""),
                        "title": first_line,
                        "tags": note.get("tags", []),
                        "modified": note.get("modifydate", ""),
                        "deleted": bool(note.get("deleted")),
                        "encrypted": VAULT_TAG in (note.get("tags") or []),
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
