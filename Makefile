.PHONY: test test-fast

test:
	SIMPLENOTE_OFFLINE_MODE=true .venv/bin/pytest -q

test-fast:
	SIMPLENOTE_OFFLINE_MODE=true .venv/bin/pytest tests/ -x -q --timeout=30
