#!/bin/bash
# Generate the release changelog via scripts/conventional_changelog.py and
# write its GitHub-Release-safe (%-escaped) form to $GITHUB_OUTPUT as
# `changelog`. Reads NEW_VERSION from the environment.

set -euo pipefail

LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

echo "Generating changelog using conventional commit parser..."

if [ -n "$LAST_TAG" ]; then
  echo "Generating changelog since $LAST_TAG"
  python scripts/conventional_changelog.py --since "$LAST_TAG" --version "$NEW_VERSION" --output changelog.md
else
  echo "No previous tag found, generating changelog from all commits"
  python scripts/conventional_changelog.py --version "$NEW_VERSION" --output changelog.md
fi

echo "Generated changelog:"
cat changelog.md

echo ""
echo "Changelog statistics:"
# shellcheck disable=SC2046  # intentional word-splitting: conditionally adds a 2nd CLI arg
python scripts/conventional_changelog.py \
  $([ -n "$LAST_TAG" ] && echo "--since $LAST_TAG") \
  --format summary

CHANGELOG_CONTENT=$(cat changelog.md)
CHANGELOG_CONTENT="${CHANGELOG_CONTENT//'%'/'%25'}"
CHANGELOG_CONTENT="${CHANGELOG_CONTENT//$'\n'/'%0A'}"
CHANGELOG_CONTENT="${CHANGELOG_CONTENT//$'\r'/'%0D'}"
echo "changelog=$CHANGELOG_CONTENT" >> "$GITHUB_OUTPUT"
