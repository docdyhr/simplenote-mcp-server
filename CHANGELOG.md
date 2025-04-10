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

## [1.0.0] - 2025-04-10

### Added
- In-memory cache implementation for faster note access 
- Background synchronization task for keeping notes up to date
- Support for filtering notes by tags in resource listing
- Comprehensive unit, integration, and performance tests
- Complete documentation with detailed installation and usage instructions
- Integration guide for Claude Desktop
- Caching mechanism explanation
- Advanced error recovery mechanisms
- Performance optimization for all operations
- Tag filtering for resource listing capability
- Proper type annotations throughout the code

### Changed
- Optimized resource listing for performance
- Enhanced error handling with better categorization and recovery
- Updated environment variable handling with comprehensive configuration options
- Improved logging with configurable levels (DEBUG, INFO, WARNING, ERROR)
- Support for structured JSON logging format
- Refined caching strategy for better memory usage
- Improved synchronization logic for more reliable updates

### Fixed
- Server startup issues with logging directory
- Circular import problem with version imports
- API parameter issues in the cache module
- Type errors in server implementation