#!/bin/bash
# Compute and (unless DRY_RUN=true) apply a semver bump across all
# version-source files (pyproject.toml, simplenote_mcp/__init__.py, VERSION,
# helm Chart.yaml, setup.py). Reads CURRENT_VERSION, BUMP_TYPE, PRE_RELEASE,
# DRY_RUN from the environment; writes new_version to $GITHUB_OUTPUT.

set -euo pipefail

# Validate bump_type against the known enum, even though the input is a
# `type: choice` field — defense in depth in case workflow_dispatch is ever
# triggered via the API with an unvalidated value.
case "$BUMP_TYPE" in
  patch|minor|major) ;;
  *)
    echo "::error::Invalid bump_type: $BUMP_TYPE" >&2
    exit 1
    ;;
esac

# Validate pre_release is a safe semver prerelease identifier before it ever
# reaches a shell-interpolated python -c invocation.
if [ -n "$PRE_RELEASE" ] && ! printf '%s' "$PRE_RELEASE" | grep -qE '^[a-zA-Z0-9.-]+$'; then
  echo "::error::Invalid pre_release label: $PRE_RELEASE" >&2
  exit 1
fi

echo "Bumping $BUMP_TYPE version from $CURRENT_VERSION"

if [ -n "$PRE_RELEASE" ]; then
  NEW_VERSION=$(python -c "import semver; print(str(semver.VersionInfo.parse('$CURRENT_VERSION').bump_$BUMP_TYPE().replace(prerelease='$PRE_RELEASE')))")
else
  NEW_VERSION=$(python -c "import semver; print(str(semver.VersionInfo.parse('$CURRENT_VERSION').bump_$BUMP_TYPE()))")
fi

# Validate the computed version before it's used in any further
# shell-interpolated step (git commit/tag/push, changelog generation).
if ! printf '%s' "$NEW_VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$'; then
  echo "::error::Computed version failed validation: $NEW_VERSION" >&2
  exit 1
fi

echo "New version: $NEW_VERSION"
echo "new_version=$NEW_VERSION" >> "$GITHUB_OUTPUT"

if [ "$DRY_RUN" != "true" ]; then
  python -c "
import toml, pathlib
data = toml.load('pyproject.toml')
data['project']['version'] = '$NEW_VERSION'
path = pathlib.Path('pyproject.toml')
path.write_text(toml.dumps(data))
"

  if [ -f "simplenote_mcp/__init__.py" ]; then
    sed -i "s/__version__ = \".*\"/__version__ = \"$NEW_VERSION\"/g" simplenote_mcp/__init__.py
  fi

  if [ -f "VERSION" ]; then
    echo "$NEW_VERSION" > VERSION
  fi

  if [ -f "helm/simplenote-mcp-server/Chart.yaml" ]; then
    sed -i "s/^version: .*/version: $NEW_VERSION/" helm/simplenote-mcp-server/Chart.yaml
    sed -i "s/^appVersion: .*/appVersion: \"$NEW_VERSION\"/" helm/simplenote-mcp-server/Chart.yaml
  fi

  if [ -f "setup.py" ]; then
    sed -i "s/version=\".*\"/version=\"$NEW_VERSION\"/" setup.py
  fi
fi
