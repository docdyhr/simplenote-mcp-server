"""Tag tools: add, remove, replace, rename, list, untagged, bulk."""

import json
from typing import Any

import mcp.types as types

from ..decorators import (
    validate_note_id_required,
    validate_tags_required,
    with_input_validation,
)
from ..error_helpers import (
    empty_field_error,
)
from ..errors import (
    InternalError,
    NetworkError,
)
from ..logging import logger
from ..security import validate_tool_security
from ..utils.common import (
    safe_get,
    safe_set,
)
from .base import (
    FAILED_UPDATE_TAGS,
    ToolHandlerBase,
    extract_title_from_content,
)


class TagOperationHandler(ToolHandlerBase):
    """Base handler for tag operations (add, remove, replace)."""

    # _parse_tags is inherited from ToolHandlerBase


class AddTagsHandler(TagOperationHandler):
    """Handler for add_tags tool."""

    @validate_tool_security("add_tags")
    @with_input_validation(validate_note_id_required, validate_tags_required)
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle add_tags tool call."""
        note_id = arguments.get("note_id", "")
        tags_input = arguments.get("tags", "")

        if not note_id:
            raise empty_field_error("note_id")

        if not tags_input:
            raise empty_field_error("tags")

        try:
            existing_note = self._get_note_from_cache_or_api(note_id)

            # Parse the tags to add (comma-separated or list); spaces → hyphens
            tags_to_add = [tag for tag in self._parse_tags(tags_input) if tag]

            # Get current tags or initialize empty list
            current_tags = safe_get(existing_note, "tags", [])
            if current_tags is None:
                current_tags = []

            # Add new tags that aren't already present
            added_tags = []
            for tag in tags_to_add:
                if tag not in current_tags:
                    current_tags.append(tag)
                    added_tags.append(tag)

            # Only update if tags were actually added
            if added_tags:
                # Update the note
                existing_note["tags"] = current_tags
                updated_note, status = self.sn.update_note(existing_note)

                if status == 0:
                    # Check if the result is actually a dictionary
                    if not isinstance(updated_note, dict):
                        logger.error(
                            f"API call success status 0, but returned non-dict: {type(updated_note)} for add_tags"
                        )
                        raise InternalError(
                            "Unexpected API response type after adding tags."
                        )

                    self._update_cache_after_operation(updated_note, "update")

                    final_tags = updated_note.get("tags", [])
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "success": True,
                                    "message": f"Added tags: {', '.join(added_tags)}",
                                    "note_id": updated_note.get("key"),
                                    "tags_added": added_tags,
                                    "tags_now": final_tags,
                                    "tags": final_tags,
                                }
                            ),
                        )
                    ]
                else:
                    logger.error(FAILED_UPDATE_TAGS)
                    raise NetworkError(FAILED_UPDATE_TAGS)
            else:
                # No tags were added (all already present)
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "message": "No new tags to add (all tags already present)",
                                "note_id": note_id,
                                "tags_added": [],
                                "tags_now": current_tags,
                                "tags": current_tags,
                            }
                        ),
                    )
                ]

        except Exception as e:
            return self._format_error_response(
                e, f"adding tags to note {note_id}", {"note_id": note_id}
            )


class RemoveTagsHandler(TagOperationHandler):
    """Handler for remove_tags tool."""

    @validate_tool_security("remove_tags")
    @with_input_validation(validate_note_id_required, validate_tags_required)
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle remove_tags tool call."""
        note_id = arguments.get("note_id", "")
        tags_input = arguments.get("tags", "")

        if not note_id:
            raise empty_field_error("note_id")

        if not tags_input:
            raise empty_field_error("tags")

        try:
            existing_note = self._get_note_from_cache_or_api(note_id)

            # Parse the tags to remove (comma-separated or list); spaces → hyphens,
            # so this matches the hyphenated form other handlers already stored.
            tags_to_remove = [tag for tag in self._parse_tags(tags_input) if tag]

            # Get current tags or initialize empty list
            current_tags = safe_get(existing_note, "tags", [])
            if current_tags is None:
                current_tags = []

            # If the note has no tags, nothing to do
            if not current_tags:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "message": "Note had no tags to remove",
                                "note_id": note_id,
                                "tags_removed": [],
                                "tags_now": [],
                                "tags": [],
                            }
                        ),
                    )
                ]

            # Remove specified tags that are present
            removed_tags = []
            new_tags = []
            for tag in current_tags:
                if tag in tags_to_remove:
                    removed_tags.append(tag)
                else:
                    new_tags.append(tag)

            # Only update if tags were actually removed
            if removed_tags:
                # Update the note
                safe_set(existing_note, "tags", new_tags)
                updated_note, status = self.sn.update_note(existing_note)

                if status == 0:
                    # Check if the result is actually a dictionary
                    if not isinstance(updated_note, dict):
                        logger.error(
                            f"API call success status 0, but returned non-dict: {type(updated_note)} for remove_tags"
                        )
                        raise InternalError(
                            "Unexpected API response type after removing tags."
                        )

                    self._update_cache_after_operation(updated_note, "update")

                    final_tags = updated_note.get("tags", [])
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "success": True,
                                    "message": f"Removed tags: {', '.join(removed_tags)}",
                                    "note_id": updated_note.get("key"),
                                    "tags_removed": removed_tags,
                                    "tags_now": final_tags,
                                    "tags": final_tags,
                                }
                            ),
                        )
                    ]
                else:
                    logger.error(FAILED_UPDATE_TAGS)
                    raise NetworkError(FAILED_UPDATE_TAGS)
            else:
                # No tags were removed (none were present)
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "message": "No tags were removed (specified tags not present on note)",
                                "note_id": note_id,
                                "tags_removed": [],
                                "tags_now": current_tags,
                                "tags": current_tags,
                            }
                        ),
                    )
                ]

        except Exception as e:
            return self._format_error_response(
                e, f"removing tags from note {note_id}", {"note_id": note_id}
            )


class ReplaceTagsHandler(TagOperationHandler):
    """Handler for replace_tags tool."""

    @validate_tool_security("replace_tags")
    @with_input_validation(validate_note_id_required, validate_tags_required)
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle replace_tags tool call."""
        note_id = arguments.get("note_id", "")
        tags_input = arguments.get("tags", "")

        if not note_id:
            raise empty_field_error("note_id")

        try:
            existing_note = self._get_note_from_cache_or_api(note_id)

            # Parse the new tags (comma-separated), spaces → hyphens
            new_tags = self._parse_tags(tags_input)

            # Get current tags
            current_tags = safe_get(existing_note, "tags", [])
            if current_tags is None:
                current_tags = []

            # Update the note with new tags
            safe_set(existing_note, "tags", new_tags)
            updated_note, status = self.sn.update_note(existing_note)

            if status == 0:
                # Check if the result is actually a dictionary
                if not isinstance(updated_note, dict):
                    logger.error(
                        f"API call success status 0, but returned non-dict: {type(updated_note)} for replace_tags"
                    )
                    raise InternalError(
                        "Unexpected API response type after replacing tags."
                    )

                self._update_cache_after_operation(updated_note, "update")

                # Generate appropriate message based on whether tags were changed
                if set(current_tags) == set(new_tags):
                    message = "Tags unchanged (new tags same as existing tags)"
                else:
                    message = f"Replaced tags: {', '.join(current_tags)} → {', '.join(new_tags)}"

                final_tags = updated_note.get("tags", [])
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "message": message,
                                "note_id": updated_note.get("key"),
                                "tags_now": final_tags,
                                "tags": final_tags,
                            }
                        ),
                    )
                ]
            else:
                error_msg = "Failed to update note tags"
                logger.error(error_msg)
                raise NetworkError(error_msg)

        except Exception as e:
            return self._format_error_response(
                e, f"replacing tags on note {note_id}", {"note_id": note_id}
            )


class RenameTagHandler(ToolHandlerBase):
    """Handler for rename_tag tool — atomically rename a tag across all notes."""

    @validate_tool_security("rename_tag")
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle rename_tag tool call."""
        from ..errors import ValidationError

        old_tag = arguments.get("old_tag", "")
        new_tag = arguments.get("new_tag", "")
        dry_run = bool(arguments.get("dry_run", False))

        if not old_tag:
            raise ValidationError("old_tag is required")
        if not new_tag:
            raise ValidationError("new_tag is required")

        # Sanitize: spaces to hyphens (shared with every other tag-accepting tool)
        new_tag = self._parse_tags([new_tag])[0]
        old_tag = old_tag.strip()

        try:
            # Find notes that have the old tag
            note_ids: set[str] = set()
            if self.note_cache is not None and self.note_cache.is_initialized:
                note_ids = self.note_cache._tag_index.get(old_tag, set())

            if not note_ids:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "updated_count": 0,
                                "note_ids": [],
                                "dry_run": dry_run,
                                "message": f"Tag '{old_tag}' not found on any notes",
                            }
                        ),
                    )
                ]

            updated_ids = []
            errors = []

            for note_id in note_ids:
                note = None
                if self.note_cache is not None and self.note_cache.is_initialized:
                    note = self.note_cache._notes.get(note_id)
                if note is None:
                    note_data, status = self.sn.get_note(note_id)
                    if status != 0 or not isinstance(note_data, dict):
                        errors.append(note_id)
                        continue
                    note = note_data

                current_tags = list(note.get("tags", []))
                if old_tag not in current_tags:
                    continue

                new_tags = [new_tag if t == old_tag else t for t in current_tags]

                if not dry_run:
                    note_copy = dict(note)
                    note_copy["tags"] = new_tags
                    updated, ustatus = self.sn.update_note(note_copy)
                    if ustatus == 0 and isinstance(updated, dict):
                        self._update_cache_after_operation(updated, "update")
                        updated_ids.append(note_id)
                    else:
                        errors.append(note_id)
                else:
                    updated_ids.append(note_id)

            response: dict[str, Any] = {
                "success": True,
                "updated_count": len(updated_ids),
                "note_ids": sorted(updated_ids),
                "dry_run": dry_run,
                "old_tag": old_tag,
                "new_tag": new_tag,
            }
            if errors:
                response["failed_ids"] = errors

            return [types.TextContent(type="text", text=json.dumps(response))]

        except Exception as e:
            return self._format_error_response(
                e, f"renaming tag '{old_tag}' to '{new_tag}'"
            )


class ListTagsHandler(ToolHandlerBase):
    """Handler for list_tags tool — list all tags with note counts."""

    @validate_tool_security("list_tags")
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle list_tags tool call."""
        sort_by = arguments.get("sort_by", "alpha")

        if self.note_cache is None or not self.note_cache.is_initialized:
            return self._format_error_response(
                InternalError("Note cache is not initialized. Cannot list tags."),
                "listing tags",
            )

        try:
            tag_index = self.note_cache._tag_index
            tags = [
                {"tag": tag, "note_count": len(note_ids)}
                for tag, note_ids in tag_index.items()
            ]

            if sort_by == "count":
                tags.sort(key=lambda t: t["note_count"], reverse=True)
            else:
                tags.sort(key=lambda t: t["tag"])

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "tags": tags,
                            "total_tags": len(tags),
                            "sort_by": sort_by,
                        }
                    ),
                )
            ]

        except Exception as e:
            return self._format_error_response(e, "listing tags")


class FindUntaggedNotesHandler(ToolHandlerBase):
    """Handler for find_untagged_notes tool — list notes with no tags."""

    @validate_tool_security("find_untagged_notes")
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle find_untagged_notes tool call."""
        if self.note_cache is None or not self.note_cache.is_initialized:
            return self._format_error_response(
                InternalError(
                    "Note cache is not initialized. Cannot find untagged notes."
                ),
                "finding untagged notes",
            )

        try:
            limit = arguments.get("limit", 50)
            try:
                limit = int(limit)
                if limit <= 0:
                    limit = 50
            except (TypeError, ValueError):
                limit = 50

            untagged = self.note_cache._filter_notes_by_untagged()
            notes_list = list(untagged.values())[:limit]

            results = []
            for note in notes_list:
                content = note.get("content", "")
                snippet = content[:100].replace("\n", " ") if content else ""
                results.append(
                    {
                        "id": note.get("key", ""),
                        "title": extract_title_from_content(
                            content, note.get("key", "")
                        ),
                        "snippet": snippet,
                        "tags": note.get("tags", []),
                    }
                )

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "notes": results,
                            "count": len(results),
                        }
                    ),
                )
            ]

        except Exception as e:
            return self._format_error_response(e, "finding untagged notes")


class BulkTagHandler(ToolHandlerBase):
    """Handler for bulk_tag tool — add/remove/set tags on multiple notes at once."""

    VALID_ACTIONS = {"add", "remove", "set"}

    @validate_tool_security("bulk_tag")
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle bulk_tag tool call."""
        note_ids = arguments.get("note_ids")
        action = arguments.get("action")
        tags_input = arguments.get("tags", [])

        if not note_ids:
            return self._format_error_response(
                ValueError("note_ids is required"),
                "bulk tagging notes",
            )
        if not action:
            return self._format_error_response(
                ValueError("action is required (add, remove, or set)"),
                "bulk tagging notes",
            )
        if action not in self.VALID_ACTIONS:
            return self._format_error_response(
                ValueError(
                    f"Unknown action '{action}'. Must be one of: "
                    f"{', '.join(sorted(self.VALID_ACTIONS))}"
                ),
                "bulk tagging notes",
            )

        tags = self._parse_tags(tags_input)

        updated = 0
        failed: list[str] = []

        for note_id in note_ids:
            try:
                note_data, status = self.sn.get_note(note_id)
                if status != 0:
                    failed.append(note_id)
                    continue

                current_tags: list[str] = note_data.get("tags") or []

                if action == "add":
                    new_tags = list(dict.fromkeys(current_tags + tags))
                elif action == "remove":
                    new_tags = [t for t in current_tags if t not in tags]
                else:  # set
                    new_tags = tags

                note_data["tags"] = new_tags
                _, upd_status = self.sn.update_note(note_data)
                if upd_status == 0:
                    updated += 1
                    if self.note_cache:
                        self.note_cache._notes[note_id] = note_data
                else:
                    failed.append(note_id)

            except Exception:
                failed.append(note_id)

        response: dict[str, Any] = {
            "success": True,
            "action": action,
            "updated": updated,
            "failed": failed,
        }

        return [types.TextContent(type="text", text=json.dumps(response))]
