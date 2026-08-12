# Disabled tests

`test_server_comprehensive.py.disabled` and `test_server_integration.py.disabled`
were written against an older `server.py` API surface and predate the mcp
Python SDK v2 migration (PR #785, 2026-08-10) and several other server
refactors. They are not collected by pytest (the `.disabled` suffix means
neither `test_*.py` glob matches), so they've been dead weight — kept here
rather than in the main `tests/` tree so they don't get mistaken for live
coverage, and so their fake credential fixtures (`SIMPLENOTE_PASSWORD:
"testpass"` etc. — not real secrets, just test fixture placeholders) don't
sit in the primary test tree scanned by CI secret-scanning tooling.

Before re-enabling either file: verify its mocks and assertions still match
current `server.py` behavior (imports resolve as of 2026-08-11, but that
doesn't mean the test bodies are still correct) and move it back to `tests/`
with the `.disabled` suffix dropped.
