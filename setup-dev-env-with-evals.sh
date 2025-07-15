#!/bin/bash
# Development setup script for Simplenote MCP Server with mcp-evals integration

set -e

echo "🚀 Setting up Simplenote MCP Server development environment with mcp-evals..."

# Check prerequisites
check_prerequisites() {
    echo "📋 Checking prerequisites..."

    # Check Python
    if ! command -v python3 &>/dev/null; then
        echo "❌ Python 3 is required but not installed"
        exit 1
    fi

    python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    echo "✅ Python $python_version found"

    # Check Node.js
    if ! command -v node &>/dev/null; then
        echo "❌ Node.js is required for mcp-evals but not installed"
        echo "Please install Node.js 18+ from https://nodejs.org/"
        exit 1
    fi

    node_version=$(node --version)
    echo "✅ Node.js $node_version found"

    # Check npm
    if ! command -v npm &>/dev/null; then
        echo "❌ npm is required but not installed"
        exit 1
    fi

    npm_version=$(npm --version)
    echo "✅ npm $npm_version found"
}

# Setup Python environment
setup_python() {
    echo "🐍 Setting up Python environment..."

    # Install Python dependencies
    pip install -e .[dev,test,monitoring]
    echo "✅ Python dependencies installed"

    # Setup pre-commit if available
    if command -v pre-commit &>/dev/null; then
        pre-commit install
        echo "✅ Pre-commit hooks installed"
    fi
}

# Setup Node.js environment for mcp-evals
setup_nodejs() {
    echo "📦 Setting up Node.js environment for mcp-evals..."

    # Install Node.js dependencies
    npm install
    echo "✅ Node.js dependencies installed"

    # Validate evaluation files
    npm run validate:evals
    echo "✅ Evaluation files validated"
}

# Setup environment files
setup_environment() {
    echo "🔧 Setting up environment configuration..."

    # Create .env.example if it doesn't exist
    if [ ! -f .env.example ]; then
        cat >.env.example <<EOF
# Simplenote MCP Server Configuration
SIMPLENOTE_EMAIL=your.email@example.com
SIMPLENOTE_PASSWORD=your_app_password

# Optional: OpenAI API Key for evaluations
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional: Monitoring
ENABLE_METRICS=false
METRICS_PORT=9090
EOF
        echo "✅ Created .env.example"
    fi

    # Create .env.test for testing
    if [ ! -f .env.test ]; then
        cat >.env.test <<EOF
# Test environment configuration
SIMPLENOTE_EMAIL=test@example.com
SIMPLENOTE_PASSWORD=test_password
LOG_LEVEL=DEBUG
EOF
        echo "✅ Created .env.test"
    fi
}

# Verify installation
verify_installation() {
    echo "🔍 Verifying installation..."

    # Test Python setup
    python3 -c "import simplenote_mcp; print('✅ Python package import successful')"

    # Test Node.js setup
    if npx mcp-eval --version &>/dev/null; then
        echo "✅ mcp-evals CLI available"
    else
        echo "⚠️  mcp-evals CLI not available (this is expected if not installed globally)"
    fi

    # Test evaluation file syntax
    npm run validate:evals
    echo "✅ All evaluation files are valid"
}

# Print usage information
print_usage() {
    echo ""
    echo "🎉 Setup complete! Here's what you can do next:"
    echo ""
    echo "Python Development:"
    echo "  python3 simplenote_mcp_server.py  # Run the MCP server"
    echo "  pytest                           # Run Python tests"
    echo "  ruff check .                     # Lint Python code"
    echo ""
    echo "MCP Evaluations:"
    echo "  npm run eval:smoke               # Quick smoke tests"
    echo "  npm run eval:basic               # Basic evaluation suite"
    echo "  npm run eval:comprehensive       # Comprehensive evaluations"
    echo "  npm run eval:all                 # Run all evaluations"
    echo ""
    echo "Development Tools:"
    echo "  pre-commit run --all-files       # Run all pre-commit checks"
    echo "  npm run validate:evals           # Validate evaluation files"
    echo ""
    echo "Configuration:"
    echo "  1. Copy .env.example to .env and fill in your credentials"
    echo "  2. Set OPENAI_API_KEY for running evaluations"
    echo "  3. Configure your Simplenote credentials for testing"
    echo ""
    echo "Documentation:"
    echo "  evals/README.md                  # MCP evaluations guide"
    echo "  README.md                        # Main project documentation"
    echo ""
}

# Main execution
main() {
    check_prerequisites
    setup_python
    setup_nodejs
    setup_environment
    verify_installation
    print_usage
}

# Handle command line arguments
case "${1:-}" in
--help | -h)
    echo "Simplenote MCP Server Development Setup"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --help, -h    Show this help message"
    echo "  --check       Only check prerequisites"
    echo ""
    exit 0
    ;;
--check)
    check_prerequisites
    echo "✅ All prerequisites met"
    exit 0
    ;;
*)
    main
    ;;
esac
