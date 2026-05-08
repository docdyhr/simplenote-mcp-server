.PHONY: test test-fast

test:
	SIMPLENOTE_OFFLINE_MODE=true pytest -q

test-fast:
	SIMPLENOTE_OFFLINE_MODE=true pytest tests/ -x -q --timeout=30
