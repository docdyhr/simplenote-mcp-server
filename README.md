<div align="right">

<a href="https://railway.com?referralCode=QhjuBc">

  <img width="160" src="https://raw.githubusercontent.com/docdyhr/.github/main/assets/railway-corner-v2@2x.png" alt="Deploy on Railway — $20 free credits">

</a>

</div>

# Simplenote MCP Server

![Simplenote MCP Server Logo](assets/logo.png)

A lightweight MCP server that integrates [Simplenote](https://simplenote.com/) with [Claude Desktop](https://github.com/johnsmith9982/claude-desktop) using the [MCP Python SDK](https://github.com/johnsmith9982/mcp-python-sdk).

This allows Claude Desktop to interact with your Simplenote notes as a memory backend or content source.

<!-- Status & Build Badges -->
[![CI/CD Pipeline](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/unified-ci.yml/badge.svg?branch=main)](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/unified-ci.yml)
[![Security](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/security.yml)

<!-- Project Info Badges -->
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://github.com/docdyhr/simplenote-mcp-server)
[![Version](https://img.shields.io/badge/version-1.17.5-blue.svg)](./CHANGELOG.md)
[![Test Coverage](https://img.shields.io/badge/coverage-77%25-brightgreen)](./htmlcov/index.html)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<!-- Download & Stats Badges -->
[![PyPI Downloads](https://img.shields.io/pypi/dm/simplenote-mcp-server?label=PyPI%20downloads)](https://pypi.org/project/simplenote-mcp-server/)
[![Docker Pulls](https://img.shields.io/docker/pulls/docdyhr/simplenote-mcp-server?label=Docker%20pulls)](https://hub.docker.com/r/docdyhr/simplenote-mcp-server)
[![GitHub Stars](https://img.shields.io/github/stars/docdyhr/simplenote-mcp-server?style=social)](https://github.com/docdyhr/simplenote-mcp-server)

<!-- Development & Quality Badges -->
[![MCP Server](https://img.shields.io/badge/MCP-Server-purple.svg)](https://github.com/modelcontextprotocol)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Smithery](https://smithery.ai/badge/@docdyhr/simplenote-mcp-server)](https://smithery.ai/server/@docdyhr/simplenote-mcp-server)

[![Verified on MseeP](https://mseep.ai/badge.svg)](https://mseep.ai/app/docdyhr-simplenote-mcp-server)
---

## What's New

**30 Tools — Full Bear Parity + Simplenote Differentiators + Claude Companion Tools + Vault Encryption**

**Vault — opt-in client-side note encryption**: Simplenote has no encryption at rest. `create_note`/`update_note` now accept `encrypt: true`, and `encrypt_note`/`decrypt_note` convert existing notes — bodies become AES-256-GCM ciphertext before they ever reach Simplenote's API. See [docs/security/encryption-design.md](docs/security/encryption-design.md).

MCP Resources and Prompts hardened for the working-memory companion use case:

- **Fixed**: `list_resources`/`read_resource` were silently dropping tag/date/pagination metadata via non-schema fields — now attached through the MCP spec's `_meta` extension field, the correct mechanism.
- **`session-handoff` MCP Prompt**: scaffolds the Session Continuity workflow (`get_or_create_note` + `add_text` with a `Status:`/`Next:`/`Blockers:` format) for cross-session context handoff.

Irreversible-deletion tools with mandatory safety guards:

- **`permanent_delete_note`**: Permanently destroy a single note; requires `confirm=true`; dry-run preview by default
- **`empty_trash`**: Permanently delete all trashed notes; defaults to `dry_run=true` (preview); requires `dry_run=false` AND `confirm=true`
- **1334 tests passing**, 79%+ coverage, zero linting/type errors

See the [CHANGELOG](./CHANGELOG.md) and [ROADMAP.md](ROADMAP.md) for complete details.

### v1.17.0

- **`search_notes` async fix**: Boolean AND queries no longer hang the server; search now runs in a thread-pool executor with a 30 s timeout
- **Substring pre-filter**: searching "test" now correctly returns notes containing "testing", "tested", etc.
- Real-engine integration test suite added; import error in test helpers fixed

### v1.16.0

- **`publish_note`**: Publish a note to a public URL — unique to Simplenote MCP; returns `public_url`
- **`unpublish_note`**: Remove a note from public access; no-op if already unpublished

See the [CHANGELOG](./CHANGELOG.md) for complete details.

---

## 🔧 Features

- 📝 **Full Note Management**: Read, create, update, and delete Simplenote notes
- 🔍 **Advanced Search**: Boolean operators, phrase matching, tag and date filters
- ⚡ **High Performance**: In-memory caching with background synchronization
- 🔐 **Secure Authentication**: Token-based authentication via environment variables
- 🔑 **Vault Encryption**: Opt-in client-side AES-256-GCM encryption for sensitive notes — Simplenote itself has no encryption at rest
- 🧩 **MCP Compatible**: Works with Claude Desktop and other MCP clients
- 🐳 **Docker Ready**: Full containerization with multi-stage builds and security hardening
- 📊 **Monitoring**: Optional HTTP endpoints for health, readiness, and metrics
- 🧪 **Robust Testing**: Comprehensive test suite with 1334 tests and continuous integration
- 🔒 **Security Hardened**: Regular security scanning with Bandit, pip-audit, and dependency checks

---

## 🚀 Quick Start

### Prerequisites

- Simplenote account (create one at [simplenote.com](https://simplenote.com/))
- Python 3.10+ (for non-Docker installs) or Docker

### Option 1: Docker (Recommended)

The fastest way to get started is using our pre-built Docker image:

```bash
# Pull and run the latest image
docker run -d \
  --name simplenote-mcp \
  -e SIMPLENOTE_EMAIL=your.email@example.com \
  -e SIMPLENOTE_PASSWORD=your-password \
  -e MCP_TRANSPORT=http \
  -e MCP_HTTP_HOST=0.0.0.0 \
  -e MCP_HTTP_AUTH_TOKEN=your-random-secret-token \
  -p 8000:8000 \
  docdyhr/simplenote-mcp-server:latest
```

`MCP_HTTP_AUTH_TOKEN` is required whenever `MCP_HTTP_HOST` is anything other
than `127.0.0.1`/`localhost` — the server refuses to start otherwise (see the
Security section below). Without `MCP_TRANSPORT=http`, the server runs over
stdio by default and nothing listens on the published port at all.

**Docker Health Checks:** health monitoring is a *separate* HTTP endpoint
from the MCP protocol port above — it's off by default and must be enabled
explicitly with `-e ENABLE_HTTP_ENDPOINT=true -e HTTP_HOST=0.0.0.0 -p 8080:8080`
(Docker's `-p` mapping forwards to the container's network interface, not its
loopback, so `HTTP_HOST` must be `0.0.0.0` for the published port to actually
reach it — the `127.0.0.1` default only works if you're calling these
endpoints from another process *inside the same container*):
- Health: `http://localhost:8080/health`
- Readiness: `http://localhost:8080/ready`
- Metrics: `http://localhost:8080/metrics` (Prometheus format)

The server refuses to start if `HTTP_HOST` is non-loopback and no
`HTTP_ENDPOINT_AUTH_TOKEN` is set, since these endpoints would otherwise be
reachable by anyone who can reach the port. Set a bearer token (checked via
`Authorization: Bearer <token>`, same mechanism as `MCP_HTTP_AUTH_TOKEN`
above) if you need a non-loopback bind — loopback callers are always
trusted regardless, so this never breaks a local health check. Prefer
keeping it loopback-only and publishing with `-p 127.0.0.1:8080:8080`
instead of `-p 8080:8080` when you can.

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

## 🗂 Documentation Map & Archives

- Start with `docs/DOCUMENTATION_GUIDE.md` for a curated tour of user, developer, and operations docs plus maintenance checklists.
- Historical project summaries now live under `docs/archive/2025/`, keeping the repository root focused on active roadmaps and guides.
- Need something fast? Run `rg "<topic>" docs/` or jump to `docs/index.md` for the MkDocs-style table of contents.

---

## 🐳 Docker Deployment

### Container Features

- **Multi-stage builds** for optimized image size
- **Security hardening** with non-root user and minimal attack surface
- **Health monitoring** endpoints built-in
- **Resource limits** and proper signal handling
- **Volume support** for persistent data

### Using Pre-built Images

The easiest way to use the server is with our pre-built Docker images:

```bash
# Pull the latest image
docker pull docdyhr/simplenote-mcp-server:latest

# Run with Docker (see Quick Start above for the required MCP_HTTP_* env vars)
docker run -d \
  -e SIMPLENOTE_EMAIL=your.email@example.com \
  -e SIMPLENOTE_PASSWORD=your-password \
  -e MCP_TRANSPORT=http \
  -e MCP_HTTP_HOST=0.0.0.0 \
  -e MCP_HTTP_AUTH_TOKEN=your-random-secret-token \
  -p 8000:8000 \
  docdyhr/simplenote-mcp-server:latest

# Or use Docker Compose (set MCP_HTTP_AUTH_TOKEN in your environment/.env first)
docker-compose up -d
```

Available tags:

- `latest` - Latest stable release
- `v1.17.5` - Specific version
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
  -e MCP_TRANSPORT=http \
  -e MCP_HTTP_HOST=0.0.0.0 \
  -e MCP_HTTP_AUTH_TOKEN=your-random-secret-token \
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

| Variable                | Required | Default | Description                                              |
| ----------------------- | -------- | ------- | -------------------------------------------------------- |
| `SIMPLENOTE_EMAIL`      | Yes      | -       | Your Simplenote account email                            |
| `SIMPLENOTE_PASSWORD`   | Yes      | -       | Your Simplenote account password                         |
| `SYNC_INTERVAL_SECONDS` | No       | 120     | Cache synchronization interval in seconds                |
| `CACHE_MAX_SIZE`        | No       | 10000   | Max notes held in memory — set ≥ your total note count   |
| `LOG_LEVEL`             | No       | INFO    | Logging level (DEBUG, INFO, WARNING, ERROR)              |
| `SIMPLENOTE_OFFLINE_MODE` | No     | false   | Skip API calls; used for testing without credentials     |
| `MCP_TRANSPORT`         | No       | stdio   | `stdio` or `http` — the MCP protocol transport            |
| `MCP_HTTP_HOST`         | No       | 127.0.0.1 | Bind host when `MCP_TRANSPORT=http`                     |
| `MCP_HTTP_AUTH_TOKEN`   | Conditional | -    | Bearer token; **required** if `MCP_HTTP_HOST` is non-loopback |
| `MCP_HTTP_ALLOWED_HOSTS` | No      | -       | Comma-separated allowlist for DNS-rebinding protection    |
| `MCP_HTTP_ALLOWED_ORIGINS` | No   | -       | Comma-separated Origin allowlist (used with the above)    |
| `ENABLE_HTTP_ENDPOINT`  | No       | false   | Enable the separate `/health`, `/ready`, `/metrics` server |
| `HTTP_HOST`             | No       | 127.0.0.1 | Bind host for the monitoring endpoint above              |
| `HTTP_PORT`             | No       | 8080    | Port for the monitoring endpoint above                    |
| `HTTP_ENDPOINT_AUTH_TOKEN` | Conditional | -  | Bearer token; **required** if `HTTP_HOST` is non-loopback |

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
        "SIMPLENOTE_PASSWORD": "your-password",
        "CACHE_MAX_SIZE": "10000"
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

| Tool                      | Description                                              | Parameters                                                                                              |
| ------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `create_note`             | Create a new note                                        | `content`, `tags` (optional)                                                                            |
| `update_note`             | Replace full note content (destructive)                  | `note_id`, `content`, `tags` (optional)                                                                 |
| `delete_note`             | Soft-delete: move note to Trash                          | `note_id`                                                                                               |
| `restore_note`            | Untrash a note — move it back from Trash                 | `note_id`                                                                                               |
| `permanent_delete_note`   | Irreversibly destroy a single note (requires `confirm=true`) | `note_id`, `confirm`                                                                                |
| `empty_trash`             | Permanently delete all trashed notes (dry-run by default) | `dry_run` (default `true`), `confirm` (default `false`)                                               |
| `get_note`                | Get a note by ID with full content and metadata          | `note_id`                                                                                               |
| `add_text`                | Append or prepend text without overwriting               | `note_id`, `text`, `position` (`"end"` \| `"beginning"`)                                               |
| `search_notes`            | Full-text search with filters and pagination             | `query`, `limit`, `offset`, `tags`, `from_date`, `to_date`, `created_after`, `modified_after`, `pinned`, `fuzzy`, `sort_by` |
| `add_tags`                | Add tags to a note                                       | `note_id`, `tags`                                                                                       |
| `remove_tags`             | Remove specific tags from a note                         | `note_id`, `tags`                                                                                       |
| `replace_tags`            | Replace all tags on a note                               | `note_id`, `tags`                                                                                       |
| `list_tags`               | List all tags with note counts                           | `sort_by` (`"alpha"` \| `"count"`)                                                                      |
| `rename_tag`              | Rename a tag across all notes atomically                 | `old_tag`, `new_tag`, `dry_run` (optional)                                                              |
| `get_note_versions`       | List version history for a note                          | `note_id`                                                                                               |
| `restore_version`         | Roll back a note to a previous version                   | `note_id`, `version_number`                                                                             |
| `get_or_create_note`      | Atomic find-or-create by title                           | `title`, `tags` (optional), `default_content` (optional)                                               |
| `append_to_daily_note`    | Append a timestamped entry to today's note               | `text`, `tags` (optional)                                                                               |
| `replace_section`         | Replace one Markdown section without touching others     | `note_id`, `header`, `content`                                                                          |
| `find_untagged_notes`     | Find notes with no tags                                  | `limit` (optional)                                                                                      |
| `bulk_tag`                | Apply tags to multiple notes in one call                 | `note_ids`, `tags`                                                                                      |
| `export_notes`            | Export notes to Markdown or JSON                         | `format`, `tags` (optional), `query` (optional)                                                         |
| `find_and_merge_duplicates` | Detect and merge duplicate notes                       | `dry_run` (optional), `similarity_threshold` (optional)                                                 |
| `get_server_info`           | Server version, author, and runtime debug info         | *(no parameters)*                                                                                       |

---

## 📊 Performance & Caching

- **In-memory caching** with background synchronization
- **Pagination support** for large note collections
- **Indexed lookups** for tags and content
- **Query result caching** for repeated searches
- **Optimized API usage** with minimal Simplenote calls

---

## 🎯 Recent Improvements

### ✅ January 2025 - Performance & Code Quality

**Critical Bug Fix**:
- **Fixed Claude Desktop timeout** - Reduced startup time from 55+ seconds to < 1 second (98% improvement)
- Implemented thread pool execution for blocking Simplenote API calls
- Made cache initialization truly non-blocking with background loading
- Resolved `anyio.BrokenResourceError` during shutdown

**Code Refactoring - Phase 1 Complete**:
- **Cache module complexity reduced**: 5 high-complexity functions (CC >= 15) → 0 (100% reduction)
- **Maintainability improved**: Cache MI from 12.7 → 16.2 (+28%)
- Extracted 23 helper methods for better code organization
- All 670 tests passing with 67% cache coverage maintained
- See `REFACTORING_PHASE1_COMPLETE.md` for details

**Documentation Enhancements**:
- Added comprehensive `CHANGELOG.md` with complete version history
- Created `TESTING_CLAUDE_DESKTOP.md` for user testing guide
- Added code complexity analysis tools (`check_complexity.py`)
- Documented refactoring plan and completion reports

**Quality Tools**:
- Integrated Radon for automated complexity analysis
- Baseline metrics: 22 functions CC >= 15 (down from 28)
- Average Maintainability Index: 57.9 (maintained)
- Zero diagnostics errors, all quality gates passing

### ✅ September 2025 - Quality & Reliability Enhancements

### ✅ Quality & Reliability Enhancements

**Test Suite Stabilization**: 
- Fixed test isolation issues that caused intermittent failures
- Improved test cleanup with proper timeout handling
- Enhanced fixture management for better test reliability
- Achieved consistent test results across individual and suite runs

**CI/CD Pipeline Optimization**:
- Consolidated 28 workflows down to 16 active workflows
- Implemented unified monitoring workflow combining security, health, and badge checks
- Improved test coverage reporting with realistic 15.6% baseline
- Enhanced Docker build validation and security scanning

**Code Quality Improvements**:
- All linting (Ruff), formatting, and type checking (MyPy) now pass consistently  
- Zero high-severity security vulnerabilities (verified with Bandit, pip-audit, safety)
- Standardized code formatting and pre-commit hooks configuration
- Enhanced error handling and user-facing error messages

### 🔧 Developer Experience

**Improved Testing**:
- 724 comprehensive tests covering core functionality
- Function-scoped fixtures for better test isolation  
- Realistic coverage baseline established (15.6%)
- Streamlined test execution with proper cleanup

**Enhanced Documentation**:
- Updated deployment guides with current Docker setup
- Improved health monitoring endpoint documentation
- Added troubleshooting guides for common issues
- Current status and roadmap documentation

**Container Improvements**:
- Multi-stage Docker builds for optimized image size
- Built-in health monitoring endpoints (`/health`, `/ready`, `/metrics`)
- Enhanced security hardening with non-root user
- Improved signal handling and graceful shutdown

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
- **MCP HTTP transport is fail-closed by default**: `MCP_TRANSPORT=http`
  refuses to start on any non-loopback `MCP_HTTP_HOST` unless
  `MCP_HTTP_AUTH_TOKEN` is set (a shared bearer secret, checked via
  constant-time comparison). Loopback binds (`127.0.0.1`/`localhost`) work
  without a token, matching stdio's local-process trust level. Set
  `MCP_HTTP_ALLOWED_HOSTS`/`MCP_HTTP_ALLOWED_ORIGINS` (comma-separated) to
  enable DNS-rebinding protection for non-loopback binds. This is intended
  for private networks (behind a VPN/Tailscale/SSH tunnel) — a static
  shared token has none of OAuth's revocation/audit/expiry properties, so
  avoid exposing it directly to the public internet even with a token set.

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

### Running MCP Evaluations

#### Docker Method (Recommended)
Due to potential permission issues with tsx, we recommend running MCP evaluations in Docker:

```bash
# Run smoke tests
./scripts/run-evals-docker.sh smoke

# Run basic evaluations
./scripts/run-evals-docker.sh basic

# Run comprehensive evaluations
./scripts/run-evals-docker.sh comprehensive

# Run all evaluations
./scripts/run-evals-docker.sh all
```

#### Direct Method (if permissions allow)
```bash
npm run eval:smoke
npm run eval:basic
npm run eval:comprehensive
npm run eval:all
```

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

## ⭐ Support the Project

If you find this project helpful, please consider giving it a star on GitHub! Your support helps:

- 🚀 **Increase visibility** for other developers who might benefit from this tool
- 💪 **Motivate continued development** and maintenance
- 📈 **Build community** around the Model Context Protocol ecosystem
- 🛡️ **Validate trust** through community engagement

**[⭐ Star this repository](https://github.com/docdyhr/simplenote-mcp-server)** — it takes just one click and means a lot!

---

[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/docdyhr-simplenote-mcp-server-badge.png)](https://mseep.ai/app/docdyhr-simplenote-mcp-server)
