"""Server and bulk tools: server info, export, duplicate merge."""

import json
from typing import Any

import mcp.types as types

from ..config import get_config
from ..errors import (
    NetworkError,
)
from ..security import validate_tool_security
from ..utils.common import (
    safe_split,
)
from ..vault import (
    VAULT_TAG,
)
from .base import (
    ToolHandlerBase,
)


class FindAndMergeDuplicatesHandler(ToolHandlerBase):
    """Handler for find_and_merge_duplicates tool."""

    @validate_tool_security("find_and_merge_duplicates")
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle find_and_merge_duplicates tool call.

        Finds duplicate notes and optionally merges them.
        """
        threshold = arguments.get("threshold", 0.8)
        dry_run = arguments.get("dry_run", True)
        tag_filter = arguments.get("tag_filter", "")

        # Validate threshold
        try:
            threshold = float(threshold)
            threshold = max(0.0, min(1.0, threshold))
        except (ValueError, TypeError):
            threshold = 0.8

        try:
            from ..duplicates import DuplicateFinder

            finder = DuplicateFinder(threshold=threshold)

            # Get all notes from cache or API. Vault-encrypted notes are
            # excluded — comparing ciphertext would never find a real
            # duplicate, and a false-positive "duplicate" match would risk
            # merging encrypted content into a plaintext note or vice versa.
            all_notes = [
                n
                for n in self._get_all_notes(tag_filter)
                if VAULT_TAG not in (n.get("tags") or [])
            ]

            if not all_notes:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "message": "No notes found to check for duplicates",
                                "groups": [],
                                "total_groups": 0,
                            }
                        ),
                    )
                ]

            # Find duplicate groups
            groups = finder.find_duplicates(all_notes)

            if not groups:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "message": f"No duplicates found among {len(all_notes)} notes (threshold: {threshold})",
                                "groups": [],
                                "total_groups": 0,
                                "notes_checked": len(all_notes),
                            }
                        ),
                    )
                ]

            if dry_run:
                return self._format_dry_run_response(groups, len(all_notes), threshold)
            else:
                return await self._perform_merge(
                    groups, finder, len(all_notes), threshold
                )

        except Exception as e:
            return self._format_error_response(e, "finding duplicates")

    def _get_all_notes(self, tag_filter: str) -> list[dict[str, Any]]:
        """Get all notes, optionally filtered by tag.

        Args:
            tag_filter: Tag to filter by, or empty string for all notes.

        Returns:
            List of note dictionaries.
        """
        if self.note_cache is not None and self.note_cache.is_initialized:
            if tag_filter:
                return self.note_cache.get_all_notes(tag_filter=tag_filter)
            return self.note_cache.get_all_notes()
        else:
            # Fallback to API
            all_notes, status = self.sn.get_note_list()
            if status != 0:
                raise NetworkError("Failed to retrieve notes for duplicate check")
            notes = all_notes if isinstance(all_notes, list) else []
            if tag_filter:
                notes = [n for n in notes if tag_filter in n.get("tags", [])]
            return notes

    def _format_dry_run_response(
        self,
        groups: list[list[dict[str, Any]]],
        total_notes: int,
        threshold: float,
    ) -> list[types.TextContent]:
        """Format response for dry run mode.

        Args:
            groups: List of duplicate groups.
            total_notes: Total notes checked.
            threshold: Similarity threshold used.

        Returns:
            Formatted response.
        """
        group_summaries = []
        for i, group in enumerate(groups):
            notes_in_group = []
            for note in group:
                content = note.get("content", "")
                title = content.split("\n", 1)[0].strip()[:80] if content else ""
                notes_in_group.append(
                    {
                        "id": note.get("key", ""),
                        "title": title,
                        "similarity": note.get("_similarity", 0),
                        "tags": note.get("tags", []),
                    }
                )
            group_summaries.append(
                {
                    "group": i + 1,
                    "count": len(group),
                    "notes": notes_in_group,
                }
            )

        total_duplicates = sum(len(g) - 1 for g in groups)
        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": True,
                        "dry_run": True,
                        "message": (
                            f"Found {len(groups)} duplicate group(s) with "
                            f"{total_duplicates} duplicate note(s) that could be merged"
                        ),
                        "groups": group_summaries,
                        "total_groups": len(groups),
                        "total_duplicates": total_duplicates,
                        "notes_checked": total_notes,
                        "threshold": threshold,
                    }
                ),
            )
        ]

    async def _perform_merge(
        self,
        groups: list[list[dict[str, Any]]],
        finder: Any,
        total_notes: int,
        threshold: float,
    ) -> list[types.TextContent]:
        """Perform actual merge of duplicate groups.

        Args:
            groups: List of duplicate groups.
            finder: DuplicateFinder instance.
            total_notes: Total notes checked.
            threshold: Similarity threshold used.

        Returns:
            Formatted response with merge results.
        """
        merged_count = 0
        trashed_count = 0
        errors = []

        for group in groups:
            try:
                # Merge the group
                merged_note = finder.merge_group(group)
                winner_id = merged_note.get("key", "")

                # Update the winning note with merged tags
                updated_note, status = self.sn.update_note(merged_note)
                if status != 0:
                    errors.append(f"Failed to update note {winner_id}")
                    continue

                if isinstance(updated_note, dict):
                    self._update_cache_after_operation(updated_note, "update")

                # Trash the duplicate notes (skip the winner)
                for note in group[1:]:
                    dup_id = note.get("key", "")
                    if dup_id and dup_id != winner_id:
                        trash_result = self.sn.trash_note(dup_id)
                        # trash_note returns a tuple (note, status)
                        _trash_note, trash_status = (
                            trash_result
                            if isinstance(trash_result, tuple)
                            else (None, trash_result)
                        )
                        if trash_status == 0:
                            self._update_cache_after_operation(dup_id, "delete")
                            trashed_count += 1
                        else:
                            errors.append(f"Failed to trash note {dup_id}")

                merged_count += 1
            except Exception as e:
                errors.append(str(e))

        response: dict[str, Any] = {
            "success": True,
            "dry_run": False,
            "message": (
                f"Merged {merged_count} group(s), trashed {trashed_count} duplicate note(s)"
            ),
            "groups_merged": merged_count,
            "notes_trashed": trashed_count,
            "notes_checked": total_notes,
            "threshold": threshold,
        }
        if errors:
            response["errors"] = errors

        return [types.TextContent(type="text", text=json.dumps(response))]


class ExportNotesHandler(ToolHandlerBase):
    """Handler for export_notes tool."""

    @validate_tool_security("export_notes")
    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle export_notes tool call.

        Exports one or more notes to Markdown or JSON format.
        """
        note_ids_input = arguments.get("note_ids", "")
        fmt = arguments.get("format", "markdown").lower()
        include_metadata = arguments.get("include_metadata", True)

        if not note_ids_input:
            from ..error_helpers import empty_field_error

            raise empty_field_error("note_ids")

        # Parse note IDs (comma-separated)
        if isinstance(note_ids_input, list):
            note_ids = [str(nid).strip() for nid in note_ids_input if str(nid).strip()]
        elif isinstance(note_ids_input, str):
            note_ids = [
                nid.strip() for nid in safe_split(note_ids_input, ",") if nid.strip()
            ]
        else:
            note_ids = []

        if not note_ids:
            from ..error_helpers import empty_field_error

            raise empty_field_error("note_ids")

        # Validate format
        if fmt not in ("markdown", "json"):
            fmt = "markdown"

        try:
            from ..export import NoteExporter

            exporter = NoteExporter()
            notes = []
            errors = []

            for note_id in note_ids:
                try:
                    note = self._get_note_from_cache_or_api(note_id)
                    notes.append(note)
                except Exception:
                    errors.append(note_id)

            if not notes:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": False,
                                "message": "No notes found for the given IDs",
                                "failed_ids": errors,
                            }
                        ),
                    )
                ]

            exported = exporter.export_batch(notes, fmt, include_metadata)

            response: dict[str, Any] = {
                "success": True,
                "format": fmt,
                "count": len(notes),
                "exported": exported,
            }
            if errors:
                response["failed_ids"] = errors

            return [types.TextContent(type="text", text=json.dumps(response))]

        except Exception as e:
            return self._format_error_response(e, "exporting notes")


class GetServerInfoHandler(ToolHandlerBase):
    """Handler for get_server_info tool — returns version, author, and debug info."""

    async def handle(
        self, arguments: dict[str, Any]
    ) -> list[types.TextContent] | types.CallToolResult:
        """Handle get_server_info tool call."""
        import platform
        import sys

        import simplenote_mcp

        from ..server import get_last_auth_error
        from .registry import ToolHandlerRegistry  # lazy: registry imports this module

        config = get_config()
        registry = ToolHandlerRegistry()

        authenticated = bool(getattr(self.sn, "token", None))
        last_sync_error = get_last_auth_error()

        cache_initialized = bool(self.note_cache and self.note_cache.is_initialized)
        note_count: int | None = None
        if cache_initialized and self.note_cache is not None:
            try:
                note_count = len(self.note_cache._notes)
            except Exception:
                note_count = None

        # cache_initialized is honest: True only when auth succeeded and notes loaded.
        cache_healthy = cache_initialized and (note_count is None or note_count > 0)

        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": True,
                        "name": "simplenote-mcp-server",
                        "version": simplenote_mcp.__version__,
                        "author": "Thomas Juul Dyhr",
                        "description": "MCP server integrating Simplenote with Claude Desktop",
                        "tool_count": len(registry.list_tools()),
                        "debug": {
                            "python_version": sys.version,
                            "platform": platform.platform(),
                            "authenticated": authenticated,
                            "cache_initialized": cache_initialized,
                            "cache_healthy": cache_healthy,
                            "note_count": note_count,
                            "last_sync_error": last_sync_error,
                            "sync_interval_seconds": config.sync_interval_seconds,
                            "log_level": config.log_level.value
                            if hasattr(config.log_level, "value")
                            else str(config.log_level),
                            "offline_mode": config.offline_mode,
                            "cache_max_size": config.cache_max_size,
                        },
                    }
                ),
            )
        ]
