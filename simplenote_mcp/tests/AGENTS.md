# simplenote_mcp/tests/

## Purpose

Legacy pytest tree (15 test files) — restored to CI but deliberately kept as a **separate pytest invocation** from `tests/` (the primary, CI-wired tree; new tests always go there — see `tests/AGENTS.md`). Not listed in `pyproject.toml`'s `testpaths`.

## Ownership

- `test_*.py` — legacy coverage for compat shims, note operations/organization, error categorization, performance monitoring/thresholds, search, server capabilities, structured logging, tag filtering, MCP client behavior.
- `conftest.py` — `_reset_process_global_singletons` (autouse) resets `MetricsCollector`/security-validator state for *this tree only* (see Local Contracts).
- `benchmark_cache.py`, `monitor_server.py`, `pagination_and_cache_diagnostic.py` — manual/live-account scripts, not pytest tests (see Local Contracts).
- `run_tests.py` — legacy category-based test runner predating the Makefile targets.
- `unit/` — subdirectory, currently empty.

## Local Contracts

- **Never merge this tree into `tests/`'s `testpaths`.** Both trees mutate the same process-global singletons (`MetricsCollector` in `server/monitoring/metrics.py`, security-validator attempt-tracking) and each tree's autouse conftest fixture resets state only for its own tests. Collecting both into one pytest process lets one tree's leftover state corrupt the other's assertions — confirmed empirically against `test_performance_monitoring.py`.
- **`pagination_and_cache_diagnostic.py` is not a pytest test module** despite living in this directory — its functions take a `cache: NoteCache` parameter with no matching fixture and require a real Simplenote account. It was previously named `test_pagination_and_cache.py`, which caused pytest to silently either error or vacuously "pass" (unawaited coroutine) without ever running. Do not rename it back to a `test_*` pattern.
- Run with `SIMPLENOTE_OFFLINE_MODE=true`, `--no-cov` (excluded from the coverage gate that governs `tests/`).

## Work Guidance

- Treat this tree as maintenance-only — fix breakage here, but add new coverage to `tests/` instead.

## Verification

- `make test-legacy` — `SIMPLENOTE_OFFLINE_MODE=true .venv/bin/pytest simplenote_mcp/tests/ -q --timeout=30 --no-cov`

## Child DOX Index

None.
