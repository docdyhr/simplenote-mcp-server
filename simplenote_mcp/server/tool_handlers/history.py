"""Version history tools: list versions, restore a version."""

import json
from typing import Any

import mcp.types as types

from ..errors import (
    NetworkError,
    ResourceNotFoundError,
)
from ..security import validate_tool_security
from .base import (
    FAILED_GET_NOTE,
    ToolHandlerBase,
)


class GetNoteVersionsHandler(ToolHandlerBase):
    """Handler for get_note_versions tool — retrieve version history of a note."""

    MAX_VERSIONS = 10
    PREVIEW_MAX_LENGTH = 200

    @validate_tool_security("get_note_versions")
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle get_note_versions tool call."""
        from ..errors import ValidationError

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
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle restore_version tool call."""
        from ..errors import ValidationError

        note_id = arguments.get("note_id", "")
        version = arguments.get("version")

        if not note_id:
            raise ValidationError("note_id is required")
        if version is None:
            raise ValidationError("version is required")

        try:
            version = int(version)
        except (TypeError, ValueError) as exc:
            from ..errors import ValidationError as VE

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
