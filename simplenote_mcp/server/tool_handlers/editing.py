"""In-place content editing tools: append text, replace a section, daily note."""

import json
from datetime import date, datetime
from typing import Any

import mcp.types as types

from ..errors import (
    NetworkError,
    ResourceNotFoundError,
)
from ..security import validate_tool_security
from .base import (
    ToolHandlerBase,
)


class AddTextHandler(ToolHandlerBase):
    """Handler for add_text tool — non-destructive append/prepend to a note."""

    @validate_tool_security("add_text")
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle add_text tool call."""
        from ..errors import ValidationError

        note_id = arguments.get("note_id", "")
        text = arguments.get("text", "")
        position = arguments.get("position", "end")

        if not note_id:
            raise ValidationError("note_id is required")
        if not text:
            raise ValidationError("text is required")
        if position not in ("end", "beginning"):
            raise ValidationError(
                f"Invalid position '{position}'. Must be 'end' or 'beginning'."
            )

        try:
            existing_note = self._get_note_from_cache_or_api(note_id)
            self._guard_against_blind_mutation(existing_note, note_id, "add_text")
            existing_content = existing_note.get("content", "")

            if position == "end":
                new_content = (
                    f"{existing_content}\n{text}" if existing_content else text
                )
            else:
                new_content = (
                    f"{text}\n{existing_content}" if existing_content else text
                )

            existing_note["content"] = new_content
            updated_note, status = self.sn.update_note(existing_note)

            if status == 0 and isinstance(updated_note, dict):
                self._update_cache_after_operation(updated_note, "update")
                final_content = updated_note.get("content", new_content)
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "note_id": updated_note.get("key", note_id),
                                "position": position,
                                "content_length": len(final_content),
                                "tags": updated_note.get("tags", []),
                            }
                        ),
                    )
                ]
            else:
                raise NetworkError("Failed to update note after adding text")

        except Exception as e:
            return self._format_error_response(
                e, f"adding text to note {note_id}", {"note_id": note_id}
            )


class ReplaceSectionHandler(ToolHandlerBase):
    """Handler for replace_section tool — surgical Markdown section replacement."""

    @validate_tool_security("replace_section")
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle replace_section tool call."""
        from ..errors import ValidationError

        note_id = arguments.get("note_id", "")
        header = arguments.get("header", "")
        new_content = arguments.get("new_content", "")

        if not note_id:
            raise ValidationError("note_id is required")
        if not header:
            raise ValidationError("header is required")

        try:
            note = self._get_note_from_cache_or_api(note_id)
            self._guard_against_blind_mutation(note, note_id, "replace_section")
            content = note.get("content", "")

            # Split content into lines and find the target section
            lines = content.split("\n")
            section_start = None
            section_end = None

            # Find the section start (line matching ## <header> or # <header>)
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped == f"## {header}" or stripped == f"# {header}":
                    section_start = i
                    break

            if section_start is None:
                return self._format_error_response(
                    ResourceNotFoundError(
                        f"Section '{header}' not found in note {note_id}",
                        resource_id=note_id,
                    ),
                    f"replacing section '{header}' in note {note_id}",
                )

            # Find the end of this section (next ## or # heading or EOF)
            for i in range(section_start + 1, len(lines)):
                if lines[i].startswith("## ") or lines[i].startswith("# "):
                    section_end = i
                    break

            # Rebuild content
            header_line = lines[section_start]
            before = lines[:section_start]
            if section_end is not None:
                after = lines[section_end:]
                new_lines = before + [header_line, new_content, ""] + after
            else:
                new_lines = before + [header_line, new_content]

            updated_content = "\n".join(new_lines).rstrip("\n")

            note["content"] = updated_content
            updated_note, status = self.sn.update_note(note)
            if status != 0:
                raise NetworkError(
                    f"Failed to update note {note_id} after section replacement"
                )

            if isinstance(updated_note, dict):
                self._update_cache_after_operation(updated_note, "update")

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "note_id": note_id,
                            "header": header,
                            "content_length": len(updated_content),
                        }
                    ),
                )
            ]

        except Exception as e:
            return self._format_error_response(
                e,
                f"replacing section '{header}' in note {note_id}",
                {"note_id": note_id},
            )


class AppendToDailyNoteHandler(ToolHandlerBase):
    """Handler for append_to_daily_note tool — timestamped journaling."""

    @validate_tool_security("append_to_daily_note")
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle append_to_daily_note tool call."""
        from ..errors import ValidationError

        text = arguments.get("text", "")
        if not text:
            raise ValidationError("text is required")

        today_str = date.today().isoformat()
        time_str = datetime.now().strftime("%H:%M")
        timestamped_entry = f"{time_str} {text}"

        try:
            # Find or create today's daily note
            daily_note = None
            note_id = None

            if self.note_cache is not None and self.note_cache.is_initialized:
                results = await self.note_cache.search_notes(query=today_str)
                for note in results:
                    content = note.get("content", "")
                    first_line = content.split("\n", 1)[0].strip()
                    clean = first_line.lstrip("#").strip()
                    if clean == today_str or first_line == today_str:
                        daily_note = note
                        note_id = note.get("key")
                        break

            if daily_note is None:
                # Create the daily note
                initial_content = f"# {today_str}\n{timestamped_entry}"
                new_note_data: dict[str, Any] = {"content": initial_content}
                created_note, status = self.sn.add_note(new_note_data)
                if status != 0:
                    raise NetworkError("Failed to create daily note")
                if isinstance(created_note, dict):
                    self._update_cache_after_operation(created_note, "create")
                result_note = created_note if isinstance(created_note, dict) else {}
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "note_id": result_note.get("key"),
                                "date": today_str,
                                "created": True,
                                "entry": timestamped_entry,
                            }
                        ),
                    )
                ]
            else:
                # Append to existing daily note
                existing_content = daily_note.get("content", "")
                new_content = f"{existing_content}\n{timestamped_entry}"
                daily_note = dict(daily_note)
                daily_note["content"] = new_content
                updated_note, ustatus = self.sn.update_note(daily_note)
                if ustatus != 0:
                    raise NetworkError("Failed to update daily note")
                if isinstance(updated_note, dict):
                    self._update_cache_after_operation(updated_note, "update")
                result_note = (
                    updated_note if isinstance(updated_note, dict) else daily_note
                )
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "note_id": result_note.get("key", note_id),
                                "date": today_str,
                                "created": False,
                                "entry": timestamped_entry,
                            }
                        ),
                    )
                ]

        except Exception as e:
            return self._format_error_response(
                e, f"appending to daily note for {today_str}"
            )
