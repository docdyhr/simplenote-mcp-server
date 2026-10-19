"""Trash lifecycle tools: delete, restore, permanent delete, empty trash."""

import json
from typing import Any

import mcp.types as types

from ..decorators import (
    validate_note_id_required,
    with_input_validation,
)
from ..error_helpers import (
    empty_field_error,
)
from ..errors import (
    NetworkError,
    ResourceNotFoundError,
)
from ..logging import logger
from ..security import validate_tool_security
from .base import (
    FAILED_TRASH_NOTE,
    ToolHandlerBase,
    extract_title_from_content,
)


class DeleteNoteHandler(ToolHandlerBase):
    """Handler for delete_note tool."""

    @validate_tool_security("delete_note")
    @with_input_validation(validate_note_id_required)
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
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


class RestoreNoteHandler(ToolHandlerBase):
    """Handler for restore_note tool — un-trash a deleted note."""

    @validate_tool_security("restore_note")
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
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


class PermanentDeleteNoteHandler(ToolHandlerBase):
    """Handler for permanent_delete_note tool — irreversibly destroy a note."""

    @validate_tool_security("permanent_delete_note")
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
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
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
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
