# simplenote_mcp/server/monitoring/

## Purpose

Performance metrics collection (`metrics.py`) and alerting thresholds (`thresholds.py`) — API call rates, cache hit/miss, tool usage, system resources. See `README.md` in this folder for end-user dashboard/usage docs; this file covers agent-relevant contracts only.

## Ownership

- `metrics.py` — `MetricsCollector` (process-global singleton via `__new__`/`_instance`), `PerformanceMetrics`/`ApiMetrics`/`CacheMetrics`/`ResourceMetrics`/`ToolMetrics` containers, `record_*`/`get_metrics` functions.
- `thresholds.py` — alert threshold definitions consumed by `server/alerting.py`.

## Local Contracts

- **`MetricsCollector` is a process-global singleton** — it cannot be reset by reassigning `_instance`; the only way to reset it between tests is replacing its `.metrics` attribute (see `_reset_process_global_singletons` in `simplenote_mcp/tests/conftest.py`). This is the root cause of why `tests/` and `simplenote_mcp/tests/` must run as separate pytest processes: each tree's autouse conftest fixture only resets state for its own tests, so collecting both trees into one pytest invocation lets one tree's leftover singleton state corrupt the other's assertions. Do not attempt to merge the two trees into one `testpaths` list without solving this isolation problem first.
- Metrics persist to `simplenote_mcp/logs/metrics/performance_metrics.json`, path overridable via `METRICS_FILE_PATH`. Collection interval via `METRICS_COLLECTION_INTERVAL` (default 60s).

## Work Guidance

- New metric types: add to `metrics.py`, update `simplenote_mcp/scripts/monitoring_dashboard.py` if dashboard-visible, add tests, update `README.md`'s API reference table.

## Verification

- `make test-fast` (`tests/test_performance_monitoring.py` is 100% stable only when run in isolation from `simplenote_mcp/tests/` — see Local Contracts)

## Child DOX Index

None.
