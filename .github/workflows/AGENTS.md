# .github/workflows/

## Purpose

CI/CD pipeline definitions. `unified-ci.yml` is the main pipeline (validate → test → security → status jobs); `release.yml` is manual-dispatch-only (see root `AGENTS.md`); others handle Dependabot automation, security scanning, docs, and evaluations.

## Ownership

- `unified-ci.yml` — `validate` (version consistency, lint), `test`, `security`, `local-test`, `status` jobs; blocks on version consistency before test/build/security run.
- `security.yml`, `dependency-review.yml` — Bandit/pip-audit/CodeQL-style scanning.
- `auto-fix.yml`, `auto-merge.yml`, `claude-dependabot-merge.yml`, `claude-status-check.yml` — Dependabot/PR automation.
- `evaluation-quality-gate.yml`, `mcp-evaluations.yml` — mcp-evals suite runners; both gate on `ANTHROPIC_API_KEY` presence so Dependabot PRs (no repo secret access) skip gracefully instead of failing.
- `release.yml` — manual `workflow_dispatch` version bump/release (patch/minor/major). `update-version.yml` — triggers on `v*.*.*` tag push, syncs version references post-release.
- `docs.yml` — thin caller (docs build via `reusable-docs-build.yml`, Pages deploy via `reusable-docs-deploy.yml`, link check via `reusable-docs-link-check.yml`). `monitoring-consolidated.yml`, `publish-pypi.yml` — consolidated monitoring checks, PyPI publish.
- `reusable-*.yml` — local `workflow_call` reusable workflows, each owned by and used only by the caller(s) listed against it above. Not standalone triggers; see the owning caller for `on:` semantics. Introduced 2026-08-12 as part of a phased thin-caller refactor (org-standard ≤80-line-per-file check) — the docdyhr org's usual pattern delegates to the separate `docdyhr/.github` repo (see `security.yml`/`claude-status-check.yml`/`claude-dependabot-merge.yml` below), but these use local composition instead by deliberate choice (no cross-repo versioning/tagging overhead for logic specific to this repo).

## Local Contracts

- **`yaml.safe_load()` is not sufficient to validate `uses:` lines.** A YAML-valid-but-schema-invalid `uses:` value (e.g. a bare SHA with the tag comment misplaced, instead of `owner/repo@<sha> # tag`) parses cleanly but makes GitHub run **zero jobs** for every workflow referencing it. Only a schema-aware linter (`actionlint`) catches this class of bug — not currently run in CI. Run `actionlint` on any `.github/workflows/*.yml` edit before considering it done, especially SHA-pinning changes.
- **`github-script` steps must pass untrusted values via `env:`**, never interpolate `${{ needs.*.outputs.* }}` / `${{ github.event.inputs.* }}` / `${{ steps.*.outputs.* }}` directly into the `script:` body — an injected value could break out of the JS string literal (script-injection). Read via `process.env.*` instead; see the existing pattern and comment in `auto-fix.yml`.
- `dependabot.yml` (one directory up, at `.github/dependabot.yml`) covers four ecosystems: `pip`, `npm`, `docker`, `github-actions` — keep all four current when adding a new dependency manager to the project.
- **`auto-merge.yml`'s `dependabot-auto-merge` job auto-approves and merges patch/minor Dependabot PRs, but skips any PR touching a security-sensitive package** (`cryptography`, `requests`, `urllib3`, `aiohttp` — matched via `contains()` against `dependency-names`, so those PRs always fall through to manual review regardless of update type). Add to that list when a new security-sensitive dependency is introduced. Note: this repo's `main` branch currently has no `required_status_checks` configured in branch protection, so this workflow's own `gh pr checks`/`FAILED` polling is the only gate before merge — it is not backed by a GitHub-enforced required-checks list.

## Verification

- `actionlint` on any changed workflow file (manual — not yet wired into CI itself)
- Push/PR and watch the `validate` job in `unified-ci.yml` actually queues and runs

## Child DOX Index

None.
