"""Tests for simplenote_mcp.server.vault — opt-in client-side note encryption."""

import base64
import os
from unittest.mock import patch

import pytest

from simplenote_mcp.server import vault


@pytest.fixture(autouse=True)
def _reset_vault_state():
    """Every test starts with a clean in-memory key cache and no env override."""
    vault.reset_for_testing()
    old_env = os.environ.pop("SIMPLENOTE_VAULT_KEY_FILE", None)
    yield
    vault.reset_for_testing()
    if old_env is not None:
        os.environ["SIMPLENOTE_VAULT_KEY_FILE"] = old_env
    else:
        os.environ.pop("SIMPLENOTE_VAULT_KEY_FILE", None)


@pytest.fixture
def key():
    return os.urandom(32)


@pytest.mark.unit
class TestEnvelopeRoundTrip:
    """encrypt_content/decrypt_content are pure functions over a raw key —
    tested independently of key provisioning."""

    def test_round_trip_preserves_content(self, key):
        original = "My Project\nSensitive line one\nSensitive line two"
        encrypted = vault.encrypt_content(original, key)
        assert vault.decrypt_content(encrypted, key) == original

    def test_round_trip_single_line_note(self, key):
        original = "Just a title, no body"
        encrypted = vault.encrypt_content(original, key)
        assert vault.decrypt_content(encrypted, key) == original

    def test_round_trip_empty_content(self, key):
        encrypted = vault.encrypt_content("", key)
        assert vault.decrypt_content(encrypted, key) == ""

    def test_title_line_stays_plaintext(self, key):
        original = "Readable Title\nSecret body content"
        encrypted = vault.encrypt_content(original, key)
        assert encrypted.startswith("Readable Title\n")
        assert "Secret body content" not in encrypted

    def test_is_encrypted_true_for_encrypted_content(self, key):
        encrypted = vault.encrypt_content("Title\nbody", key)
        assert vault.is_encrypted(encrypted) is True

    def test_is_encrypted_false_for_plain_content(self):
        assert vault.is_encrypted("Just a normal note\nwith some lines") is False

    def test_is_encrypted_false_for_empty_content(self):
        assert vault.is_encrypted("") is False

    def test_is_encrypted_false_for_single_line_content(self):
        assert vault.is_encrypted("No newline at all") is False

    def test_nonce_is_unique_per_encryption(self, key):
        a = vault.encrypt_content("Title\nsame body", key)
        b = vault.encrypt_content("Title\nsame body", key)
        assert a != b


@pytest.mark.unit
class TestTamperDetection:
    def test_wrong_key_raises_decryption_error(self, key):
        encrypted = vault.encrypt_content("Title\nsecret", key)
        wrong_key = os.urandom(32)
        with pytest.raises(vault.VaultDecryptionError):
            vault.decrypt_content(encrypted, wrong_key)

    def test_flipped_ciphertext_byte_raises_not_garbage(self, key):
        """A single flipped bit must raise, never silently return corrupted plaintext."""
        encrypted = vault.encrypt_content("Title\nsecret content here", key)
        lines = encrypted.split("\n")
        raw = bytearray(base64.b64decode(lines[2]))
        raw[-1] ^= 0xFF  # flip a bit in the auth tag
        lines[2] = base64.b64encode(bytes(raw)).decode("ascii")
        tampered = "\n".join(lines)
        with pytest.raises(vault.VaultDecryptionError):
            vault.decrypt_content(tampered, key)

    def test_malformed_base64_raises_decryption_error(self, key):
        tampered = "Title\n%%SNVAULT:v1%%\nnot-valid-base64!!!"
        with pytest.raises(vault.VaultDecryptionError):
            vault.decrypt_content(tampered, key)

    def test_decrypting_plain_content_raises(self, key):
        with pytest.raises(vault.VaultDecryptionError):
            vault.decrypt_content("Just a normal note, never encrypted", key)

    def test_truncated_ciphertext_raises(self, key):
        tampered = "Title\n%%SNVAULT:v1%%\n" + base64.b64encode(b"short").decode()
        with pytest.raises(vault.VaultDecryptionError):
            vault.decrypt_content(tampered, key)


@pytest.mark.unit
class TestKeyProvisioning:
    def test_key_file_creates_new_key_if_missing(self, tmp_path):
        key_file = tmp_path / "vault.key"
        with patch.dict(os.environ, {"SIMPLENOTE_VAULT_KEY_FILE": str(key_file)}):
            resolved = vault.get_or_create_vault_key()
        assert len(resolved) == 32
        assert key_file.exists()
        assert oct(key_file.stat().st_mode)[-3:] == "600"

    def test_key_file_created_with_no_permissive_window(self, tmp_path):
        """Regression test: the key file must never exist with default (often
        world-readable) permissions, even momentarily. A write-then-chmod
        pattern has a race window between creation and restriction; the file
        must be created with 0600 atomically via os.open's mode argument.
        """
        key_file = tmp_path / "vault.key"
        original_open = os.open
        observed_modes = []

        def spying_open(path, flags, mode=0o777):
            observed_modes.append(mode)
            return original_open(path, flags, mode)

        with (
            patch.dict(os.environ, {"SIMPLENOTE_VAULT_KEY_FILE": str(key_file)}),
            patch("os.open", side_effect=spying_open),
        ):
            vault.get_or_create_vault_key()

        assert observed_modes, "os.open was not called to create the key file"
        assert all(mode == 0o600 for mode in observed_modes), (
            f"key file was opened with a non-restrictive mode: {observed_modes}"
        )

    def test_key_file_reuses_existing_key_across_process_restarts(self, tmp_path):
        key_file = tmp_path / "vault.key"
        with patch.dict(os.environ, {"SIMPLENOTE_VAULT_KEY_FILE": str(key_file)}):
            first = vault.get_or_create_vault_key()
            vault.reset_for_testing()  # simulate a fresh process
            second = vault.get_or_create_vault_key()
        assert first == second

    def test_key_cached_in_memory_after_first_resolution(self, tmp_path):
        """The key file must not be re-read on every call within one process."""
        key_file = tmp_path / "vault.key"
        with patch.dict(os.environ, {"SIMPLENOTE_VAULT_KEY_FILE": str(key_file)}):
            first = vault.get_or_create_vault_key()
            key_file.write_text("corrupted-should-not-be-read-again")
            second = vault.get_or_create_vault_key()
        assert first == second

    def test_keyring_used_when_no_key_file_env_set(self):
        stored: dict[tuple[str, str], str] = {}

        def fake_set_password(service, username, password):
            stored[(service, username)] = password

        def fake_get_password(service, username):
            return stored.get((service, username))

        with (
            patch("keyring.get_password", side_effect=fake_get_password),
            patch("keyring.set_password", side_effect=fake_set_password),
        ):
            first = vault.get_or_create_vault_key()
            vault.reset_for_testing()
            second = vault.get_or_create_vault_key()
        assert first == second
        assert len(first) == 32

    def test_has_vault_key_false_when_nothing_provisioned(self):
        with patch("keyring.get_password", return_value=None):
            assert vault.has_vault_key() is False

    def test_has_vault_key_true_after_provisioning(self):
        with (
            patch("keyring.get_password", return_value=None),
            patch("keyring.set_password"),
        ):
            vault.get_or_create_vault_key()
        assert vault.has_vault_key() is True

    def test_has_vault_key_true_when_key_file_exists(self, tmp_path):
        key_file = tmp_path / "vault.key"
        with patch.dict(os.environ, {"SIMPLENOTE_VAULT_KEY_FILE": str(key_file)}):
            vault.get_or_create_vault_key()
            vault.reset_for_testing()
            assert vault.has_vault_key() is True

    def test_key_provider_name_file_when_env_set(self, tmp_path):
        key_file = tmp_path / "vault.key"
        with patch.dict(os.environ, {"SIMPLENOTE_VAULT_KEY_FILE": str(key_file)}):
            assert vault.key_provider_name() == "file"

    def test_key_provider_name_keyring_by_default(self):
        assert vault.key_provider_name() == "keyring"

    def test_keyring_unavailable_raises_clear_error(self):
        import keyring.errors

        with (
            patch(
                "keyring.get_password",
                side_effect=keyring.errors.NoKeyringError("no backend"),
            ),
            patch(
                "keyring.set_password",
                side_effect=keyring.errors.NoKeyringError("no backend"),
            ),
            pytest.raises(vault.VaultKeyUnavailableError),
        ):
            vault.get_or_create_vault_key()
