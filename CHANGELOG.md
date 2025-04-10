# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-04-10

### Added
- Initial project structure with `mcp` package integration
- Core MCP server functionality for Simplenote interactions
- Resource capabilities for listing and reading notes
- Tool capabilities for creating, updating, and searching notes
- Basic logging and error handling
- Helper scripts for running and managing the server

## [0.2.0] - 2025-04-10

### Added
- Organized project into a proper package structure
  - `/simplenote_mcp/server/` - Server code
  - `/simplenote_mcp/scripts/` - Helper scripts
  - `/simplenote_mcp/tests/` - Test utilities
  - `/simplenote_mcp/logs/` - Log files directory
- Added path resolution in helper scripts for better reliability
- Created new test client script for verifying functionality
- Added `verify_tools.sh` for checking tool registration

### Changed
- Updated file paths in all scripts to use the new structure
- Improved server module to use proper Python imports
- Enhanced logging to store logs in a dedicated directory
- Updated package configuration in setup.py and pyproject.toml

### Fixed
- Fixed logging path issues by supporting both new and legacy locations
- Corrected tool verification to work with the current log structure

## [0.3.0] - Unreleased

### Added
- In-memory cache implementation for faster note access
- Background synchronization task for keeping notes up to date
- Support for filtering notes by tags
- Improved error handling and logging
- More comprehensive metadata in note representations
- Enhanced search capabilities with in-memory cache

### Changed
- Optimized resource listing for performance
- Updated environment variable handling for better configuration options
- Improved validation for note operations

## [1.0.0] - Unreleased

### Added
- Complete test suite with unit and integration tests
- Comprehensive documentation with installation and usage instructions
- Integration guide for Claude Desktop
- Advanced error recovery mechanisms
- Performance optimizations for large note collections

### Changed
- Enhanced user experience with more informative messages
- Refined caching strategy for better memory usage
- Improved synchronization logic for more reliable updates