#!/bin/bash
# Delete release/<TAG> once its release PR has merged. Reads TAG (vX.Y.Z) and
# GITHUB_REPOSITORY from the environment; gh authenticates via GH_TOKEN.
#
# `gh pr merge --auto --delete-branch` doesn't delete the branch when the
# merge happens later through auto-merge, and the repo doesn't auto-delete
# head branches, so every release left release/vX.Y.Z behind. Deletes only
# when the branch tip is exactly the merged PR's head and no open PR uses
# the branch; otherwise keeps it and says why.

set -euo pipefail

: "${TAG:?TAG is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
BRANCH="release/$TAG"

if ! TIP=$(gh api "repos/$GITHUB_REPOSITORY/git/refs/heads/$BRANCH" --jq .object.sha 2>/dev/null); then
  echo "Couldn't read $BRANCH (already gone, or an API error); not deleting anything"
  exit 0
fi

OPEN=$(gh pr list --repo "$GITHUB_REPOSITORY" --head "$BRANCH" --state open \
  --json number --jq length)
MERGED_HEAD=$(gh pr list --repo "$GITHUB_REPOSITORY" --head "$BRANCH" --state merged \
  --json headRefOid --jq '.[0].headRefOid // empty')

if [ "$OPEN" != "0" ] || [ -z "$MERGED_HEAD" ] || [ "$TIP" != "$MERGED_HEAD" ]; then
  echo "::warning::Keeping $BRANCH: open PRs $OPEN, merged PR head ${MERGED_HEAD:-none}, branch tip $TIP"
  exit 0
fi

gh api -X DELETE "repos/$GITHUB_REPOSITORY/git/refs/heads/$BRANCH" >/dev/null
echo "Deleted $BRANCH (tip $TIP, the merged release PR's head)"
