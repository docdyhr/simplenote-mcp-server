# helm/

## Purpose

Helm chart for deploying `simplenote-mcp-server` to Kubernetes (`helm/simplenote-mcp-server/`).

## Ownership

- `Chart.yaml` — chart metadata; `version` and `appVersion` must track the project version (see Local Contracts).
- `values.yaml` — defaults (replica count, image repo/tag, security context, resources).
- `templates/` — `deployment.yaml`, `service.yaml`, `serviceaccount.yaml`, `configmap.yaml`, `secret.yaml` (renders `SIMPLENOTE_PASSWORD` from `.Values.simplenote.password`, base64-encoded — never hardcode a real password in `values.yaml`), `hpa.yaml`, `_helpers.tpl`.

## Local Contracts

- `Chart.yaml`'s `appVersion` is one of the four files checked by `scripts/quality/check_version_consistency.py` (alongside `VERSION`, `pyproject.toml`, `simplenote_mcp/__init__.py`) — keep it in sync; never bump manually outside the release workflow.
- `values.yaml`'s `image.tag` is **not** covered by `check_version_consistency.py` or `scripts/validate-helm.py` (the latter only checks `values.yaml` for security settings) — it can silently drift behind `Chart.yaml`'s `appVersion`. Check it manually when bumping versions.
- No real credentials in `values.yaml` or any committed values file — `secret.yaml` expects `.Values.simplenote.password` to be supplied at install time (`--set` or a separate, untracked values file).

## Verification

- `python scripts/validate-helm.py`
- `helm lint helm/simplenote-mcp-server`

## Child DOX Index

None.
