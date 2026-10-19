"""Publishing tools: publish and unpublish notes."""

import json
from typing import Any

import mcp.types as types

from ..errors import (
    NetworkError,
)
from ..security import validate_tool_security
from .base import (
    ToolHandlerBase,
)


class PublishNoteHandler(ToolHandlerBase):
    """Handler for publish_note tool — publish a note to a public URL."""

    @validate_tool_security("publish_note")
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
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
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
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
