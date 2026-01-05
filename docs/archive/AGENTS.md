# Repository Guidelines

## Project Structure & Module Organization
- Core server logic lives in `simplenote_mcp/server`, split into auth, caching, monitoring, and search modules; keep new protocol handlers under `tool_handlers.py` or `server/compat` when targeting specific MCP clients.
- Shared utilities reside in `simplenote_mcp/server/utils` and `simplenote_mcp/scripts` hosts operational helpers; reuse before adding new helpers.
- Top-level `tests/` covers integration scenarios, while `simplenote_mcp/tests/` mirrors package internals; place fixtures in `tests/conftest.py`.
- Docker and deployment assets are in `docker-compose.*`, `Dockerfile*`, and `helm/`; docs and guides belong in `docs/`.

## Build, Test, and Development Commands
- Install with `pip install -e .[dev]` to pull Ruff, Black, Mypy, and the test stack.
- Run `pytest` for the full suite, or `pytest -m unit` for fast checks; append `--cov=simplenote_mcp --cov-report=term-missing` when updating coverage.
- Enforce style with `ruff check .` and auto-format with `ruff format`; run `mypy simplenote_mcp` before PRs.
- Use `docker-compose -f docker-compose.dev.yml up` for a live-reload server, or `simplenote-mcp-server` after setting environment variables for a local CLI run.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation and 88-character lines; prefer dataclasses and type hints for new structures.
- Keep module-level constants UPPER_SNAKE_CASE, async handlers in lower_snake_case, and classes in CapWords.
- Ruff enforces lint rules; if a rule must be skipped, document the rationale above the pragma. Prefer `ruff format` over direct Black calls unless formatting diverges.

## Testing Guidelines
- Prefer unit tests under `simplenote_mcp/tests` with filenames like `test_<feature>.py`; use markers (`@pytest.mark.unit`, `@pytest.mark.integration`) defined in `pytest.ini`.
- Mock Simplenote I/O; integration tests may exercise the live API only when guarded by the `network` marker.
- Keep coverage steady or rising; add regression tests for every bugfix touching server endpoints or cache behavior.

## Commit & Pull Request Guidelines
- Follow Conventional Commits (`feat(scope):`, `fix(server):`, `chore(deps):`); group breaking changes behind `!` when required.
- Squash noisy commits locally; ensure PRs include a short summary, test evidence (`pytest` output or coverage delta), and linked issues using GitHub keywords.
- Update relevant docs (`README.md`, `docs/`, or Helm values) when altering defaults, CLI flags, or environment variables.

## Security & Configuration Tips
- Never commit Simplenote credentials; rely on environment variables `SIMPLENOTE_EMAIL` and `SIMPLENOTE_PASSWORD` or your secrets manager.
- Run `bandit -c pyproject.toml -r simplenote_mcp` and `pip-audit` when modifying dependencies or auth flows.
- Monitor the optional HTTP endpoints (`/health`, `/ready`, `/metrics`) in staging to catch regressions introduced by new agents.
