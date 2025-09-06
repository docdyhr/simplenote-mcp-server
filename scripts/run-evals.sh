#!/bin/bash
# Run MCP evaluations with proper environment setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 MCP Evaluation Runner${NC}"
echo "================================"

# Setup environment
export TSX_CACHE_DIR="${TSX_CACHE_DIR:-$HOME/.tsx-cache}"
export NODE_OPTIONS="${NODE_OPTIONS:---max-old-space-size=4096}"
export SIMPLENOTE_OFFLINE_MODE="${SIMPLENOTE_OFFLINE_MODE:-true}"

# Create cache directory with proper permissions
if [ ! -d "$TSX_CACHE_DIR" ]; then
    echo -e "${YELLOW}Creating TSX cache directory: $TSX_CACHE_DIR${NC}"
    mkdir -p "$TSX_CACHE_DIR"
    chmod 755 "$TSX_CACHE_DIR"
fi

# Check if running in CI or locally
if [ -n "$CI" ]; then
    echo -e "${YELLOW}Running in CI environment${NC}"
    export TSX_CACHE_DIR="/tmp/tsx-cache-$$"
    mkdir -p "$TSX_CACHE_DIR"
fi

# Ensure npm dependencies are installed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing npm dependencies...${NC}"
    npm ci
fi

# Validate evaluation files first
echo -e "${GREEN}Validating evaluation files...${NC}"
npm run validate:evals || {
    echo -e "${RED}❌ Evaluation files validation failed${NC}"
    exit 1
}

# Function to run evaluation with retry
run_eval_with_retry() {
    local eval_type=$1
    local max_attempts=3
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        echo -e "${GREEN}Running $eval_type evaluation (attempt $attempt/$max_attempts)...${NC}"

        if npm run eval:$eval_type; then
            echo -e "${GREEN}✅ $eval_type evaluation completed successfully${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️ $eval_type evaluation failed (attempt $attempt)${NC}"

            if [ $attempt -lt $max_attempts ]; then
                echo "Retrying in 5 seconds..."
                sleep 5
            fi
        fi

        attempt=$((attempt + 1))
    done

    echo -e "${RED}❌ $eval_type evaluation failed after $max_attempts attempts${NC}"
    return 1
}

# Parse arguments
EVAL_TYPE="${1:-smoke}"

case $EVAL_TYPE in
smoke)
    run_eval_with_retry smoke
    ;;
basic)
    run_eval_with_retry basic
    ;;
comprehensive)
    run_eval_with_retry comprehensive
    ;;
all)
    echo -e "${GREEN}Running all evaluations...${NC}"
    run_eval_with_retry smoke &&
        run_eval_with_retry basic &&
        run_eval_with_retry comprehensive
    ;;
*)
    echo -e "${RED}Usage: $0 [smoke|basic|comprehensive|all]${NC}"
    exit 1
    ;;
esac

# Cleanup
if [ -n "$CI" ] && [ -d "$TSX_CACHE_DIR" ]; then
    echo -e "${YELLOW}Cleaning up temporary cache directory${NC}"
    rm -rf "$TSX_CACHE_DIR"
fi

echo -e "${GREEN}🎉 Evaluation complete!${NC}"
