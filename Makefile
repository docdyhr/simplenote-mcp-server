.PHONY: test test-fast test-legacy

test:
	SIMPLENOTE_OFFLINE_MODE=true .venv/bin/pytest -q

test-fast:
	SIMPLENOTE_OFFLINE_MODE=true .venv/bin/pytest tests/ -x -q --timeout=30

# simplenote_mcp/tests/ — kept as a separate pytest process deliberately:
# both trees exercise process-global singletons (metrics collector,
# security validator), and each resets them only for its own tests, so
# merging them into one pytest invocation lets one tree corrupt the
# other's state. See unified-ci.yml's "Run legacy test suite" step.
test-legacy:
	SIMPLENOTE_OFFLINE_MODE=true .venv/bin/pytest simplenote_mcp/tests/ -q --timeout=30 --no-cov
