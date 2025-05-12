#!/bin/bash
# release.sh - Release a new version of Simplenote MCP

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Go to project root
cd "$PROJECT_ROOT" || exit 1

# Check if the working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    echo "Error: Working directory is not clean. Please commit all changes before release."
    exit 1
fi

# Check parameters
if [ $# -ne 1 ]; then
    echo "Usage: $0 <release-type>"
    echo "  release-type: patch, minor, major"
    exit 1
fi

RELEASE_TYPE=$1

# Get current version
CURRENT_VERSION=$(cat VERSION)
echo "Current version: $CURRENT_VERSION"

# Split version into components
IFS='.' read -r -a VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR=${VERSION_PARTS[0]}
MINOR=${VERSION_PARTS[1]}
PATCH=${VERSION_PARTS[2]}

# Calculate new version
case $RELEASE_TYPE in
    patch)
        PATCH=$((PATCH + 1))
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    *)
        echo "Error: Invalid release type. Must be one of: patch, minor, major"
        exit 1
        ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"
echo "New version: $NEW_VERSION"

# Update version in files
echo "$NEW_VERSION" > VERSION
echo "Updated VERSION file"

# Update version in Python files
sed -i '' "s/__version__ = \"$CURRENT_VERSION\"/__version__ = \"$NEW_VERSION\"/" simplenote_mcp/__init__.py
echo "Updated simplenote_mcp/__init__.py"

# Update version in setup.py
sed -i '' "s/version=\"$CURRENT_VERSION\"/version=\"$NEW_VERSION\"/" setup.py
echo "Updated setup.py"

# Update version in pyproject.toml
sed -i '' "s/version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml
echo "Updated pyproject.toml"

# Update CHANGELOG.md
DATE=$(date +%Y-%m-%d)
sed -i '' "s/## \[$NEW_VERSION\] - Unreleased/## [$NEW_VERSION] - $DATE/" CHANGELOG.md
echo "Updated CHANGELOG.md"

# Commit changes
git add VERSION simplenote_mcp/__init__.py setup.py pyproject.toml CHANGELOG.md
git commit -m "Release version $NEW_VERSION"
echo "Committed version changes"

# Create tag
git tag -a "v$NEW_VERSION" -m "Version $NEW_VERSION"
echo "Created tag v$NEW_VERSION"

echo ""
echo "Version $NEW_VERSION has been released."
echo "Don't forget to push the changes with: git push && git push --tags"
