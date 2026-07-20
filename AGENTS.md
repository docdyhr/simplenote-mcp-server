# simplenote-mcp-server

MCP server connecting Simplenote to Claude Desktop and other MCP clients. Python ≥3.10, package root `simplenote_mcp/`.

## Commands

```bash
# Setup
pip install -e ".[dev,test,all]"
pre-commit install

# Tests — two independent trees, run separately (see tests/AGENTS.md and simplenote_mcp/tests/AGENTS.md for why)
make test-fast      # SIMPLENOTE_OFFLINE_MODE=true .venv/bin/pytest tests/ -x -q --timeout=30
make test-legacy    # SIMPLENOTE_OFFLINE_MODE=true .venv/bin/pytest simplenote_mcp/tests/ -q --timeout=30 --no-cov
make test           # both, via .venv/bin/pytest -q (root testpaths = tests/ only; legacy run separately in CI)

# Quality
ruff check .
ruff format .
mypy simplenote_mcp
bandit -c pyproject.toml -r simplenote_mcp   # always pass -c; bare invocation misapplies exclude_dirs

# Evaluations (npm devDependency tree, never shipped — see package.json)
npm install && npm run eval:smoke   # eval:basic, eval:comprehensive, eval:all also available
```

Always invoke `.venv/bin/pytest` / `.venv/bin/ruff` / `.venv/bin/mypy` / `.venv/bin/bandit` explicitly, or prefix with `source .venv/bin/activate &&` in the same shell call — each Bash invocation is a fresh shell, so a prior `activate` does not persist and bare commands silently resolve through the pyenv shim to the global environment instead of `.venv`.

## Architecture

```text
simplenote_mcp/
├── server/            # MCP protocol handlers, tool registry, cache, security — see server/AGENTS.md
│   ├── search/         # Query parser + boolean/fuzzy/date search engine — see server/search/AGENTS.md
│   └── monitoring/      # Metrics collection + alerting thresholds — see server/monitoring/AGENTS.md
├── scripts/            # Runtime diagnostics shipped with the package — see simplenote_mcp/scripts/AGENTS.md
├── tests/               # Legacy pytest tree, separate invocation — see simplenote_mcp/tests/AGENTS.md
└── __main__.py         # Entry point (module execution)
tests/                  # Primary CI-wired pytest tree — see tests/AGENTS.md
scripts/                # CI/quality/release tooling — see scripts/AGENTS.md
helm/                   # Helm chart — see helm/AGENTS.md
.github/workflows/      # CI/CD pipelines — see .github/workflows/AGENTS.md
docs/, evals/           # Reference docs and mcp-evals suites; no durable local contracts of their own
```

### Design patterns

- **Tool Handler Registry**: each tool (`create_note`, `search_notes`, etc.) is a `ToolHandlerBase` subclass registered in `ToolHandlerRegistry` (`server/tool_handlers.py`).
- **Middleware chain**: security validation, input validation, and rate limiting applied via decorators (`server/decorators.py`, `server/middleware.py`) before a handler runs.
- **Background sync**: `NoteCache` (`server/cache.py`) syncs from Simplenote in a background thread so tool calls stay responsive.
- **Error hierarchy**: custom exceptions in `server/errors.py` / `server/error_taxonomy.py` carry MCP-appropriate error codes and user-facing messages.

## Local Contracts

- **Version consistency**: four files must carry the same version — `VERSION`, `pyproject.toml`, `simplenote_mcp/__init__.py`, `helm/simplenote-mcp-server/Chart.yaml` (`appVersion`). `setup.py` also has a version string, now checked as a legacy fallback by `scripts/quality/check_version_consistency.py`. Never bump manually outside the release workflow.
- **Release process is manual, not automatic**: `.github/workflows/release.yml` runs only on `workflow_dispatch` (explicit bump-type input). No workflow triggers a release from a conventional-commit push to `main` — merging a `docs:`/`feat:`/`fix:` PR never cuts a release by itself.
- **Write-mode gate**: any tool that mutates Simplenote data must be added to the `WRITE_TOOLS` frozenset in `server/server.py` or it bypasses the write-mode/write-budget gate — see `server/AGENTS.md`.
- **Bandit config**: `[tool.bandit]` in `pyproject.toml` is authoritative; the separate `.bandit` YAML file disagrees on skipped checks and must not be used. Always run with `-c pyproject.toml`.
- **No credentials, tokens, or Simplenote account data** in any AGENTS.md, doc, script output, or committed fixture, ever.

## Work Guidance

- Read the nearest child `AGENTS.md` for the folder you're editing before making changes; this root file covers only repo-wide rules.
- Extract conventions from existing code — do not invent patterns not already present.
- Update the owning `AGENTS.md` (and any Child DOX Index) whenever you change structure, contracts, or workflow — see the DOX framework block below.

## Verification

- `make test-fast` and `make test-legacy` (both must pass; do not merge into one invocation — see `tests/AGENTS.md`)
- `ruff check . && ruff format --check .`
- `mypy simplenote_mcp`
- `bandit -c pyproject.toml -r simplenote_mcp`
- `python scripts/quality/check_version_consistency.py`

---

## DOX framework

- DOX is highly performant AGENTS.md hierarchy installed here
- Agent must follow DOX instructions across any edits

### Core Contract

- AGENTS.md files are binding work contracts for their subtrees
- Work products, source materials, instructions, records, assets, and durable docs must stay understandable from the nearest applicable AGENTS.md plus every parent AGENTS.md above it

### Read Before Editing

1. Read the root AGENTS.md
2. Identify every file or folder you expect to touch
3. Walk from the repository root to each target path
4. Read every AGENTS.md found along each route
5. If a parent AGENTS.md lists a child AGENTS.md whose scope contains the path, read that child and continue from there
6. Use the nearest AGENTS.md as the local contract and parent docs for repo-wide rules
7. If docs conflict, the closer doc controls local work details, but no child doc may weaken DOX

Do not rely on memory. Re-read the applicable DOX chain in the current session before editing.

### Update After Editing

Every meaningful change requires a DOX pass before the task is done.

Update the closest owning AGENTS.md when a change affects:

- purpose, scope, ownership, or responsibilities
- durable structure, contracts, workflows, or operating rules
- required inputs, outputs, permissions, constraints, side effects, or artifacts
- user preferences about behavior, communication, process, organization, or quality
- AGENTS.md creation, deletion, move, rename, or index contents

Update parent docs when parent-level structure, ownership, workflow, or child index changes. Update child docs when parent changes alter local rules. Remove stale or contradictory text immediately. Small edits that do not change behavior or contracts may leave docs unchanged, but the DOX pass still must happen.

### Hierarchy

- Root AGENTS.md is the DOX rail: project-wide instructions, global preferences, durable workflow rules, and the top-level Child DOX Index
- Child AGENTS.md files own domain-specific instructions and their own Child DOX Index
- Each parent explains what its direct children cover and what stays owned by the parent
- The closer a doc is to the work, the more specific and practical it must be

### Child Doc Shape

- Create a child AGENTS.md when a folder becomes a durable boundary with its own purpose, rules, responsibilities, workflow, materials, or quality standards
- Work Guidance must reflect the current standards of the project or user instructions; if there are no specific standards or instructions yet, leave it empty
- Verification must reflect an existing check; if no verification framework exists yet, leave it empty and update it when one exists

Default section order:

- Purpose
- Ownership
- Local Contracts
- Work Guidance
- Verification
- Child DOX Index

### Style

- Keep docs concise, current, and operational
- Document stable contracts, not diary entries
- Put broad rules in parent docs and concrete details in child docs
- Prefer direct bullets with explicit names
- Do not duplicate rules across many files unless each scope needs a local version
- Delete stale notes instead of explaining history
- Trim obvious statements, repeated rules, misplaced detail, and warnings for risks that no longer exist

### Closeout

1. Re-check changed paths against the DOX chain
2. Update nearest owning docs and any affected parents or children
3. Refresh every affected Child DOX Index
4. Remove stale or contradictory text
5. Run existing verification when relevant
6. Report any docs intentionally left unchanged and why

### User Preferences

- Never bump versions manually; the release workflow (`workflow_dispatch` only) owns version bumps across all four version-source files.
- Never include `[skip ci]` in commits.
- Always run the full test suite (both trees) after source changes; do not mark work done with failing tests.

### Child DOX Index

- `simplenote_mcp/server/AGENTS.md` — core server package: protocol handlers, tool registry, cache, security, credentials, vault encryption
- `simplenote_mcp/server/search/AGENTS.md` — query parser and boolean/fuzzy/date search engine
- `simplenote_mcp/server/monitoring/AGENTS.md` — metrics collection and alerting thresholds
- `simplenote_mcp/scripts/AGENTS.md` — runtime diagnostics scripts shipped inside the package
- `simplenote_mcp/tests/AGENTS.md` — legacy pytest tree (112 tests, separate invocation)
- `tests/AGENTS.md` — primary CI-wired pytest tree
- `scripts/AGENTS.md` — CI/quality/release tooling (not shipped)
- `helm/AGENTS.md` — Helm chart for Kubernetes deployment
- `.github/workflows/AGENTS.md` — CI/CD pipeline definitions
