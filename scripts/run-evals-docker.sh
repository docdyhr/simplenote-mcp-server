#!/bin/bash
# Run MCP evaluations in Docker to avoid permission issues

set -e

echo "🐳 Running MCP Evaluations in Docker..."

# Build the evaluation Docker image
echo "Building Docker image..."
docker build -f Dockerfile.eval -t simplenote-mcp-eval:latest .

# Run evaluations based on argument
EVAL_TYPE="${1:-smoke}"

case $EVAL_TYPE in
  smoke)
    echo "Running smoke tests..."
    docker run --rm \
      -e SIMPLENOTE_EMAIL="${SIMPLENOTE_EMAIL}" \
      -e SIMPLENOTE_PASSWORD="${SIMPLENOTE_PASSWORD}" \
      -e SIMPLENOTE_OFFLINE_MODE=true \
      -v "$(pwd)/eval-results:/app/eval-results" \
      simplenote-mcp-eval:latest npm run eval:smoke
    ;;
  basic)
    echo "Running basic evaluations..."
    docker run --rm \
      -e SIMPLENOTE_EMAIL="${SIMPLENOTE_EMAIL}" \
      -e SIMPLENOTE_PASSWORD="${SIMPLENOTE_PASSWORD}" \
      -e SIMPLENOTE_OFFLINE_MODE=true \
      -v "$(pwd)/eval-results:/app/eval-results" \
      simplenote-mcp-eval:latest npm run eval:basic
    ;;
  comprehensive)
    echo "Running comprehensive evaluations..."
    docker run --rm \
      -e SIMPLENOTE_EMAIL="${SIMPLENOTE_EMAIL}" \
      -e SIMPLENOTE_PASSWORD="${SIMPLENOTE_PASSWORD}" \
      -e SIMPLENOTE_OFFLINE_MODE=true \
      -v "$(pwd)/eval-results:/app/eval-results" \
      simplenote-mcp-eval:latest npm run eval:comprehensive
    ;;
  all)
    echo "Running all evaluations..."
    docker run --rm \
      -e SIMPLENOTE_EMAIL="${SIMPLENOTE_EMAIL}" \
      -e SIMPLENOTE_PASSWORD="${SIMPLENOTE_PASSWORD}" \
      -e SIMPLENOTE_OFFLINE_MODE=true \
      -v "$(pwd)/eval-results:/app/eval-results" \
      simplenote-mcp-eval:latest npm run eval:all
    ;;
  *)
    echo "Usage: $0 [smoke|basic|comprehensive|all]"
    exit 1
    ;;
esac

echo "✅ Evaluation complete!"
