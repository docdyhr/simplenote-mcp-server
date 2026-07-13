# Live Testing Guide — Simplenote MCP v1.17.1

Paste each prompt block into Claude Desktop to verify the tool works.
Run them in order — later tests depend on notes created earlier.

Sections 19-20 (Vault, Companion Architecture) were additionally verified by an
automated harness — `simplenote_mcp/scripts/live_test_redesign.py` — that drives
the real server subprocess over the actual MCP stdio protocol with
`mcp.ClientSession`, rather than mocking the Simplenote client the way the unit
suite does. Run it with `SIMPLENOTE_EMAIL`/`SIMPLENOTE_PASSWORD` set:
`.venv/bin/python simplenote_mcp/scripts/live_test_redesign.py`. It creates and
trashes its own `LiveTest-Redesign-`-prefixed notes and cleans up after itself,
including on failure. Last run: 2026-07-13, 35/35 checks passed.

---

## 0. Smoke Test

> Are you connected to Simplenote? List my tags and tell me how many notes I have.

**Expect**: Tag list (or "no tags yet"), note count from the cache. Confirms the server is running and authenticated.

---

## 1. Server Info

> Use get_server_info to show me which version of the Simplenote MCP server is running and whether the cache is initialized.

**Expect**: `success: true`, `version: "1.13.0"`, `author: "Thomas Juul Dyhr"`, `tool_count: 22`, and a `debug` block containing `python_version`, `platform`, `cache_initialized`, `sync_interval_seconds`, `log_level`, and `offline_mode`.

> Call get_server_info again after the cache has had time to initialize.

**Expect**: `debug.cache_initialized: true` and `debug.note_count` showing a number.

---

## 2. Create Notes

> Create a Simplenote note with this content:
>
> ```
> # Live Test Note
>
> This note was created during v1.13.0 live testing.
> ```
>
> Tag it with `test` and `live-test`.

**Expect**: Note created, returns a note ID. Save the ID — you'll use it below.

> Create another note titled "Live Test Log" with just the title as content. Tag it `test`.

**Expect**: Second note created.

---

## 3. Get a Note

> Get the note you just created (the "Live Test Note") and show me its full content, tags, and modification date.

**Expect**: Full note content, `["test", "live-test"]` tag array, ISO datetime.

---

## 4. Add Text (append / prepend)

> Append this line to the Live Test Note:
>
> ```
> Status: verified
> ```

**Expect**: Note content now ends with `Status: verified`. Original content untouched.

> Now prepend this line to the same note:
>
> ```
> > Last updated during live test
> ```

**Expect**: Note starts with the blockquote. Both previous lines still present.

---

## 5. Replace Section

> The Live Test Note has a `# Live Test Note` heading at the top. Replace that section with this content:
>
> ```
> This note was updated by replace_section during live testing.
> Version: 1.13.0
> ```

**Expect**: Only the content under the first heading changed. The `Status: verified` line still present.

---

## 6. Update Note (full overwrite)

> Update the Live Test Log note so its full content is:
>
> ```
> # Live Test Log
>
> ## Session 1
> Initial entry.
>
> ## Session 2
> Second entry.
> ```

**Expect**: Full content replaced. Old content gone.

---

## 7. Tags

> Add the tag `verified` to the Live Test Note.

**Expect**: Returns `tags_now` array containing `test`, `live-test`, and `verified`.

> Remove the tag `live-test` from the Live Test Note.

**Expect**: Returns `tags_now` with `live-test` absent.

> Replace all tags on the Live Test Note with just `archived`.

**Expect**: Returns `tags_now: ["archived"]`.

---

## 8. List Tags

> List all my Simplenote tags sorted by note count.

**Expect**: Table/list of `{tag, note_count}` pairs. Should include `test` and `archived` from above.

---

## 9. Search Notes

> Search my notes for "live test".

**Expect**: Both test notes appear in results.

> Search my notes for tag:test.

**Expect**: Notes tagged `test` returned.

> Search my notes modified after today's date (use ISO format).

**Expect**: The notes you just modified appear.

> Search my notes with pinned=true.

**Expect**: Any pinned notes returned, or empty list if none are pinned.

---

## 10. Get or Create Note

> Find or create a note titled "Live Test — Idempotent". Tell me if it was newly created or already existed.

**Expect**: `created: true` on first call.

> Run the same request again.

**Expect**: `created: false` — same note returned, no duplicate.

---

## 11. Append to Daily Note

> Append this entry to today's daily note: "Live test in progress — v1.13.0 verified"

**Expect**: Note titled today's date (YYYY-MM-DD) created (or found). Entry appended with HH:MM timestamp prefix.

> Append another entry: "Second test entry"

**Expect**: Both entries visible in the daily note with separate timestamps.

---

## 12. Find Untagged Notes

> Find my untagged notes (limit 10).

**Expect**: Notes with no tags. The "Live Test — Idempotent" note may appear here if no tags were given.

---

## 13. Bulk Tag

> Apply the tag `bulk-test` to both the Live Test Note and the Live Test Log note in one call.

**Expect**: `updated_count: 2`, `failed_ids: []`.

---

## 14. Rename Tag

> Do a dry run of renaming the tag `bulk-test` to `bulk-verified`. Don't write any changes yet.

**Expect**: Preview showing which notes would be updated, `updated_count` > 0, no changes written.

> Now rename the tag `bulk-test` to `bulk-verified` for real.

**Expect**: Same notes updated, changes written.

---

## 15. Version History

> Show me the version history of the Live Test Note.

**Expect**: List of versions (newest first), each with version number, modified date, and a content preview. Should show multiple versions from the edits above.

> Restore the Live Test Note to version 1.

**Expect**: Note content rolled back to the original creation content.

---

## 16. Export Notes

> Export all notes tagged `test` as Markdown.

**Expect**: Markdown export containing the test notes.

---

## 17. Find and Merge Duplicates

> Check for duplicate notes in my account. Do a dry run only.

**Expect**: Either "no duplicates found" or a list of candidate groups with a preview — no changes written.

---

## 18. Soft Delete and Restore

> Move the "Live Test — Idempotent" note to Trash.

**Expect**: Note deleted (moved to Trash). `delete_note` confirms.

> Restore that note from Trash.

**Expect**: Note back in the main note list.

---

## 19. Vault — Client-Side Encryption

**Automated result (2026-07-13)**: PASS — all sub-checks below confirmed by
`live_test_redesign.py` against the real Simplenote account.

> Call vault_status. Tell me whether a key is available and which provider it's using.

**Expect**: `key_available` (bool), `key_provider` (`"keyring"` or `"file"`), `encrypted_note_count`. First call may trigger a one-time macOS Keychain approval dialog — approve it.

> Create a note with content "Vault Test\nThis is sensitive test data — SSN 000-00-0000" and encrypt=true.

**Expect**: `success: true`, `encrypted: true`, `tags` includes `vault-encrypted`. Note this note's ID.

> Get that note back.

**Expect**: `encrypted: true`, `decryptable: true`, `content` shows the full original text including "SSN 000-00-0000" — decrypted transparently. `title` shows "Vault Test".

> Search my notes for "sensitive test data".

**Expect**: The Vault note does NOT appear (body isn't searchable — this is a documented limitation, not a bug).

> Search my notes for "Vault Test".

**Expect**: The Vault note DOES appear (title stays searchable), and its snippet shows only the title, never the encrypted body or raw ciphertext.

> Try to append text to the Vault Test note with add_text.

**Expect**: A clear error explaining the note is Vault-encrypted and to use decrypt_note first — NOT a corrupted note, NOT silently-added plaintext.

> Decrypt the Vault Test note.

**Expect**: `success: true`, `encrypted: false`. Getting the note now shows plain content with no `%%SNVAULT:v1%%` marker.

> Encrypt the Vault Test note again, then check vault_status.

**Expect**: `encrypted_note_count` increased by 1 versus the first vault_status call.

---

## 20. MCP Resources & Prompts — Companion Architecture

**Automated result (2026-07-13)**: PASS — all sub-checks below confirmed by
`live_test_redesign.py`, including the exact regression this section exists to
catch: `read_resource` previously crashed on every real call (see CHANGELOG
"Fixed" — `'tuple' object has no attribute 'content'`) because the handler
returned the wrong type for the MCP SDK's `@server.read_resource()` decorator.
No unit test caught this since they all called the handler function directly,
bypassing the decorator; only driving the real stdio protocol surfaced it.

> List the available Simplenote resources.

**Expect**: A list of `simplenote://note/<id>` resources. This exercises `handle_list_resources` — each resource's tags and modify/create dates are attached via the MCP `_meta` field (not visible as prose, but the description text should mention the note's tags).

> Read the resource for one of the notes returned above (ask Claude to fetch its content via the resource, not via get_note).

**Expect**: The note's content comes back without error. Before the fix in this section, this call crashed with `'tuple' object has no attribute 'content'` on every invocation — if it errors, that's a live regression, not a flaky test.

> Use the session_handoff_prompt to draft a handoff note for a project called "test-project", with status "wrapping up live testing" and next steps "none".

**Expect**: A prompt response instructing Claude to call `get_or_create_note` and `add_text` with a `Status:`/`Next:`/`Blockers:` formatted body, mentioning "test-project".

---

## 21. Cleanup

> Delete the following test notes (move to Trash):
> - Live Test Note
> - Live Test Log
> - Live Test — Idempotent
> - Vault Test
> - Today's daily note (YYYY-MM-DD)

**Expect**: All moved to Trash. Verify with a search for "live test" — should return empty or only trashed notes.

---

## Pass Criteria

| # | Tool(s) | Pass? |
|---|---------|-------|
| 0 | `list_tags` + smoke test | |
| 1 | `get_server_info` (version, debug, cache status) | |
| 2 | `create_note` | |
| 3 | `get_note` | |
| 4 | `add_text` (append + prepend) | |
| 5 | `replace_section` | |
| 6 | `update_note` | |
| 7 | `add_tags`, `remove_tags`, `replace_tags` | |
| 8 | `list_tags` (sorted) | |
| 9 | `search_notes` (text, tag, date, pinned) | |
| 10 | `get_or_create_note` (idempotency) | |
| 11 | `append_to_daily_note` | |
| 12 | `find_untagged_notes` | |
| 13 | `bulk_tag` | |
| 14 | `rename_tag` (dry run + live) | |
| 15 | `get_note_versions` + `restore_version` | |
| 16 | `export_notes` | |
| 17 | `find_and_merge_duplicates` (dry run) | |
| 18 | `delete_note` + `restore_note` | |
| 19 | `vault_status`, `encrypt_note`, `decrypt_note`, encrypted search/add_text behavior | ✅ 2026-07-13 (automated) |
| 20 | `list_resources`/`read_resource` `_meta`, `session_handoff_prompt` | ✅ 2026-07-13 (automated) |
| 21 | Cleanup | ✅ 2026-07-13 (automated) |

Rows 0-18 test pre-existing Bear-parity tools, unchanged by the companion
redesign (Phases 8-10) — not re-verified in this pass; see git history for
when each was last live-tested. Rows 19-21 cover this redesign and were
verified by `simplenote_mcp/scripts/live_test_redesign.py` (35/35 checks
passed) rather than manual Claude Desktop prompts — the prompts above remain
for anyone who wants to confirm the same behavior conversationally.
