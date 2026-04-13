# Simplenote MCP Server

[![Docker Hub](https://img.shields.io/docker/pulls/docdyhr/simplenote-mcp-server.svg)](https://hub.docker.com/r/docdyhr/simplenote-mcp-server)
[![Docker Image Size](https://img.shields.io/docker/image-size/docdyhr/simplenote-mcp-server/latest)](https://hub.docker.com/r/docdyhr/simplenote-mcp-server)
[![Security Rating](https://img.shields.io/badge/security-A+-green)](https://hub.docker.com/r/docdyhr/simplenote-mcp-server)

A **Model Context Protocol (MCP) server** that provides seamless integration with [Simplenote](https://simplenote.com) for note management, search, and organization capabilities. Built with enterprise-grade security and performance optimization.

## 🚀 Quick Start

### Using Docker Compose (Recommended)

```yaml
services:
  simplenote-mcp:
    image: docdyhr/simplenote-mcp-server:latest
    container_name: simplenote-mcp-server
    restart: unless-stopped
    environment:
      - SIMPLENOTE_EMAIL=your-email@example.com
      - SIMPLENOTE_PASSWORD=your-password
    ports:
      - "8000:8000"
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=100m
```

### Using Docker Run

```bash
docker run -d \
  --name simplenote-mcp-server \
  --restart unless-stopped \
  -e SIMPLENOTE_EMAIL=your-email@example.com \
  -e SIMPLENOTE_PASSWORD=your-password \
  -p 8000:8000 \
  --security-opt no-new-privileges:true \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=100m \
  docdyhr/simplenote-mcp-server:latest
```

## 🔧 Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SIMPLENOTE_EMAIL` | Your Simplenote account email | `user@example.com` |
| `SIMPLENOTE_PASSWORD` | Your Simplenote account password | `your-secure-password` |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SIMPLENOTE_OFFLINE_MODE` | `false` | Run in offline mode for testing |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `SYNC_INTERVAL` | `120` | Cache sync interval in seconds |

## 🏗️ Container Features

### 🛡️ Security Hardened
- ✅ **Non-root user** - Runs as dedicated `mcp` user
- ✅ **Read-only filesystem** - Immutable container runtime
- ✅ **No privilege escalation** - Security-first design
- ✅ **Minimal attack surface** - Distroless-style base image
- ✅ **Signed images** - Cosign keyless signing
- ✅ **Vulnerability scanned** - Trivy + Docker Scout

### ⚡ Performance Optimized
- 📦 **97MB image size** - Multi-stage build optimization
- 🚀 **Fast startup** - Intelligent caching and lazy loading
- 💾 **Memory efficient** - <256MB runtime memory usage
- 🔄 **Health checks** - Built-in container health monitoring

### 🏢 Production Ready
- 🌐 **Multi-architecture** - AMD64 and ARM64 support
- 📊 **Observability** - Comprehensive logging and metrics
- 🔄 **Graceful shutdown** - Proper signal handling
- 📈 **Resource limits** - CPU and memory constraints
- 🔒 **SLSA attestation** - Supply chain security

## 🌟 Capabilities

### Note Management
- 📝 **Create notes** - Rich text content with tags
- ✏️ **Update notes** - Modify content and metadata
- 🗑️ **Delete notes** - Safe note removal
- 📋 **List notes** - Paginated note browsing
- 🔍 **Search notes** - Advanced search with filters

### Tag Management
- 🏷️ **Add tags** - Organize notes with tags
- 🗂️ **Remove tags** - Clean up tag assignments
- 🔄 **Replace tags** - Bulk tag operations
- 📊 **Tag statistics** - Usage analytics

### Advanced Search
- 🔎 **Full-text search** - Content and title searching
- 📅 **Date filtering** - Time-based note retrieval
- 🏷️ **Tag filtering** - Category-based search
- 🔤 **Boolean operators** - AND, OR, NOT queries
- 📝 **Phrase matching** - Exact phrase searches

## 🏥 Health Checks

The container includes built-in health monitoring:

```bash
# Check container health
docker exec simplenote-mcp-server python -c "import simplenote_mcp; print('✅ Healthy')"

# View health status
docker inspect --format='{{.State.Health.Status}}' simplenote-mcp-server
```

## 📊 Usage Examples

### Basic MCP Client Integration

```python
import asyncio
from mcp import StdioServerManager

async def main():
    async with StdioServerManager("docker", [
        "run", "--rm", "-i",
        "-e", "SIMPLENOTE_EMAIL=your-email@example.com",
        "-e", "SIMPLENOTE_PASSWORD=your-password",
        "docdyhr/simplenote-mcp-server:latest"
    ]) as server:
        # List available tools
        tools = await server.list_tools()
        print(f"Available tools: {[tool.name for tool in tools.tools]}")
        
        # Search notes
        result = await server.call_tool("search_notes", {"query": "important"})
        print(f"Search results: {result}")
```

### Claude Desktop Integration

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "simplenote": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--env-file", "/path/to/simplenote.env",
        "docdyhr/simplenote-mcp-server:latest"
      ]
    }
  }
}
```

## 🔄 Updates & Versions

### Available Tags

| Tag | Description | Stability |
|-----|-------------|-----------|
| `latest` | Latest stable release | 🟢 Stable |
| `1.6.0` | Specific version | 🟢 Stable |
| `1.6` | Minor version | 🟢 Stable |
| `1` | Major version | 🟢 Stable |

### Automatic Updates

Images are automatically rebuilt weekly with security updates every Sunday at 2 AM UTC.

```bash
# Update to latest version
docker pull docdyhr/simplenote-mcp-server:latest
docker-compose up -d  # Recreate containers
```

## 🔐 Security

### Vulnerability Scanning
- **Trivy**: Container and filesystem scanning
- **Docker Scout**: Advanced vulnerability analysis
- **Automated scans**: Every build and weekly rebuilds

### Image Signing
All images are signed with Cosign for supply chain security:

```bash
# Verify image signature
cosign verify docdyhr/simplenote-mcp-server:latest
```

### SLSA Attestation
Build provenance attestations available for compliance:

```bash
# View build attestation
cosign verify-attestation docdyhr/simplenote-mcp-server:latest
```

## 🆘 Troubleshooting

### Common Issues

#### Authentication Errors
```bash
# Check credentials
docker logs simplenote-mcp-server | grep -i auth

# Verify environment variables
docker exec simplenote-mcp-server env | grep SIMPLENOTE
```

#### Connection Issues
```bash
# Test network connectivity
docker exec simplenote-mcp-server curl -I https://app.simplenote.com

# Check container health
docker exec simplenote-mcp-server python -c "import simplenote_mcp; print('OK')"
```

#### Performance Issues
```bash
# Monitor resource usage
docker stats simplenote-mcp-server

# Check memory limits
docker inspect simplenote-mcp-server | jq '.[0].HostConfig.Memory'
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
docker run --rm -it \
  -e SIMPLENOTE_EMAIL=your-email@example.com \
  -e SIMPLENOTE_PASSWORD=your-password \
  -e LOG_LEVEL=DEBUG \
  docdyhr/simplenote-mcp-server:latest
```

## 📚 Documentation

- **Full Documentation**: [GitHub Repository](https://github.com/docdyhr/simplenote-mcp-server)
- **API Reference**: [Tools and Resources Guide](https://github.com/docdyhr/simplenote-mcp-server#tools-and-resources)
- **Configuration Guide**: [Setup Instructions](https://github.com/docdyhr/simplenote-mcp-server#configuration)
- **Development Guide**: [Contributing](https://github.com/docdyhr/simplenote-mcp-server/blob/main/CONTRIBUTING.md)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/docdyhr/simplenote-mcp-server/blob/main/LICENSE) file for details.

## 🤝 Support

- **Issues**: [GitHub Issues](https://github.com/docdyhr/simplenote-mcp-server/issues)
- **Discussions**: [GitHub Discussions](https://github.com/docdyhr/simplenote-mcp-server/discussions)
- **Security**: [Security Policy](https://github.com/docdyhr/simplenote-mcp-server/security)

---

**Maintained by**: [Thomas Juul Dyhr](https://github.com/docdyhr)  
**Source Code**: [GitHub Repository](https://github.com/docdyhr/simplenote-mcp-server)  
**Container Registry**: [Docker Hub](https://hub.docker.com/r/docdyhr/simplenote-mcp-server)
