# scripts/

## Purpose

CI, quality-gate, and release tooling — not shipped in the package or Docker image (devDependency-equivalent for Python: dev-only, invoked by CI workflows, Makefile, and pre-commit, never imported by `simplenote_mcp/`).

## Ownership

- `quality/` — CI "Validate" job checks: `check_version_consistency.py` (VERSION/pyproject.toml/`simplenote_mcp/__init__.py`/Chart.yaml/setup.py must match), `check_coverage.py`, `check_complexity.py` (Radon), `archive_old_docs.py`.
- `run-quality-checks.py`, `run-comprehensive-tests.py`, `test-categories.py` — local aggregate quality/test runners (mirror CI locally).
- `validate-*.py` (workflows, badges, CI/CD health/pipeline, Helm, version-pinning, offline) — CI/config validators, mostly read-only.
- `conventional_changelog.py` — parses conventional-commit history into changelog sections; used by `release.yml`.
- `release/` — `release.yml`'s steps: `bump_version.sh` (bumps the five version-source files), `set_pyproject_version.py` (its pyproject.toml edit: rewrites only the `[project]` version line, because a `toml` load/dump round-trip drops comments), `generate_release_changelog.sh`, `tag_release_commit.sh` (tags the release PR's merge commit after checking it is on `origin/main` and its `VERSION` matches), `delete_merged_release_branch.sh` (deletes `release/vX.Y.Z` once its PR merged, only if the branch tip is that PR's head and no open PR uses it; run last and `continue-on-error` by `release.yml` and `release-finish.yml`), and `sync_version_references.sh` (`update-version.yml`).
- `generate_release_security_reports.py` — the release's SBOM and vulnerability reports, describing the environment of `--python` (the release build passes a clean venv holding only the built wheel). A failed scan exits non-zero; it never writes a "no vulnerabilities" report.
- `manage-prs.py`, `resolve-prs-offline.py`, `check-workflow-status.py`, `verify-github-status.py` — GitHub API tooling for solo-maintainer PR/workflow triage; `--merge`/`--close` operations are destructive (merge/close real PRs) and require explicit invocation, never run unattended.
- `update-dockerhub-readme.py`/`.sh` — pushes repository description to Docker Hub via `DOCKER_USERNAME`/`DOCKER_TOKEN`; external side effect, requires credentials.
- `add-timeouts-to-workflows.py` — one-off workflow-mutation helper; review its diff before trusting output on new workflows.
- `claude-code-support/` — Claude Code hook/assistant scripts (`auto-test.sh` etc.), not part of the CI pipeline.

## Local Contracts

- Scripts here are **dev/CI-only** — never import from this directory in `simplenote_mcp/`, and never bundle it into the Docker image or PyPI package.
- `manage-prs.py --merge`/`--close` and any Docker Hub push script have real external side effects (merges/closes GitHub PRs, updates a public Docker Hub listing) — confirm with the user before running, same as any other hard-to-reverse action.

## Verification

- `python scripts/quality/check_version_consistency.py`
- `python scripts/run-quality-checks.py`

## Child DOX Index

None — `quality/` is a thin sub-boundary covered above, not large enough for its own doc.
