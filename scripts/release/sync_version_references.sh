#!/bin/bash
# Sync version references across README.md, Helm chart, and docs after a release tag.
# Usage: sync_version_references.sh <version> <tag>
#   version: bare semver, e.g. 1.17.5
#   tag:     git tag, e.g. v1.17.5

set -euo pipefail

VERSION="${1:?Usage: sync_version_references.sh <version> <tag>}"
TAG="${2:?Usage: sync_version_references.sh <version> <tag>}"

# README.md: version badge + example tag
sed -i.bak "s|version-[0-9]*\.[0-9]*\.[0-9]*-blue|version-${VERSION}-blue|g" README.md
sed -i.bak "s|- \`v[0-9]*\.[0-9]*\.[0-9]*\` - Specific version|- \`${TAG}\` - Specific version|g" README.md
rm -f README.md.bak

# Helm chart: version, appVersion, default image tag
sed -i.bak "s|^version: .*|version: ${VERSION}|g" helm/simplenote-mcp-server/Chart.yaml
sed -i.bak "s|^appVersion: .*|appVersion: \"${VERSION}\"|g" helm/simplenote-mcp-server/Chart.yaml
sed -i.bak "s|tag: \".*\"|tag: \"${TAG}\"|g" helm/simplenote-mcp-server/values.yaml
rm -f helm/simplenote-mcp-server/Chart.yaml.bak helm/simplenote-mcp-server/values.yaml.bak

# Docker CI/CD setup docs, if present
if [ -f "docs/DOCKER_CI_CD_SETUP.md" ]; then
  sed -i.bak "s|docdyhr/simplenote-mcp-server:v[0-9]*\.[0-9]*\.[0-9]*|docdyhr/simplenote-mcp-server:${TAG}|g" docs/DOCKER_CI_CD_SETUP.md
  rm -f docs/DOCKER_CI_CD_SETUP.md.bak
fi
