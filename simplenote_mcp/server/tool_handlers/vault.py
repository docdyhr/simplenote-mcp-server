"""Vault tools: encrypt, decrypt, and report Vault status."""

import json
from typing import Any

import mcp.types as types

from ..errors import (
    NetworkError,
    SecurityError,
)
from ..security import validate_tool_security
from ..vault import (
    VAULT_TAG,
    VaultDecryptionError,
    VaultKeyCorruptedError,
    decrypt_content,
    encrypt_content,
    has_vault_key,
    key_provider_name,
)
from .base import (
    ToolHandlerBase,
)


class EncryptNoteHandler(ToolHandlerBase):
    """Handler for encrypt_note tool — Vault-encrypt an existing note's body."""

    @validate_tool_security("encrypt_note")
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle encrypt_note tool call."""
        note_id = arguments.get("note_id", "")

        if not note_id:
            return self._format_error_response(
                ValueError("note_id is required"),
                "encrypting note",
            )

        try:
            note_data = self._get_note_from_cache_or_api(note_id)
            tags: list[str] = list(note_data.get("tags") or [])

            if VAULT_TAG in tags:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "note_id": note_id,
                                "encrypted": True,
                                "message": "Note is already Vault-encrypted; no changes made.",
                            }
                        ),
                    )
                ]

            vault_key = self._resolve_vault_key()
            content = note_data.get("content", "") or ""
            note_data["content"] = encrypt_content(content, vault_key)
            tags.append(VAULT_TAG)
            note_data["tags"] = tags

            updated_note, status = self.sn.update_note(note_data)
            if status != 0:
                raise NetworkError(f"Failed to encrypt note {note_id}")

            self._update_cache_after_operation(updated_note, "update")

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "note_id": note_id,
                            "encrypted": True,
                            "tags": updated_note.get("tags", []),
                            "message": "Note encrypted successfully.",
                        }
                    ),
                )
            ]

        except Exception as e:
            return self._format_error_response(
                e, f"encrypting note {note_id}", {"note_id": note_id}
            )


class DecryptNoteHandler(ToolHandlerBase):
    """Handler for decrypt_note tool — reverse encrypt_note."""

    @validate_tool_security("decrypt_note")
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle decrypt_note tool call."""
        note_id = arguments.get("note_id", "")

        if not note_id:
            return self._format_error_response(
                ValueError("note_id is required"),
                "decrypting note",
            )

        try:
            note_data = self._get_note_from_cache_or_api(note_id)
            tags: list[str] = list(note_data.get("tags") or [])

            if VAULT_TAG not in tags:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "note_id": note_id,
                                "encrypted": False,
                                "message": "Note was not Vault-encrypted; no changes made.",
                            }
                        ),
                    )
                ]

            vault_key = self._resolve_vault_key()
            content = note_data.get("content", "") or ""
            try:
                note_data["content"] = decrypt_content(content, vault_key)
            except VaultDecryptionError as e:
                raise SecurityError(
                    str(e),
                    subcategory="decryption_failed",
                    resource_id=note_id,
                ) from e

            tags = [t for t in tags if t != VAULT_TAG]
            note_data["tags"] = tags

            updated_note, status = self.sn.update_note(note_data)
            if status != 0:
                raise NetworkError(f"Failed to decrypt note {note_id}")

            self._update_cache_after_operation(updated_note, "update")

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "note_id": note_id,
                            "encrypted": False,
                            "tags": updated_note.get("tags", []),
                            "message": "Note decrypted successfully.",
                        }
                    ),
                )
            ]

        except Exception as e:
            return self._format_error_response(
                e, f"decrypting note {note_id}", {"note_id": note_id}
            )


class VaultStatusHandler(ToolHandlerBase):
    """Handler for vault_status tool — read-only Vault key/encrypted-note status."""

    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle vault_status tool call."""
        del arguments  # no parameters

        encrypted_count = 0
        if self.note_cache is not None and self.note_cache.is_initialized:
            encrypted_count = len(self.note_cache._tag_index.get(VAULT_TAG, set()))

        key_available = False
        key_error: str | None = None
        try:
            key_available = has_vault_key()
        except VaultKeyCorruptedError as e:
            # A status check must not itself crash on a corrupted key — that
            # would defeat the point of being able to diagnose it.
            key_error = str(e)

        status: dict[str, Any] = {
            "success": True,
            "key_available": key_available,
            "key_provider": key_provider_name(),
            "encrypted_note_count": encrypted_count,
        }
        if key_error is not None:
            status["key_error"] = key_error

        return [
            types.TextContent(
                type="text",
                text=json.dumps(status),
            )
        ]
