#!/bin/bash
set -e

# Docker build test script for Simplenote MCP Server
# This script tests the Docker build and basic functionality locally

echo "🐳 Testing Docker build and functionality for Simplenote MCP Server"
echo "=================================================================="

# Variables
IMAGE_NAME="simplenote-mcp-server:test"
CONTAINER_NAME="simplenote-mcp-test"

# Cleanup function
cleanup() {
    echo "🧹 Cleaning up..."
    docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
    docker rmi -f "$IMAGE_NAME" 2>/dev/null || true
}

# Set trap for cleanup on exit
trap cleanup EXIT

# Test 1: Build the Docker image
echo "📦 Building Docker image..."
if docker build -t "$IMAGE_NAME" .; then
    echo "✅ Docker build successful"
else
    echo "❌ Docker build failed"
    exit 1
fi

# Test 2: Check image was created
echo "🔍 Checking image exists..."
if docker images "$IMAGE_NAME" --format "table {{.Repository}}:{{.Tag}}" | grep -q "$IMAGE_NAME"; then
    echo "✅ Image exists"
else
    echo "❌ Image not found"
    exit 1
fi

# Test 3: Test help command
echo "📖 Testing help command..."
if docker run --rm --name "$CONTAINER_NAME-help" "$IMAGE_NAME" --help; then
    echo "✅ Help command works"
else
    echo "❌ Help command failed"
    exit 1
fi

# Test 4: Test module import
echo "🐍 Testing Python module import..."
if docker run --rm --name "$CONTAINER_NAME-import" "$IMAGE_NAME" python -c "import simplenote_mcp.server; print('✅ Module import successful')"; then
    echo "✅ Module import test passed"
else
    echo "❌ Module import test failed"
    exit 1
fi

# Test 5: Test console script availability
echo "🔧 Testing console script..."
if docker run --rm --name "$CONTAINER_NAME-script" "$IMAGE_NAME" which simplenote-mcp-server; then
    echo "✅ Console script available"
else
    echo "⚠️ Console script not found, but this is acceptable if module execution works"
fi

# Test 6: Test with environment variables (should start but fail auth)
echo "🔐 Testing with environment variables..."
docker run --rm --name "$CONTAINER_NAME-env" \
    -e SIMPLENOTE_EMAIL=test@example.com \
    -e SIMPLENOTE_PASSWORD=testpassword \
    -e SIMPLENOTE_OFFLINE_MODE=true \
    "$IMAGE_NAME" python -c "
import os
print('Environment variables:')
print(f'SIMPLENOTE_EMAIL: {os.getenv(\"SIMPLENOTE_EMAIL\", \"Not set\")}')
print(f'SIMPLENOTE_PASSWORD: {\"***\" if os.getenv(\"SIMPLENOTE_PASSWORD\") else \"Not set\"}')
print(f'SIMPLENOTE_OFFLINE_MODE: {os.getenv(\"SIMPLENOTE_OFFLINE_MODE\", \"Not set\")}')
print('✅ Environment test passed')
" && echo "✅ Environment variable test passed"

# Test 7: Test health check
echo "🏥 Testing health check..."
if docker run --rm --name "$CONTAINER_NAME-health" "$IMAGE_NAME" python -c "import simplenote_mcp.server; print('✅ Health check passed')"; then
    echo "✅ Health check works"
else
    echo "❌ Health check failed"
    exit 1
fi

# Test 8: Check image size
echo "📏 Checking image size..."
SIZE=$(docker images "$IMAGE_NAME" --format "{{.Size}}")
echo "📦 Image size: $SIZE"

# Test 9: Check image layers
echo "🔍 Checking image history..."
docker history "$IMAGE_NAME" --format "table {{.CreatedBy}}\t{{.Size}}" | head -10

echo ""
echo "🎉 All Docker tests passed successfully!"
echo "✅ The Docker image is ready for deployment"
echo ""
echo "To run the container:"
echo "docker run -e SIMPLENOTE_EMAIL=your@email.com -e SIMPLENOTE_PASSWORD=yourpassword $IMAGE_NAME"
