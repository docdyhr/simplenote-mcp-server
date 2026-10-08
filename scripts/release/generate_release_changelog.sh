#!/bin/bash
# Generate the release changelog via scripts/conventional_changelog.py and
# write it to $GITHUB_OUTPUT as the multiline output `changelog`. Reads
# NEW_VERSION from the environment.

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

# Multiline outputs need the heredoc form: $GITHUB_OUTPUT never decodes the
# %0A escaping of the retired ::set-output command, which is how v1.17.2-v1.17.5
# got release notes full of literal %0A. The random delimiter stops commit
# subjects from closing the value early.
DELIMITER="CHANGELOG_EOF_$(openssl rand -hex 16)"
{
  echo "changelog<<$DELIMITER"
  printf '%s\n' "$(cat changelog.md)"
  echo "$DELIMITER"
} >> "$GITHUB_OUTPUT"
