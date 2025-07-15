# Simplenote MCP Server

![Simplenote MCP Server Logo](assets/logo.png)

A lightweight MCP server that integrates [Simplenote](https://simplenote.com/) with [Claude Desktop](https://github.com/johnsmith9982/claude-desktop) using the [MCP Python SDK](https://github.com/johnsmith9982/mcp-python-sdk).

This allows Claude Desktop to interact with your Simplenote notes as a memory backend or content source.

<!-- Status & Build Badges -->
[![CI/CD Pipeline](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/ci.yml)
[![Code Quality](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/code-quality.yml/badge.svg?branch=main)](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/code-quality.yml)
[![Security](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/security.yml)
[![Docker](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/docker-publish.yml)

<!-- Project Info Badges -->
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://github.com/docdyhr/simplenote-mcp-server)
[![Version](https://img.shields.io/badge/version-1.6.0-blue.svg)](./CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/docker/v/docdyhr/simplenote-mcp-server?label=docker&color=blue)](https://hub.docker.com/r/docdyhr/simplenote-mcp-server)

<!-- Development & Quality Badges -->
[![MCP Server](https://img.shields.io/badge/MCP-Server-purple.svg)](https://github.com/modelcontextprotocol)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Smithery](https://smithery.ai/badge/@docdyhr/simplenote-mcp-server)](https://smithery.ai/server/@docdyhr/simplenote-mcp-server)

---

## 🔧 Features

- 📝 **Full Note Management**: Read, create, update, and delete Simplenote notes
- 🔍 **Advanced Search**: Boolean operators, phrase matching, tag and date filters
- ⚡ **High Performance**: In-memory caching with background synchronization
- 🔐 **Secure Authentication**: Token-based authentication via environment variables
- 🧩 **MCP Compatible**: Works with Claude Desktop and other MCP clients
- 🐳 **Docker Ready**: Full containerization with multi-stage builds and security hardening
- 📊 **Monitoring**: Optional performance metrics and monitoring

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

The fastest way to get started is using our pre-built Docker image:

```bash
# Pull and run the latest image
docker run -d \
  -e SIMPLENOTE_EMAIL=your.email@example.com \
  -e SIMPLENOTE_PASSWORD=your-password \
  -p 8000:8000 \
  docdyhr/simplenote-mcp-server:latest
```

Or use Docker Compose:

```bash
# Clone the repository for docker-compose.yml
git clone https://github.com/docdyhr/simplenote-mcp-server.git
cd simplenote-mcp-server

# Set environment variables
export SIMPLENOTE_EMAIL=your.email@example.com
export SIMPLENOTE_PASSWORD=your-password

# Run with Docker Compose
docker-compose up -d
```

### Option 2: Smithery (One-click install)

Install automatically via [Smithery](https://smithery.ai/server/@docdyhr/simplenote-mcp-server):

```bash
npx -y @smithery/cli install @docdyhr/simplenote-mcp-server --client claude
```

This method automatically configures Claude Desktop with the MCP server.

### Option 3: Traditional Python Install

```bash
git clone https://github.com/docdyhr/simplenote-mcp-server.git
cd simplenote-mcp-server
pip install -e .
simplenote-mcp-server
```

---

## 🐳 Docker Deployment

### Using Pre-built Images

The easiest way to use the server is with our pre-built Docker images:

```bash
# Pull the latest image
docker pull docdyhr/simplenote-mcp-server:latest

# Run with Docker
docker run -d \
  -e SIMPLENOTE_EMAIL=your.email@example.com \
  -e SIMPLENOTE_PASSWORD=your-password \
  -p 8000:8000 \
  docdyhr/simplenote-mcp-server:latest

# Or use Docker Compose
docker-compose up -d
```

Available tags:
- `latest` - Latest stable release
- `v1.6.0` - Specific version
- `main` - Latest development build

### Production Deployment

```bash
# Build and run the production container
docker-compose up -d

# Or build manually
docker build -t simplenote-mcp-server .
docker run -d \
  -e SIMPLENOTE_EMAIL=your.email@example.com \
  -e SIMPLENOTE_PASSWORD=your-password \
  -p 8000:8000 \
  simplenote-mcp-server
```

### Development with Docker

```bash
# Use the development compose file for live code mounting
docker-compose -f docker-compose.dev.yml up
```

### Docker Features

- **Multi-stage build** for optimized image size (346MB)
- **Multi-platform support**: `linux/amd64` and `linux/arm64`
- **Security hardening**: Non-root user, read-only filesystem, no new privileges
- **Health checks** and automatic restart policies
- **Resource limits**: 1 CPU, 512MB memory
- **Logging**: Persistent log volumes
- **Environment-based configuration**
- **CI/CD Pipeline**: Automated builds and publishing to Docker Hub
- **Security scanning**: Trivy vulnerability scanning on all images
- **Container signing**: Sigstore cosign signatures for supply chain security
- **Kubernetes ready**: Production-grade Helm chart with security hardening
- **Automated updates**: Dependabot for dependencies, auto-versioning workflows
- **Health monitoring**: Continuous health checks and alerting
- **Enterprise notifications**: Slack and email integration for CI/CD status

---

## ☸️ Kubernetes Deployment

### Using Helm (Recommended)

Deploy to Kubernetes with our production-ready Helm chart:

```bash
# Install from local chart
helm install my-simplenote ./helm/simplenote-mcp-server \
  --set simplenote.email="your-email@example.com" \
  --set simplenote.password="your-password"

# Or with external secrets (recommended for production)
helm install my-simplenote ./helm/simplenote-mcp-server \
  --set externalSecrets.enabled=true \
  --set externalSecrets.secretStore.name="vault-backend"
```

### Kubernetes Features

- **Security hardening**: Non-root user, read-only filesystem, dropped capabilities
- **Resource management**: CPU/memory limits and requests configured
- **Auto-scaling**: Horizontal Pod Autoscaler support
- **Health checks**: Liveness and readiness probes
- **External secrets**: Integration with external secret management
- **Service mesh ready**: Compatible with Istio and other service meshes

### Production Configuration

```yaml
# values.yaml for production
replicaCount: 3
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
resources:
  limits:
    cpu: 1000m
    memory: 512Mi
  requests:
    cpu: 500m
    memory: 256Mi
```

---

## ⚙️ Configuration

### Environment Variables

| Variable                | Required | Default | Description                                 |
| ----------------------- | -------- | ------- | ------------------------------------------- |
| `SIMPLENOTE_EMAIL`      | Yes      | -       | Your Simplenote account email               |
| `SIMPLENOTE_PASSWORD`   | Yes      | -       | Your Simplenote account password            |
| `SYNC_INTERVAL_SECONDS` | No       | 120     | Cache synchronization interval              |
| `LOG_LEVEL`             | No       | INFO    | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Claude Desktop Integration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "simplenote": {
      "description": "Access and manage your Simplenote notes",
      "command": "simplenote-mcp-server",
      "env": {
        "SIMPLENOTE_EMAIL": "your.email@example.com",
        "SIMPLENOTE_PASSWORD": "your-password"
      }
    }
  }
}
```

---

## 🔍 Advanced Search

Powerful search with boolean logic and filters:

```text
# Boolean operators
project AND meeting AND NOT cancelled

# Phrase matching
"action items" AND project

# Tag filtering
meeting tag:work tag:important

# Date ranges
project from:2023-01-01 to:2023-12-31

# Combined query
"status update" AND project tag:work from:2023-01-01 NOT cancelled
```

---

## 🛠️ Available Tools

| Tool           | Description                  | Parameters                                                 |
| -------------- | ---------------------------- | ---------------------------------------------------------- |
| `create_note`  | Create a new note            | `content`, `tags` (optional)                               |
| `update_note`  | Update an existing note      | `note_id`, `content`, `tags` (optional)                    |
| `delete_note`  | Move a note to trash         | `note_id`                                                  |
| `get_note`     | Get a note by ID             | `note_id`                                                  |
| `search_notes` | Advanced search with filters | `query`, `limit`, `offset`, `tags`, `from_date`, `to_date` |
| `add_tags`     | Add tags to a note           | `note_id`, `tags`                                          |
| `remove_tags`  | Remove tags from a note      | `note_id`, `tags`                                          |
| `replace_tags` | Replace all tags on a note   | `note_id`, `tags`                                          |

---

## 📊 Performance & Caching

- **In-memory caching** with background synchronization
- **Pagination support** for large note collections
- **Indexed lookups** for tags and content
- **Query result caching** for repeated searches
- **Optimized API usage** with minimal Simplenote calls

---

## 🧪 Testing & Evaluation

### MCP Evaluations ✅

**Status**: ✅ **WORKING** - Complete mcp-evals integration with TypeScript wrapper!

This project includes comprehensive evaluations using [mcp-evals](https://github.com/mclenhard/mcp-evals) to ensure reliability and performance:

```bash
# Setup evaluation environment
npm install
npm run validate:evals

# Run evaluation suites
npm run eval:smoke          # Quick smoke tests (2-3 minutes) ✅ VERIFIED
npm run eval:basic          # Standard evaluations (5-10 minutes)
npm run eval:comprehensive  # Full evaluation suite (15-30 minutes)
```

**Latest Test Results**: 4/5 tests passing excellently (avg 4.1/5):

- **Server Startup**: 4.6/5 ⭐ (Excellent)
- **Authentication**: 4.0/5 ⭐ (Good)  
- **Note Operations**: 3.8/5 ⭐ (Good)
- **Search**: 5.0/5 ⭐ (Perfect)
- **Error Handling**: 1.4/5 ⚠️ (Needs improvement)

#### Evaluation Types

- **Smoke Tests**: Basic functionality validation
- **CRUD Operations**: Note creation, reading, updating, deletion
- **Search & Filtering**: Boolean search, tag filtering, date ranges
- **Error Handling**: Authentication, network issues, edge cases
- **Performance**: Large datasets, concurrent operations
- **Security**: Input validation, authentication enforcement

#### Automated Testing

Evaluations run automatically on:

- **Pull Requests**: Smoke + basic tests
- **Releases**: Comprehensive evaluation suite
- **Manual Trigger**: Full test matrix with detailed reporting

The evaluations use OpenAI's GPT models to assess:

- **Accuracy**: Correctness of responses
- **Completeness**: Thoroughness of results
- **Relevance**: Response appropriateness
- **Clarity**: Response readability
- **Performance**: Operation efficiency

📁 See [`evals/README.md`](./evals/README.md) for detailed evaluation documentation.

### Traditional Testing

```bash
# Python unit tests
pytest

# Code quality checks
ruff check .
mypy simplenote_mcp
```

---

## 🛡️ Security

- **Token-based authentication** via environment variables
- **No hardcoded credentials** in Docker images
- **Security-hardened containers** with non-root users
- **Read-only filesystem** in production containers
- **Resource limits** to prevent abuse

---

## 🚨 Troubleshooting

### Common Issues

**Authentication Problems**:

- Verify `SIMPLENOTE_EMAIL` and `SIMPLENOTE_PASSWORD` are set correctly
- Check for typos in credentials

**Docker Issues**:

```bash
# Check container logs
docker-compose logs

# Restart services
docker-compose restart

# Rebuild if needed
docker-compose up --build
```

**Claude Desktop Connection**:

```bash
# Verify tools are available
./simplenote_mcp/scripts/verify_tools.sh

# Monitor logs
./simplenote_mcp/scripts/watch_logs.sh
```

### Diagnostic Commands

```bash
# Test connectivity
python simplenote_mcp/tests/test_mcp_client.py

# Check server status
./simplenote_mcp/scripts/check_server_pid.sh

# Clean up and restart
./simplenote_mcp/scripts/cleanup_servers.sh
```

---

## 📚 Development

### Quick Setup with mcp-evals

```bash
# One-command setup including evaluations
./setup-dev-env-with-evals.sh

# Or manual setup
git clone https://github.com/docdyhr/simplenote-mcp-server.git
cd simplenote-mcp-server
pip install -e ".[dev,test]"
npm install  # For mcp-evals
```

### Local Development

```bash
# Run the server
python simplenote_mcp_server.py

# Run Python tests
pytest

# Run mcp-evals
npm run eval:smoke    # Quick validation
npm run eval:basic    # Standard tests
npm run eval:all      # Full test suite

# Code quality
ruff check .
ruff format .
mypy simplenote_mcp
```

### Development Environment

The setup script creates:

- Python development environment with all dependencies
- Node.js environment for mcp-evals
- Example configuration files
- Pre-commit hooks
- Validation for all evaluation files

### Testing Strategy

1. **Unit Tests**: Traditional Python pytest for core logic
2. **Integration Tests**: MCP protocol compliance testing
3. **Smoke Tests**: Quick validation of basic functionality
4. **Evaluation Tests**: LLM-based assessment of real-world usage
5. **Performance Tests**: Load and stress testing

### Docker Development

```bash
# Development with live code reload
docker-compose -f docker-compose.dev.yml up

# Build and test
docker build -t simplenote-mcp-server:test .
docker run --rm simplenote-mcp-server:test --help
```

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP Example Servers](https://modelcontextprotocol.io/examples)

---

[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/docdyhr-simplenote-mcp-server-badge.png)](https://mseep.ai/app/docdyhr-simplenote-mcp-server)
