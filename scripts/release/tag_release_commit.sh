#!/bin/bash
# Tag the release PR's merge commit and push the tag. Reads NEW_VERSION and
# MERGE_SHA from the environment; writes commit_sha to $GITHUB_OUTPUT.
#
# Tags MERGE_SHA, never origin/main's HEAD: another PR merged between the
# release PR's merge and this step would otherwise get the release tag. Refuses
# a commit that is not on origin/main or whose VERSION file disagrees.

set -euo pipefail

: "${NEW_VERSION:?NEW_VERSION is required}"
: "${MERGE_SHA:?MERGE_SHA is required}"

if ! printf '%s' "$MERGE_SHA" | grep -qE '^[0-9a-f]{40}$'; then
  echo "::error::MERGE_SHA is not a full commit SHA: $MERGE_SHA" >&2
  exit 1
fi

git fetch --no-tags origin main
if ! git merge-base --is-ancestor "$MERGE_SHA" origin/main; then
  echo "::error::$MERGE_SHA is not on origin/main; refusing to tag it" >&2
  exit 1
fi

FOUND=$(git show "$MERGE_SHA:VERSION" | tr -d '[:space:]')
if [ "$FOUND" != "$NEW_VERSION" ]; then
  echo "::error::VERSION at $MERGE_SHA is '$FOUND', expected '$NEW_VERSION'" >&2
  exit 1
fi

git tag -a "v$NEW_VERSION" -m "Version $NEW_VERSION" "$MERGE_SHA"
git push origin "v$NEW_VERSION"
echo "Tagged $MERGE_SHA as v$NEW_VERSION (origin/main is $(git rev-parse origin/main))"
echo "commit_sha=$MERGE_SHA" >> "$GITHUB_OUTPUT"
