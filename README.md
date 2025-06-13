[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/docdyhr-simplenote-mcp-server-badge.png)](https://mseep.ai/app/docdyhr-simplenote-mcp-server)

# Simplenote MCP Server

![Simplenote MCP Server Logo](assets/logo.png)

A lightweight MCP server that integrates [Simplenote](https://simplenote.com/) with [Claude Desktop](https://github.com/johnsmith9982/claude-desktop) using the [MCP Python SDK](https://github.com/johnsmith9982/mcp-python-sdk).

This allows Claude Desktop to interact with your Simplenote notes as a memory backend or content source.

<!-- Status & Build Badges -->
[![CI/CD Pipeline](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/ci.yml)
[![Tests](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/python-tests.yml/badge.svg?branch=main)](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/python-tests.yml)
[![Code Quality](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/code-quality.yml/badge.svg?branch=main)](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/code-quality.yml)
[![Security](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/security.yml)

<!-- Project Info Badges -->
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://github.com/docdyhr/simplenote-mcp-server)
[![Version](https://img.shields.io/badge/version-1.5.0-blue.svg)](./CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://github.com/docdyhr/simplenote-mcp-server)

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

The fastest way to get started is using Docker:

```bash
# Clone the repository
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
- **Security hardening**: Non-root user, read-only filesystem, no new privileges
- **Health checks** and automatic restart policies
- **Resource limits**: 1 CPU, 512MB memory
- **Logging**: Persistent log volumes
- **Environment-based configuration**

---

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SIMPLENOTE_EMAIL` | Yes | - | Your Simplenote account email |
| `SIMPLENOTE_PASSWORD` | Yes | - | Your Simplenote account password |
| `SYNC_INTERVAL_SECONDS` | No | 120 | Cache synchronization interval |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

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

| Tool | Description | Parameters |
|------|-------------|------------|
| `create_note` | Create a new note | `content`, `tags` (optional) |
| `update_note` | Update an existing note | `note_id`, `content`, `tags` (optional) |
| `delete_note` | Move a note to trash | `note_id` |
| `get_note` | Get a note by ID | `note_id` |
| `search_notes` | Advanced search with filters | `query`, `limit`, `offset`, `tags`, `from_date`, `to_date` |
| `add_tags` | Add tags to a note | `note_id`, `tags` |
| `remove_tags` | Remove tags from a note | `note_id`, `tags` |
| `replace_tags` | Replace all tags on a note | `note_id`, `tags` |

---

## 📊 Performance & Caching

- **In-memory caching** with background synchronization
- **Pagination support** for large note collections
- **Indexed lookups** for tags and content
- **Query result caching** for repeated searches
- **Optimized API usage** with minimal Simplenote calls

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

### Local Development

```bash
# Clone and setup
git clone https://github.com/docdyhr/simplenote-mcp-server.git
cd simplenote-mcp-server
pip install -e ".[dev,test]"

# Run tests
pytest

# Code quality
ruff check .
ruff format .
mypy simplenote_mcp
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
