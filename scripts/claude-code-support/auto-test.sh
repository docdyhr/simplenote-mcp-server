#!/bin/bash
# Auto-test script for Claude Code
# Intelligently runs relevant tests based on changed files

set -euo pipefail

# Configuration
OFFLINE_MODE="true"
VERBOSE=${VERBOSE:-false}
QUICK_MODE=${QUICK_MODE:-false}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Function to find related test files
find_related_tests() {
    local file="$1"
    local tests=()

    # Direct test file mapping
    local basename=$(basename "$file" .py)
    local test_file="tests/test_${basename}.py"

    if [ -f "$test_file" ]; then
        tests+=("$test_file")
    fi

    # Find tests that import this module
    local module_name=$(echo "$file" | sed 's/\.py$//' | sed 's/\//./g' | sed 's/^simplenote_mcp\.//')

    while IFS= read -r -d '' test; do
        if grep -l "from.*${module_name}\|import.*${module_name}" "$test" >/dev/null 2>&1; then
            tests+=("$test")
        fi
    done < <(find tests -name "test_*.py" -print0)

    printf '%s\n' "${tests[@]}" | sort -u
}

# Function to run specific tests
run_tests() {
    local test_files=("$@")
    local exit_code=0

    export SIMPLENOTE_OFFLINE_MODE="$OFFLINE_MODE"

    if [ ${#test_files[@]} -eq 0 ]; then
        log "No specific tests found, running full suite..."
        if $QUICK_MODE; then
            python -m pytest tests/ -x -q --tb=short --maxfail=5
        else
            python -m pytest tests/ -v --tb=short
        fi
        return $?
    fi

    log "Running ${#test_files[@]} related test file(s)..."

    for test_file in "${test_files[@]}"; do
        if [ -f "$test_file" ]; then
            log "Running $test_file..."
            if $VERBOSE; then
                python -m pytest "$test_file" -v --tb=short
            else
                python -m pytest "$test_file" -q --tb=line
            fi

            if [ $? -ne 0 ]; then
                error "Test failed: $test_file"
                exit_code=1
                if $QUICK_MODE; then
                    break
                fi
            else
                success "Test passed: $test_file"
            fi
        else
            warn "Test file not found: $test_file"
        fi
    done

    return $exit_code
}

# Function to run performance check
check_performance() {
    log "Checking performance..."
    if [ -f "tests/test_performance.py" ]; then
        python -m pytest tests/test_performance.py -q --tb=short
    else
        warn "Performance tests not found"
    fi
}

# Function to check code coverage
check_coverage() {
    local files=("$@")
    log "Checking code coverage..."

    if [ ${#files[@]} -eq 0 ]; then
        python -m pytest tests/ --cov=simplenote_mcp --cov-report=term-missing:skip-covered --cov-fail-under=75 -q
    else
        # Coverage for specific modules
        local modules=""
        for file in "${files[@]}"; do
            if [[ "$file" == simplenote_mcp/* ]]; then
                local module=$(echo "$file" | sed 's/\.py$//' | sed 's/\//./g')
                modules="$modules --cov=$module"
            fi
        done

        if [ -n "$modules" ]; then
            python -m pytest tests/ $modules --cov-report=term-missing:skip-covered -q
        fi
    fi
}

# Function to validate changed files
validate_files() {
    local files=("$@")

    for file in "${files[@]}"; do
        if [[ "$file" == *.py ]]; then
            log "Validating $file..."

            # Syntax check
            python -m py_compile "$file" || {
                error "Syntax error in $file"
                return 1
            }

            # Type check (non-blocking)
            if command -v mypy >/dev/null 2>&1; then
                mypy "$file" --ignore-missing-imports 2>/dev/null || warn "Type issues in $file"
            fi

            # Format check
            if command -v ruff >/dev/null 2>&1; then
                ruff check "$file" --quiet || warn "Linting issues in $file"
            fi
        fi
    done
}

# Main execution
main() {
    local files=()
    local run_all=false
    local check_cov=false
    local check_perf=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --all|-a)
                run_all=true
                shift
                ;;
            --coverage|-c)
                check_cov=true
                shift
                ;;
            --performance|-p)
                check_perf=true
                shift
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --quick|-q)
                QUICK_MODE=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS] [FILES...]"
                echo "Options:"
                echo "  -a, --all         Run all tests"
                echo "  -c, --coverage    Check code coverage"
                echo "  -p, --performance Check performance"
                echo "  -v, --verbose     Verbose output"
                echo "  -q, --quick       Quick mode (fail fast)"
                echo "  -h, --help        Show this help"
                exit 0
                ;;
            *)
                if [ -f "$1" ]; then
                    files+=("$1")
                fi
                shift
                ;;
        esac
    done

    # Set up environment
    log "Setting up test environment..."
    export SIMPLENOTE_OFFLINE_MODE="$OFFLINE_MODE"

    # If no files specified and not running all, detect changed files
    if [ ${#files[@]} -eq 0 ] && [ "$run_all" = false ]; then
        log "Detecting changed files..."

        # Use portable method for reading files into array
        while IFS= read -r file; do
            files+=("$file")
        done < <(git diff --name-only HEAD~1..HEAD 2>/dev/null | grep -E '\.(py)$' || true)

        if [ ${#files[@]} -eq 0 ]; then
            # Check staged files
            while IFS= read -r file; do
                files+=("$file")
            done < <(git diff --name-only --cached 2>/dev/null | grep -E '\.(py)$' || true)
        fi

        if [ ${#files[@]} -eq 0 ]; then
            warn "No changed files detected, running all tests"
            run_all=true
        else
            log "Found ${#files[@]} changed file(s): ${files[*]}"
        fi
    fi

    local exit_code=0

    # Validate files first
    if [ ${#files[@]} -gt 0 ] && [ "$run_all" = false ]; then
        validate_files "${files[@]}" || exit_code=1
    fi

    # Find and run tests
    if [ "$run_all" = true ]; then
        log "Running full test suite..."
        run_tests || exit_code=1
    else
        local test_files=()
        for file in "${files[@]}"; do
            while IFS= read -r test_file; do
                test_files+=("$test_file")
            done < <(find_related_tests "$file")
        done

        # Remove duplicates
        IFS=$'\n' test_files=($(printf '%s\n' "${test_files[@]}" | sort -u))

        run_tests "${test_files[@]}" || exit_code=1
    fi

    # Additional checks
    if [ "$check_perf" = true ]; then
        check_performance || warn "Performance check failed"
    fi

    if [ "$check_cov" = true ]; then
        check_coverage "${files[@]}" || warn "Coverage check failed"
    fi

    # Summary
    if [ $exit_code -eq 0 ]; then
        success "All tests passed! 🎉"
    else
        error "Some tests failed! 💥"
    fi

    return $exit_code
}

# Run main function with all arguments
main "$@"
