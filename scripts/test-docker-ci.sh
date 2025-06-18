#!/bin/bash
# Test script for Docker CI/CD setup

set -e

echo "🐳 Docker CI/CD Test Suite"
echo "========================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test functions
test_docker_build() {
    echo -e "\n${YELLOW}Testing Docker build...${NC}"
    if docker build -t simplenote-mcp-server:test .; then
        echo -e "${GREEN}✓ Docker build successful${NC}"
        return 0
    else
        echo -e "${RED}✗ Docker build failed${NC}"
        return 1
    fi
}

test_docker_run() {
    echo -e "\n${YELLOW}Testing Docker run...${NC}"
    if docker run --rm simplenote-mcp-server:test --help > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Docker run successful${NC}"
        return 0
    else
        echo -e "${RED}✗ Docker run failed${NC}"
        return 1
    fi
}

test_docker_compose() {
    echo -e "\n${YELLOW}Testing Docker Compose...${NC}"

    # Create test env file
    echo "SIMPLENOTE_EMAIL=test@example.com" > .env.test
    echo "SIMPLENOTE_PASSWORD=testpassword" >> .env.test

    if docker-compose --env-file .env.test config > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Docker Compose config valid${NC}"
        rm -f .env.test
        return 0
    else
        echo -e "${RED}✗ Docker Compose config invalid${NC}"
        rm -f .env.test
        return 1
    fi
}

test_multi_platform_build() {
    echo -e "\n${YELLOW}Testing multi-platform build setup...${NC}"

    # Check if buildx is available
    if docker buildx version > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Docker buildx available${NC}"

        # List available platforms
        echo "  Available platforms:"
        docker buildx ls | grep -E "linux/(amd64|arm64)" | sed 's/^/    /'
        return 0
    else
        echo -e "${RED}✗ Docker buildx not available${NC}"
        return 1
    fi
}

test_workflow_syntax() {
    echo -e "\n${YELLOW}Testing GitHub Actions workflow syntax...${NC}"

    WORKFLOW_FILE=".github/workflows/docker-publish.yml"

    if [ -f "$WORKFLOW_FILE" ]; then
        # Basic YAML syntax check
        if python3 -c "import yaml; yaml.safe_load(open('$WORKFLOW_FILE'))" 2>/dev/null; then
            echo -e "${GREEN}✓ Workflow YAML syntax valid${NC}"
            return 0
        else
            echo -e "${RED}✗ Workflow YAML syntax invalid${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ Workflow file not found${NC}"
        return 1
    fi
}

test_dockerfile_best_practices() {
    echo -e "\n${YELLOW}Checking Dockerfile best practices...${NC}"

    if [ -f "Dockerfile" ]; then
        # Check for non-root user
        if grep -q "USER mcp" Dockerfile; then
            echo -e "${GREEN}✓ Non-root user configured${NC}"
        else
            echo -e "${RED}✗ No non-root user found${NC}"
        fi

        # Check for multi-stage build
        if grep -q "FROM.*AS" Dockerfile; then
            echo -e "${GREEN}✓ Multi-stage build used${NC}"
        else
            echo -e "${YELLOW}⚠ Consider using multi-stage build${NC}"
        fi

        # Check for health check
        if grep -q "HEALTHCHECK" Dockerfile; then
            echo -e "${GREEN}✓ Health check configured${NC}"
        else
            echo -e "${YELLOW}⚠ Consider adding HEALTHCHECK${NC}"
        fi

        return 0
    else
        echo -e "${RED}✗ Dockerfile not found${NC}"
        return 1
    fi
}

# Run tests
echo -e "\nRunning tests..."

TESTS_PASSED=0
TESTS_FAILED=0

# Run each test and track results
for test in test_docker_build test_docker_run test_docker_compose test_multi_platform_build test_workflow_syntax test_dockerfile_best_practices; do
    if $test; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
done

# Summary
echo -e "\n${YELLOW}Test Summary${NC}"
echo "============"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"

# Cleanup
echo -e "\n${YELLOW}Cleaning up...${NC}"
docker rmi simplenote-mcp-server:test 2>/dev/null || true

# Exit code
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}All tests passed! 🎉${NC}"
    exit 0
else
    echo -e "\n${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
