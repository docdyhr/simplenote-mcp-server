# Changelog

All notable changes to the Simplenote MCP Server project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **Critical**: Resolved Claude Desktop timeout by making cache initialization truly async
  - Run blocking Simplenote API calls in thread pool executor to avoid blocking event loop
  - Reduced server startup time from 55+ seconds to < 1 second
  - Fixed `anyio.BrokenResourceError` during shutdown
  - Fixed unawaited coroutine warnings in log monitor
  - Allow graceful operation with empty cache during background loading
  - See `CLAUDE_DESKTOP_TIMEOUT_FIX.md` for detailed technical analysis

## [1.8.1] - 2025-10-26

### Added
- Comprehensive quality automation and project improvements
- Added comprehensive cache coverage tests (14% → 83% coverage for cache module)
- Test performance script for startup validation
- Enhanced documentation for troubleshooting

### Changed
- Updated TODO.md with 2025-10-20 maintenance actions
- Upgraded actions/setup-node from v5 to v6 in CI/CD workflows

### Fixed
- Corrected Python 3.14 site-packages path in Docker builds

### Dependencies
- Upgraded MCP library from 1.14.0 to 1.18.0
- Upgraded Ruff from 0.14.0 to 0.14.1
- Upgraded pytest from 8.4.1 to 8.4.2
- Upgraded pytest-asyncio from 1.1.0 to 1.2.0
- Upgraded pytest-cov from 6.2.1 to 7.0.0
- Upgraded mypy from 1.18.1 to 1.18.2
- Upgraded coverage from 7.8.2 to 7.11.0
- Multiple dependency updates via Dependabot (pydantic, uvicorn, idna, etc.)

## [1.8.0] - 2025-10-19

### Changed
- Major dependency refresh to latest stable versions
- Improved metrics collection and monitoring

### Dependencies
- Updated multiple production and development dependencies to latest versions

## [1.7.0] - 2025-10-14

### Added
- CodeQL security analysis integration
- Enhanced CI/CD pipeline with security scanning
- Improved Docker multi-stage builds

### Fixed
- Resolved CodeQL and Trivy scanner failures in CI
- Fixed integration test failures in CI offline mode
- Updated workflow badge references in README
- Installed build package for CI and local testing

### Changed
- Upgraded Docker base image to Python 3.14-slim
- Upgraded GitHub Actions dependencies

## [1.6.0] - 2025-09

### Added
- MCP evaluations framework integration
- Comprehensive test suite with 700+ tests
- Performance monitoring and metrics collection
- Security hardening with multiple scanning tools
- HTTP endpoints for health and metrics
- Advanced search with boolean operators
- Tag filtering and pagination support

### Changed
- Improved cache performance with background synchronization
- Enhanced error handling and taxonomy
- Better logging and diagnostics

### Security
- Added Bandit security scanning
- Added pip-audit vulnerability scanning
- Added Trivy container scanning
- Implemented rate limiting and DoS protection
- Enhanced input validation and sanitization

## [1.5.0] - 2025-08

### Added
- Docker and Kubernetes deployment support
- Helm charts for production deployments
- Background cache synchronization
- Rate limiting middleware
- Security monitoring and alerting

### Changed
- Refactored server architecture for better modularity
- Improved error handling with custom error taxonomy
- Enhanced documentation with deployment guides

## [1.4.0] - 2025-07

### Added
- MCP protocol 2024-11-05 support
- Prompts capability for note templates
- Resources capability for note listing
- Tools capability for note management
- Basic caching implementation

### Changed
- Migrated to MCP Python SDK 1.0+
- Updated authentication to use environment variables
- Improved note search functionality

## [1.3.0] - 2025-06

### Added
- Tag management support
- Note filtering by tags
- Pagination for note lists

### Changed
- Improved note content parsing
- Better error messages

## [1.2.0] - 2025-05

### Added
- Note update functionality
- Note deletion (trash) functionality
- Search query support

### Changed
- Enhanced note listing with sorting
- Improved connection handling

## [1.1.0] - 2025-04

### Added
- Note creation capability
- Basic note listing
- Initial MCP integration

### Changed
- Refactored to use Simplenote Python library
- Improved logging

## [1.0.0] - 2025-03

### Added
- Initial release
- Basic Simplenote authentication
- Read-only note access
- Simple MCP server implementation

---

## Version History Summary

- **1.8.1** (Current) - Quality improvements, dependency updates, Claude Desktop fix
- **1.8.0** - Major dependency refresh
- **1.7.0** - Security enhancements, CI/CD improvements
- **1.6.0** - Comprehensive testing, monitoring, advanced features
- **1.5.0** - Docker/Kubernetes support, production features
- **1.4.0** - Full MCP protocol implementation
- **1.3.0** - Tag management
- **1.2.0** - Note editing capabilities
- **1.1.0** - Note creation
- **1.0.0** - Initial release

[Unreleased]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.8.1...HEAD
[1.8.1]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.8.0...v1.8.1
[1.8.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.7.0...v1.8.0
[1.7.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.6.0...v1.7.0
[1.6.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/docdyhr/simplenote-mcp-server/releases/tag/v1.0.0
