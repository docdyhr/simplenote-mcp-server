# Vault — Opt-In Client-Side Note Encryption

Design reference for `simplenote_mcp/server/vault.py`. See [SECURITY.md](../../SECURITY.md) for the user-facing summary and [ROADMAP.md](../../ROADMAP.md#phase-9--vault-opt-in-client-side-encryption) for the roadmap context.

## Why

Simplenote has no encryption at rest. Automattic's own documentation confirms notes are stored as plaintext on their servers, staff can technically read note content, and recommends against storing sensitive information in Simplenote. As Simplenote MCP becomes a working-memory layer for Claude, that gap matters more: Claude will write increasingly operational detail into it — credentials mentioned in passing, financial figures, personal reflections, debugging output that happens to contain secrets.

Vault closes that gap for notes explicitly marked for it, without changing anything about the notes that aren't.

## Design principle: opt-in, not a re-architecture

Most notes stay exactly as they are today — plaintext, fully indexed, fully searchable. A note becomes encrypted only when a caller explicitly asks for it (`encrypt=true`, or `encrypt_note`). This keeps the blast radius small: the search engine, the cache, and every other tool continue to work unmodified for the 99% of notes that were never sensitive to begin with.

## Trust boundary

The MCP server process already sees plaintext note content and holds Simplenote credentials — that boundary is unchanged by Vault. What Vault closes is the gap *between* "local process" and "Simplenote's cloud," which today has zero protection. Plaintext exists only in local process memory during a request; it is never persisted decrypted, never logged, and never sent anywhere except back to the caller (Claude) who asked for it.

## Envelope format

Simplenote notes have no separate title field — the title is always the first line of content (see `extract_title_from_content`). Vault preserves that: **only the content after the first line is encrypted.** The title stays plaintext so `get_or_create_note`, browsing, and title-based search keep working on encrypted notes.

```
<title line — unchanged plaintext>
%%SNVAULT:v1%%
<base64(nonce || ciphertext_with_tag)>
```

- AEAD cipher: AES-256-GCM (`cryptography.hazmat.primitives.ciphers.aead.AESGCM`). No hand-rolled crypto — high-level, misuse-resistant recipes only.
- Nonce: 12 random bytes (`secrets.token_bytes`), unique per encryption. Never reused with the same key.
- The `%%SNVAULT:v1%%` marker makes an encrypted note unambiguous to `list_tags`, to a human opening the note in the native Simplenote app, and to this server's own `vault.is_encrypted()` check — versioned so a future envelope change can coexist with v1 notes during migration.
- A reserved tag, `vault-encrypted` (`vault.VAULT_TAG`), is added alongside the marker so tag-based filtering, `vault_status`'s count, and the cache's indexing logic can all recognize encrypted notes without parsing content.

## Key management

The one piece of this design with real UX risk — designed to avoid a mistake this project already made once. `keychain.py`'s Simperium-token cache previously used the real macOS Keychain, then moved to a plaintext file cache specifically because the Keychain triggered a repeated OS-approval dialog. Vault's key is read far more often than the auth token (every encrypted-note read or write, not just once at startup), so repeating that mistake would be worse.

**Resolution order** (`vault.get_or_create_vault_key()`):
1. `SIMPLENOTE_VAULT_KEY_FILE` env var — path to a file holding a base64-encoded 32-byte key. Generated on first use if the file doesn't exist. This is the container/headless-deployment path: no OS keychain is available inside most containers.
2. OS keychain via the `keyring` library (macOS Keychain, Linux Secret Service, Windows Credential Locker). Generated and stored on first use if none exists.

**Caching**: resolved once per process lifetime, then cached in memory (`vault._cached_key`) for the rest of the process's life. This means at most one OS-keychain prompt per server start, not one per operation — matching the low-friction UX the file-cache token approach already established, but without ever writing the *key itself* to plaintext disk (unlike the token, the key is not rotatable-and-low-stakes; losing control of it defeats the entire feature).

**Read-path behavior is deliberately different from write-path**: `get_or_create_vault_key()` (used when a caller explicitly opts into encryption) will generate a new key if none exists. But `_decrypt_for_read()` (used by `get_note`/`search_notes`/`list_notes`) checks `has_vault_key()` first and *never* generates a key as a side effect of a read — calling `get_note` on a note encrypted on a different machine must not silently provision an unrelated new key on this one.

## What's NOT built (documented limitations, not gaps)

- **No decrypted shadow search index.** Vault-note bodies are excluded from the word/title index (only the plaintext title line is indexed) and from the search engine's candidate set (`NoteCache.search_notes()` substitutes title-only content into the snapshot handed to `SearchEngine`, and the API-fallback path does the same). Full-text search into vault contents doesn't work in this version. The alternative — a memory-only decrypted shadow index, rebuilt each session — is a bounded future option if this tradeoff turns out to matter in practice; it wasn't built now to keep the design's blast radius small and to avoid ever holding decrypted content anywhere beyond a single request's response construction.
- **No multi-device key sync.** An encrypted note is only decryptable on a machine holding the matching key. There's no export/import flow yet; moving between machines is a manual, out-of-band key transfer the user does themselves (never through Simplenote).
- **No "paranoid" full-note encryption.** The title always stays plaintext. A mode that also encrypts the title (with a placeholder shown instead) is a documented future option, not implemented.

## Safety guards against silent corruption

Tools that read-modify-write note content blindly (`add_text`, `replace_section`) would corrupt the envelope if applied to Vault ciphertext — there's no way to cleanly "append" to an AEAD ciphertext blob. `update_note` without `encrypt=true` would silently overwrite encrypted content with plaintext, quietly undoing the protection. All three refuse with a structured `vault_encrypted_note` error (`ToolHandlerBase._guard_against_blind_mutation`) rather than doing either. `find_and_merge_duplicates` excludes Vault-encrypted notes from its comparison set entirely, since comparing ciphertext can never find a real duplicate and a false-positive match risks merging encrypted content into a plaintext note.

## Error handling

Decryption failures (wrong key, tampered/corrupted ciphertext) raise `vault.VaultDecryptionError`, translated at the tool-handler layer into a `SecurityError` with `subcategory="decryption_failed"` — reusing the existing `error_taxonomy.py`/`ServerError` structured-error infrastructure rather than a parallel scheme. Key-provisioning failures (no keychain backend, no writable key file) raise `vault.VaultKeyUnavailableError`, translated into a `ConfigurationError` with `subcategory="vault_key_unavailable"`. Neither ever logs plaintext content or key material, and neither ever includes decrypted content in an exception message.

## Dependencies

`cryptography` and `keyring` are direct runtime dependencies (`pyproject.toml`). Both were already present in `requirements-lock.txt` as transitive dependencies of dev/publish tooling (`pip-audit`, `twine`) before this feature, so no unfamiliar new package was introduced — they were promoted from transitive to direct and are now actually imported by server code.
