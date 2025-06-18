# Docker CI/CD Setup Guide

This guide helps you configure the Docker CI/CD pipeline for the Simplenote MCP Server.

## Prerequisites

1. Docker Hub account
2. Repository access on GitHub
3. Docker Hub repository created under `docdyhr` organization

## Setting up GitHub Secrets

### Required Secrets

Navigate to your GitHub repository → Settings → Secrets and variables → Actions, and add:

1. **DOCKER_USERNAME**
   - Value: `docdyhr` (or your Docker Hub username)
   - Description: Docker Hub username for authentication

2. **DOCKER_TOKEN**
   - Value: Your Docker Hub Access Token
   - Description: Docker Hub access token with read/write permissions

### Creating Docker Hub Access Token

1. Log in to [Docker Hub](https://hub.docker.com)
2. Navigate to [Account Settings → Security](https://hub.docker.com/settings/security)
3. Click "New Access Token"
4. Provide a descriptive name (e.g., "GitHub Actions - simplenote-mcp-server")
5. Select permissions:
   - Read
   - Write
   - Delete (optional, for cleanup)
6. Click "Generate"
7. Copy the token immediately (it won't be shown again)
8. Add it as `DOCKER_TOKEN` in GitHub Secrets

## Workflow Overview

The Docker publishing workflow (`docker-publish.yml`) provides:

### Features

- **Multi-platform builds**: Supports `linux/amd64` and `linux/arm64`
- **Automatic tagging**:
  - `latest`: Always points to the latest main branch build
  - `vX.Y.Z`: Semantic version tags (e.g., `v1.0.0`)
  - `X.Y`: Major.minor tags (e.g., `1.0`)
  - `X`: Major version tags (e.g., `1`)
  - `main`: Latest main branch build
  - `YYYYMMDD-sha`: Date-prefixed SHA tags
- **Build caching**: Uses GitHub Actions cache for faster builds
- **Security scanning**: Trivy vulnerability scanning on published images
- **Build attestation**: Generates provenance for supply chain security
- **Pull request testing**: Builds but doesn't push on PRs

### Workflow Triggers

- **Push to main**: Builds and publishes with `latest` and `main` tags
- **Version tags**: Push tags like `v1.0.0` to trigger versioned releases
- **Pull requests**: Builds images for testing without publishing
- **Manual dispatch**: Trigger manually from GitHub Actions tab

## Local Development vs Production

### Using Pre-built Images (Production)

The default `docker-compose.yml` uses pre-built images from Docker Hub:

```bash
# Uses docdyhr/simplenote-mcp-server:latest
docker-compose up -d
```

### Building Locally (Development)

To build from local source code:

```bash
# Use the build compose file
docker-compose -f docker-compose.build.yml up -d

# Or for development with live code mounting
docker-compose -f docker-compose.dev.yml up
```

## Using Published Images

### Docker Hub Repository

Images are published to: `docker.io/docdyhr/simplenote-mcp-server`

### Pulling Images

```bash
# Latest version
docker pull docdyhr/simplenote-mcp-server:latest

# Specific version
docker pull docdyhr/simplenote-mcp-server:v1.0.0

# Specific platform
docker pull --platform linux/arm64 docdyhr/simplenote-mcp-server:latest
```

### Running with Docker

```bash
# Using docker run
docker run -e SIMPLENOTE_EMAIL="your-email" \
           -e SIMPLENOTE_PASSWORD="your-password" \
           docdyhr/simplenote-mcp-server:latest

# Using docker-compose
docker-compose up -d
```

## Monitoring Builds

### GitHub Actions

- View build status: Actions tab in GitHub repository
- Build logs: Click on individual workflow runs
- Security alerts: Security tab for vulnerability scan results

### Docker Hub

- View published tags: https://hub.docker.com/r/docdyhr/simplenote-mcp-server/tags
- Image details: Click on individual tags for metadata

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Verify `DOCKER_USERNAME` and `DOCKER_TOKEN` secrets
   - Ensure token has read/write permissions
   - Check token hasn't expired

2. **Build Failures**
   - Check Dockerfile syntax
   - Verify all required files are present
   - Review build logs in GitHub Actions

3. **Platform Build Issues**
   - QEMU setup might fail on some runners
   - Consider building platforms separately if issues persist

### Security Scan Failures

Trivy scans may find vulnerabilities. To address:

1. Update base images in Dockerfile
2. Update dependencies in `pyproject.toml`
3. Use specific version tags instead of `latest` for base images
4. Consider adding `.trivyignore` for false positives

## Best Practices

1. **Versioning**
   - Use semantic versioning for tags
   - Tag releases with `v` prefix (e.g., `v1.0.0`)
   - Update version in `pyproject.toml` before tagging

2. **Security**
   - Regularly update base images
   - Monitor security scan results
   - Use minimal base images (e.g., `python:3.11-slim`)
   - Run as non-root user (already configured)

3. **Performance**
   - Leverage build cache
   - Use multi-stage builds (already implemented)
   - Minimize layer count
   - Order Dockerfile commands by change frequency

## Manual Deployment

If you need to build and push manually:

```bash
# Build for multiple platforms
docker buildx build --platform linux/amd64,linux/arm64 \
  -t docdyhr/simplenote-mcp-server:latest \
  -t docdyhr/simplenote-mcp-server:v1.0.0 \
  --push .

# Build for single platform
docker build -t docdyhr/simplenote-mcp-server:latest .
docker push docdyhr/simplenote-mcp-server:latest
```

## Future Enhancements

- [ ] Add container signing with cosign
- [ ] Implement automated dependency updates
- [ ] Add health check endpoint monitoring
- [ ] Create Helm chart for Kubernetes deployment
- [ ] Add notification webhooks for build status
