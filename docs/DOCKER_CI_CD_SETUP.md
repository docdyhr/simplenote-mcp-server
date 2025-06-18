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

## Implemented Enhancements

- ✅ **Container signing with cosign**: All published images are cryptographically signed
- ✅ **Automated dependency updates**: Dependabot configured for Python, GitHub Actions, and Docker
- ✅ **Health check endpoint monitoring**: Automated health checks every 15 minutes
- ✅ **Helm chart for Kubernetes deployment**: Full Helm chart with security hardening
- ✅ **Notification webhooks**: Support for Slack and email notifications
- ✅ **Linting/test stage pre-publish**: Code quality checks before Docker builds
- ✅ **Automatic version updates**: README and documentation auto-updated on releases

## Enterprise Features

### Container Signing

All Docker images are signed with Sigstore cosign for supply chain security:

```bash
# Verify image signature
cosign verify docdyhr/simplenote-mcp-server:latest
```

### Kubernetes Deployment

Deploy using Helm:

```bash
# Add Helm repository (when published)
helm repo add simplenote-mcp https://docdyhr.github.io/simplenote-mcp-server

# Install with custom values
helm install my-simplenote simplenote-mcp/simplenote-mcp-server \
  --set simplenote.email="your-email@example.com" \
  --set simplenote.password="your-password"
```

### Health Monitoring

- **Automated health checks**: Runs weekly on Sunday mornings (optimized resource usage)
- **Container startup verification**: Tests image integrity
- **Security scanning**: Regular vulnerability monitoring
- **Multi-tag monitoring**: Tests both `latest` and `main` tags
- **Release validation**: Automatic checks on new releases
- **Manual triggering**: Available via workflow_dispatch

### Notifications

**Status**: ✅ **CONFIGURED AND INTEGRATED**

The notification system is now fully integrated into all CI/CD workflows:

#### Email Notifications Setup ✅

**Required GitHub Secrets**:
- `NOTIFICATION_EMAIL` - Gmail address for sending/receiving notifications
- `EMAIL_PASSWORD` - Gmail app password for SMTP authentication  

**Integration Status**:
- ✅ Docker CI/CD Pipeline (`docker-publish.yml`) - sends email on completion
- ✅ Health Check Monitoring (`health-check.yml`) - sends email on status change
- ✅ Test Notifications (`test-notifications.yml`) - manual testing workflow

#### How Email Notifications Work

1. **Centralized System**: All workflows use `.github/workflows/notifications.yml`
2. **Email Provider**: Gmail SMTP (smtp.gmail.com:587)
3. **Content**: HTML-formatted emails with workflow details, links, and status
4. **Triggers**: Automatic on workflow completion (success/failure)

#### Email Content Includes
- 📧 **Subject**: Workflow name and status with emoji
- 🔗 **Links**: Direct links to workflow run and commit
- 📋 **Details**: Repository, branch, commit SHA
- 💬 **Message**: Custom status information per workflow

#### Slack Notifications (Optional)

```yaml
# To enable Slack notifications, add:
slack_enabled: true

# Add GitHub secret:
# - SLACK_WEBHOOK_URL
```

#### Manual Testing

```bash
# Test email notifications manually
gh workflow run test-notifications.yml --ref main -f test_type=success
```

#### Configuration Example

```yaml
# In workflow files:
notify:
  uses: ./.github/workflows/notifications.yml
  with:
    status: success
    workflow_name: "My Workflow"
    message: "Custom status message"
    email_enabled: true
    slack_enabled: false
  secrets:
    NOTIFICATION_EMAIL: ${{ secrets.NOTIFICATION_EMAIL }}
    EMAIL_PASSWORD: ${{ secrets.EMAIL_PASSWORD }}
```

### Dependency Management

Automated updates via Dependabot:
- **Python dependencies**: Weekly on Sundays
- **GitHub Actions**: Weekly on Mondays  
- **Docker base images**: Weekly on Tuesdays
- **Grouped updates**: Production and development dependencies

## Lessons Learned - CI/CD Troubleshooting

### Common CI/CD Issues and Solutions

#### Version Consistency Problems
**Issue**: Version mismatch between VERSION file and pyproject.toml causing CI/CD failures
- **Symptom**: "❌ Version mismatch detected!" in CI logs
- **Root Cause**: VERSION file (1.5.0) != pyproject.toml version (1.6.0)
- **Solution**: Ensure VERSION file and pyproject.toml version field always match
- **Prevention**: Add version consistency check to pre-commit hooks

#### Docker Build Path Issues  
**Issue**: Dockerfile failing with "python3.11/site-packages: not found" 
- **Symptom**: Multi-stage build copy commands failing during production stage
- **Root Cause**: Python version mismatch between base image (3.13) and copy paths (3.11)
- **Solution**: Update all Python paths to match base image version
- **Prevention**: Use variables for Python version in Dockerfile

#### Wheel Package Contamination
**Issue**: "W009: Wheel contains multiple toplevel library entries" during CI
- **Symptom**: Tests directory included in wheel distribution
- **Root Cause**: setuptools including test files by default
- **Solution**: Add explicit exclusions in pyproject.toml and MANIFEST.in
- **Prevention**: Test wheel contents locally before pushing

#### Health Check False Positives
**Issue**: Health check monitoring failing with dummy credentials
- **Symptom**: Expected authentication failures treated as errors
- **Root Cause**: Health check logic not accounting for credential validation
- **Solution**: Update logic to expect and validate auth error messages
- **Prevention**: Use realistic test scenarios in health checks

### Debugging Workflow

1. **Check CI/CD Logs**: Always start with GitHub Actions workflow logs
2. **Test Locally**: Reproduce Docker builds locally before pushing
3. **Verify Versions**: Ensure consistency across VERSION, pyproject.toml, and README
4. **Check Paths**: Validate all file paths in Docker multi-stage builds
5. **Test Wheel**: Check wheel contents with `unzip -l dist/*.whl`

### Best Practices Learned

- **Version Management**: Keep VERSION file as single source of truth
- **Docker Paths**: Use Python version variables in Dockerfiles
- **Package Distribution**: Explicitly exclude test files from wheels
- **Health Monitoring**: Design health checks for realistic failure scenarios
- **Local Testing**: Always test Docker builds locally before CI/CD

## Future Enhancements

- [ ] Add OCI artifact attestations
- [ ] Implement artifact caching for faster builds
- [ ] Add GitOps deployment pipelines
- [ ] Create operator for Kubernetes
- [ ] Add metrics and observability stack
- [ ] Add pre-commit hook for version consistency checks
