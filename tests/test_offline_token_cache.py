"""Regression tests: offline mode must never touch the token file cache.

In SIMPLENOTE_OFFLINE_MODE the client is a MagicMock. _test_simplenote_connection
still acquired and cached a token for it, so cache_token() got a MagicMock
username and token: _cache_path() formatted the mock's repr into a filename,
os.open(O_CREAT) created it, and the write raised TypeError. Every offline
start left a zero-byte "<MagicMock name='mock.username.replace().replace()'
...>.token" in ~/.config/simplenote-mcp/ (12 found on 2026-10-21) and logged
a failed background cache initialization.

The autouse ``isolate_token_file_cache`` fixture (conftest.py) points the
cache directory at this test's ``tmp_path``, so "nothing written" is checked
by listing it.
"""

from unittest.mock import MagicMock, patch

import pytest

from simplenote_mcp.server import keychain
from simplenote_mcp.server.server import (
    OFFLINE_CLIENT_MARKER,
    _build_offline_mock_client,
    _test_simplenote_connection,
)


@pytest.mark.asyncio
async def test_offline_client_skips_token_acquisition(tmp_path, monkeypatch):
    monkeypatch.delenv("SIMPLENOTE_TOKEN", raising=False)
    sn = _build_offline_mock_client()

    with (
        patch.object(keychain, "get_simperium_token") as get_token,
        patch.object(keychain, "cache_token") as cache,
    ):
        await _test_simplenote_connection(sn)

    get_token.assert_not_called()
    cache.assert_not_called()
    sn.authenticate.assert_not_called()
    sn.get_note_list.assert_called_once()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_offline_client_writes_no_cache_file_end_to_end(tmp_path, monkeypatch):
    """The reproduction from 2026-10-21, unpatched: no file, no TypeError."""
    monkeypatch.delenv("SIMPLENOTE_TOKEN", raising=False)

    await _test_simplenote_connection(_build_offline_mock_client())

    assert list(tmp_path.iterdir()) == []


def test_only_the_offline_client_carries_the_marker():
    # Any other MagicMock answers the attribute with a (truthy) mock, which
    # is why the check compares with `is True`.
    assert getattr(_build_offline_mock_client(), OFFLINE_CLIENT_MARKER) is True
    assert getattr(MagicMock(), OFFLINE_CLIENT_MARKER, None) is not True


@pytest.mark.parametrize(
    ("email", "token"),
    [
        (MagicMock(), MagicMock()),
        ("user@example.com", MagicMock()),
        (MagicMock(), "a-token"),
        ("user@example.com", ""),
        ("", "a-token"),
    ],
)
def test_write_file_cache_rejects_non_strings_before_touching_disk(
    tmp_path, email, token
):
    keychain._write_file_cache(email, token)

    assert list(tmp_path.iterdir()) == []


def test_write_file_cache_still_writes_a_real_token(tmp_path):
    keychain._write_file_cache("user@example.com", "a-token")

    assert keychain._read_file_cache("user@example.com") == "a-token"
    assert (tmp_path / "user_at_example.com.token").stat().st_mode & 0o777 == 0o600


def test_get_simperium_token_ignores_a_non_string_email(tmp_path):
    with (
        patch("simplenote_mcp.server.keychain.sys") as mock_sys,
        patch("simplenote_mcp.server.keychain.subprocess.run") as run,
    ):
        mock_sys.platform = "darwin"
        assert keychain.get_simperium_token(MagicMock()) is None

    run.assert_not_called()
    assert list(tmp_path.iterdir()) == []
