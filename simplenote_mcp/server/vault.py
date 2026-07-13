"""Opt-in client-side encryption for sensitive Simplenote note content ("Vault").

Simplenote has no encryption at rest — Automattic's own documentation confirms
staff can technically read note content, and recommends against storing
sensitive data there (see SECURITY.md). Vault closes that gap for notes
explicitly marked for it: everything after the first line of a note's
content is encrypted locally before it ever reaches the Simplenote API, and
decrypted transiently when read back. The first line (the note's title, per
this project's `extract_title_from_content` convention — Simplenote notes
have no separate title field) stays plaintext, so title-based lookup
(`get_or_create_note`) and browsing keep working for encrypted notes.

Master key: resolved once per process lifetime, then cached in memory only —
never written to disk in plaintext, never re-prompted per operation. Lookup
order:
1. `SIMPLENOTE_VAULT_KEY_FILE` env var — path to a file holding a
   base64-encoded 32-byte key, for headless/container deployments with no
   OS keychain. Generated on first use if the file doesn't exist yet.
2. OS keychain via the `keyring` library (macOS Keychain / Linux Secret
   Service / Windows Credential Locker). Generated and stored on first use.

This is a different, more sensitive secret than the Simperium auth token
(keychain.py) and is deliberately kept in a separate store: the vault key
IS the data — losing it makes encrypted notes permanently unreadable — so
it is never written to the plaintext file cache keychain.py uses for the
lower-stakes, rotatable Simperium session token.
"""

import base64
import binascii
import os
import secrets
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

VAULT_TAG = "vault-encrypted"

_MARKER = "%%SNVAULT:v1%%"
_KEYRING_SERVICE = "simplenote-mcp-vault"
_KEYRING_USERNAME = "vault-master-key"
_KEY_LENGTH_BYTES = 32  # AES-256
_NONCE_LENGTH_BYTES = 12  # 96-bit, standard for AES-GCM

_cached_key: bytes | None = None


class VaultKeyUnavailableError(Exception):
    """Raised when no vault key can be resolved or generated."""


class VaultDecryptionError(Exception):
    """Raised when decryption fails — wrong/missing key, malformed envelope,
    or tampered ciphertext."""


# ---------------------------------------------------------------------------
# Key provisioning
# ---------------------------------------------------------------------------


def _read_key_file(path: str) -> bytes | None:
    try:
        raw = Path(path).read_text().strip()
        return base64.b64decode(raw, validate=True) if raw else None
    except (OSError, binascii.Error, ValueError):
        return None


def _write_key_file(path: str, key: bytes) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(base64.b64encode(key).decode("ascii"))
    os.chmod(p, 0o600)


def _read_keyring_key() -> bytes | None:
    import keyring
    import keyring.errors

    try:
        raw = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
    except keyring.errors.KeyringError:
        return None
    if not raw:
        return None
    try:
        return base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        return None


def _write_keyring_key(key: bytes) -> bool:
    import keyring
    import keyring.errors

    try:
        keyring.set_password(
            _KEYRING_SERVICE,
            _KEYRING_USERNAME,
            base64.b64encode(key).decode("ascii"),
        )
        return True
    except keyring.errors.KeyringError:
        return False


def get_or_create_vault_key() -> bytes:
    """Return the vault master key, generating and persisting one if needed.

    Resolved once per process lifetime and cached in memory — subsequent
    calls never re-read the key file or re-consult the OS keychain, so this
    never re-prompts per encrypt/decrypt operation.

    Raises:
        VaultKeyUnavailableError: no SIMPLENOTE_VAULT_KEY_FILE is set and the
            OS keychain has no backend available to store a new key.
    """
    global _cached_key
    if _cached_key is not None:
        return _cached_key

    key_file = os.environ.get("SIMPLENOTE_VAULT_KEY_FILE")
    if key_file:
        key = _read_key_file(key_file)
        if key is None:
            key = secrets.token_bytes(_KEY_LENGTH_BYTES)
            _write_key_file(key_file, key)
        _cached_key = key
        return key

    key = _read_keyring_key()
    if key is None:
        key = secrets.token_bytes(_KEY_LENGTH_BYTES)
        if not _write_keyring_key(key):
            raise VaultKeyUnavailableError(
                "No vault key is available. Set SIMPLENOTE_VAULT_KEY_FILE to a "
                "writable file path (recommended for Docker/headless deployments), "
                "or ensure an OS keychain / secret-service backend is available "
                "for the `keyring` library to use."
            )
    _cached_key = key
    return key


def has_vault_key() -> bool:
    """Return True if a vault key is available, without generating a new one."""
    if _cached_key is not None:
        return True
    key_file = os.environ.get("SIMPLENOTE_VAULT_KEY_FILE")
    if key_file:
        return _read_key_file(key_file) is not None
    return _read_keyring_key() is not None


def key_provider_name() -> str:
    """Human-readable name of the active key provider, for vault_status()."""
    if os.environ.get("SIMPLENOTE_VAULT_KEY_FILE"):
        return "file"
    return "keyring"


def reset_for_testing() -> None:
    """Clear the in-memory key cache. Test-only."""
    global _cached_key
    _cached_key = None


# ---------------------------------------------------------------------------
# Envelope format: encrypt everything after the first line (title stays
# plaintext), AEAD via AES-256-GCM with a random nonce per encryption.
# ---------------------------------------------------------------------------


def is_encrypted(content: str) -> bool:
    """Return True if content is in the Vault envelope format."""
    lines = content.split("\n", 2)
    return len(lines) >= 2 and lines[1] == _MARKER


def encrypt_content(content: str, key: bytes) -> str:
    """Encrypt everything after the first line of content.

    The first line (title) stays plaintext so title-based lookup and
    browsing keep working for encrypted notes.
    """
    parts = content.split("\n", 1)
    title_line = parts[0]
    body = parts[1] if len(parts) > 1 else ""
    nonce = secrets.token_bytes(_NONCE_LENGTH_BYTES)
    ciphertext = AESGCM(key).encrypt(nonce, body.encode("utf-8"), None)
    blob = base64.b64encode(nonce + ciphertext).decode("ascii")
    return f"{title_line}\n{_MARKER}\n{blob}"


def decrypt_content(content: str, key: bytes) -> str:
    """Decrypt Vault-encrypted content back to its original plaintext.

    Raises:
        VaultDecryptionError: content isn't a valid Vault envelope, or the
            key is wrong / the ciphertext has been tampered with.
    """
    lines = content.split("\n", 2)
    if len(lines) < 2 or lines[1] != _MARKER:
        raise VaultDecryptionError("Content is not Vault-encrypted")

    title_line = lines[0]
    blob = lines[2] if len(lines) > 2 else ""
    try:
        raw = base64.b64decode(blob, validate=True)
    except (binascii.Error, ValueError) as e:
        raise VaultDecryptionError(f"Malformed Vault envelope: {e}") from e

    if len(raw) < _NONCE_LENGTH_BYTES:
        raise VaultDecryptionError("Malformed Vault envelope: ciphertext too short")

    nonce, ciphertext = raw[:_NONCE_LENGTH_BYTES], raw[_NONCE_LENGTH_BYTES:]
    try:
        body = AESGCM(key).decrypt(nonce, ciphertext, None).decode("utf-8")
    except InvalidTag as e:
        raise VaultDecryptionError(
            "Decryption failed — wrong key, or the note has been tampered with"
        ) from e

    return f"{title_line}\n{body}" if body else title_line
