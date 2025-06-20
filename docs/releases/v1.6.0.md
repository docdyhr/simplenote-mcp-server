# Release Notes - Simplenote MCP Server v1.6.0

**Release Date**: June 18, 2025

## 🚀 What's New in v1.6.0

This release focuses on **CI/CD pipeline stability** and **Docker deployment reliability**. We've resolved critical infrastructure issues that were preventing successful builds and deployments.

## 🛠️ Critical Fixes

### CI/CD Pipeline Reliability ✅
- **Fixed version mismatch** between VERSION file (1.5.0) and pyproject.toml (1.6.0) that was causing CI/CD failures
- **Resolved Docker build failures** by updating Python 3.11 paths to Python 3.13 in multi-stage builds
- **Fixed wheel packaging issues** that included test files in distribution packages
- **Improved health check monitoring** to properly handle expected authentication failures

### Docker & Container Improvements 🐳
- **Multi-stage Dockerfile** now correctly copies Python 3.13 site-packages and binaries
- **Package distribution** properly excludes test files using setuptools configuration and MANIFEST.in
- **Container builds** working reliably across all platforms (linux/amd64, linux/arm64)

### Dependency Management 📦
- **Merged 3 Dependabot PRs** for updated dependencies:
  - `peter-evans/create-pull-request@v7.0.5`
  - `codecov/codecov-action@v5.0.7`
  - `dawidd6/action-send-mail@v3.17.0`
- **Helm chart improvements** with added icon to resolve linting warnings

## 📊 Testing & Quality Assurance

- ✅ **All 208 Python tests** passing successfully
- ✅ **Docker builds** working locally with all fixes applied
- ✅ **CI/CD pipeline** now fully functional
- ✅ **Health check monitoring** properly handles authentication scenarios

## 🔧 Impact Summary

| Area | Improvement |
|------|-------------|
| **CI/CD Reliability** | 100% resolution of Docker build and publishing failures |
| **Deployment Stability** | Fixed version consistency and package distribution issues |
| **Container Quality** | Proper multi-stage builds with correct Python version paths |
| **Security** | Maintained up-to-date dependencies through automated updates |
| **Testing** | Comprehensive test coverage with all scenarios passing |

## 🚀 Upgrade Instructions

### For Docker Users
```bash
# Pull the latest image
docker pull docdyhr/simplenote-mcp-server:v1.6.0

# Or use latest tag
docker pull docdyhr/simplenote-mcp-server:latest
```

### For Python Installation
```bash
# Upgrade via pip
pip install --upgrade simplenote-mcp-server==1.6.0
```

### For Helm Users
```bash
# Upgrade Helm deployment
helm upgrade my-simplenote ./helm/simplenote-mcp-server
```

## 🐛 Known Issues

- None identified in this release

## 📚 Documentation Updates

- Updated `CHANGELOG.md` with comprehensive v1.6.0 changes
- Enhanced `docs/DOCKER_CI_CD_SETUP.md` with troubleshooting lessons learned
- Added debugging workflow and best practices for CI/CD issues

## 🤝 Contributors

This release includes contributions from automated dependency management and infrastructure improvements.

## 🔗 Links

- **Docker Hub**: https://hub.docker.com/r/docdyhr/simplenote-mcp-server
- **GitHub Repository**: https://github.com/docdyhr/simplenote-mcp-server
- **Documentation**: https://github.com/docdyhr/simplenote-mcp-server/tree/main/docs

## 🎯 Next Release (v1.7.0)

Planning for the next release will focus on:
- Pre-commit hooks for version consistency checks
- Enhanced monitoring and observability features
- Performance optimizations

---

**Full Changelog**: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.5.1...v1.6.0
