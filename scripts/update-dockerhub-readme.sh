#!/bin/bash
# Docker Hub README Update Script
#
# This script updates the Docker Hub repository description from a README file.
# It provides a convenient wrapper around the Python script with proper error handling.

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Print functions
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}" >&2
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_header() {
    echo -e "\n${BOLD}${BLUE}$1${NC}"
    echo -e "${BLUE}$(printf '=%.0s' $(seq 1 ${#1}))${NC}\n"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python requirements
check_python_requirements() {
    print_info "Checking Python requirements..."
    [[ "$verbose" == true ]] && print_info "Verbose mode: Checking for Python 3.7+"

    if ! command_exists python3; then
        print_error "Python 3 is required but not installed"
        return 1
    fi

    # Check for requests module
    if ! python3 -c "import requests" 2>/dev/null; then
        print_warning "requests module not found, attempting to install..."
        if ! pip3 install requests; then
            print_error "Failed to install requests module"
            return 1
        fi
    fi

    print_success "Python requirements satisfied"
}

# Function to validate environment variables
validate_environment() {
    print_info "Validating environment variables..."
    [[ "$verbose" == true ]] && print_info "Verbose mode: Checking required environment variables"

    local missing_vars=()

    if [[ -z "${DOCKER_USERNAME:-}" ]]; then
        missing_vars+=("DOCKER_USERNAME")
    fi

    if [[ -z "${DOCKER_TOKEN:-}" ]]; then
        missing_vars+=("DOCKER_TOKEN")
    fi

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        print_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo -e "  ${RED}- $var${NC}"
        done
        echo
        print_info "Please set the missing variables and try again:"
        echo -e "  ${BLUE}export DOCKER_USERNAME=your-username${NC}"
        echo -e "  ${BLUE}export DOCKER_TOKEN=your-access-token${NC}"
        return 1
    fi

    print_success "Environment variables validated"
}

# Function to check if README file exists
check_readme_file() {
    local readme_file="${README_FILE:-DOCKER_README.md}"

    print_info "Checking README file: $readme_file"

    if [[ ! -f "$readme_file" ]]; then
        print_error "README file not found: $readme_file"
        print_info "Available README files:"
        find . -name "*.md" -type f | head -5 | while read -r file; do
            echo -e "  ${BLUE}- $file${NC}"
        done
        return 1
    fi

    local file_size
    file_size=$(wc -c <"$readme_file")
    print_success "README file found (${file_size} bytes)"
}

# Function to display current configuration
show_configuration() {
    print_header "Current Configuration"

    echo -e "${BOLD}Docker Hub Settings:${NC}"
    echo -e "  Username: ${BLUE}${DOCKER_USERNAME}${NC}"
    echo -e "  Repository: ${BLUE}${DOCKER_REPOSITORY:-docdyhr/simplenote-mcp-server}${NC}"
    echo -e "  Token: ${BLUE}$(printf '%*s' ${#DOCKER_TOKEN} | tr ' ' '*')${NC}"
    echo
    echo -e "${BOLD}File Settings:${NC}"
    echo -e "  README File: ${BLUE}${README_FILE:-DOCKER_README.md}${NC}"
    echo -e "  Short Description: ${BLUE}${SHORT_DESCRIPTION:-A Model Context Protocol (MCP) server...}${NC}"
    echo
}

# Function to run the update
run_update() {
    print_header "Updating Docker Hub README"

    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local python_script="$script_dir/update-dockerhub-readme.py"

    if [[ ! -f "$python_script" ]]; then
        print_error "Python update script not found: $python_script"
        return 1
    fi

    print_info "Running update script..."

    if python3 "$python_script"; then
        print_success "Docker Hub README updated successfully!"
        print_info "View your repository at: https://hub.docker.com/r/${DOCKER_REPOSITORY:-docdyhr/simplenote-mcp-server}"
        return 0
    else
        print_error "Failed to update Docker Hub README"
        return 1
    fi
}

# Function to show usage
show_usage() {
    cat <<EOF
${BOLD}Docker Hub README Update Script${NC}

${BOLD}USAGE:${NC}
    $0 [OPTIONS]

${BOLD}DESCRIPTION:${NC}
    Updates the Docker Hub repository description from a local README file.

${BOLD}REQUIRED ENVIRONMENT VARIABLES:${NC}
    DOCKER_USERNAME     Docker Hub username
    DOCKER_TOKEN        Docker Hub access token

${BOLD}OPTIONAL ENVIRONMENT VARIABLES:${NC}
    DOCKER_REPOSITORY   Repository name (default: docdyhr/simplenote-mcp-server)
    README_FILE         README file path (default: DOCKER_README.md)
    SHORT_DESCRIPTION   Short description for the repository

${BOLD}OPTIONS:${NC}
    -h, --help          Show this help message
    -c, --check         Check configuration without updating
    -v, --verbose       Enable verbose output

${BOLD}EXAMPLES:${NC}
    # Basic usage (requires environment variables to be set)
    $0

    # Check configuration only
    $0 --check

    # Set variables and run
    DOCKER_USERNAME=myuser DOCKER_TOKEN=mytoken $0

    # Use custom README file
    README_FILE=custom-readme.md $0

${BOLD}SETUP:${NC}
    1. Get a Docker Hub access token:
       https://hub.docker.com/settings/security

    2. Set environment variables:
       export DOCKER_USERNAME=your-username
       export DOCKER_TOKEN=your-access-token

    3. Run the script:
       $0

EOF
}

# Main function
main() {
    local check_only=false
    local verbose=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
        -h | --help)
            show_usage
            exit 0
            ;;
        -c | --check)
            check_only=true
            shift
            ;;
        -v | --verbose)
            verbose=true
            set -x
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
        esac
    done

    print_header "Docker Hub README Updater"

    # Run validation checks
    if ! check_python_requirements; then
        exit 1
    fi

    if ! validate_environment; then
        exit 1
    fi

    if ! check_readme_file; then
        exit 1
    fi

    # Show current configuration
    show_configuration

    # If check-only mode, exit here
    if [[ "$check_only" == true ]]; then
        print_success "Configuration check completed successfully"
        exit 0
    fi

    # Confirm before proceeding
    echo -n "Proceed with updating Docker Hub README? [y/N] "
    read -r response
    case "$response" in
    [yY][eE][sS] | [yY]) ;;
    *)
        print_info "Operation cancelled"
        exit 0
        ;;
    esac

    # Run the update
    if run_update; then
        exit 0
    else
        exit 1
    fi
}

# Run main function with all arguments
main "$@"
