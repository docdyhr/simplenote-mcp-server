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

## [1.1.0] - 2025-04-12

### Added
- Dedicated tag management tools:
  - `add_tags`: Add additional tags to a note without modifying content
  - `remove_tags`: Remove specific tags from a note
  - `replace_tags`: Replace all tags on a note with a new set
- Comprehensive test suite for tag management functionality
- Updated documentation to reflect new capabilities

### Changed
- Expanded README with detailed descriptions of the tag management tools
- Updated TODO.md to reflect completion of tag management feature
- Created and documented a strategic ROADMAP.md for future enhancements

## [1.2.0] - 2025-04-13

### Added
- Docker support with a new Dockerfile for containerized deployment
- Smithery configuration for simplified cloud deployment
- Installation instructions for Smithery platform
- Smithery badge in README for enhanced visibility
- Retry mechanisms with exponential backoff for API operations
- Timeout handling for background sync to prevent hanging

### Improved
- Code quality improvements:
  - Modern type annotations (replaced typing.Dict, typing.List with built-in types)
  - Better docstring formatting with consistent style
  - Improved exception handling with centralized error messages
  - Added parameter and return type annotations
  - Alphabetically sorted __all__ lists
- Enhanced cleanup script with better process termination
- More resilient background sync with better recovery from failures
- Graceful handling of network connectivity issues

### Fixed
- Bug in email logging when credentials are not provided
- Server crashes during background sync when network errors occur
- Unstable behavior when Simplenote API is unreachable
- Server crashes when MCP client times out during slow API operations
- Initialization failure when Simplenote API is slow to respond

## [1.3.0] - 2025-04-14

### Added
- Debug logging configuration in pytest.ini for better test visibility
- Detailed debug logging throughout the search operation
- Thread-safe caching with proper lock implementation

### Improved
- Enhanced search algorithm with better relevance scoring
- Prioritization of title matches in search results
- More descriptive tool documentation for search functionality
- More robust cache initialization with direct API fallback
- Extended timeout for better handling of slow API responses

### Fixed
- Search functionality in Claude Desktop returning empty results
- Thread safety issues with concurrent cache access
- Cache initialization failures with Simplenote API
- Empty search results when API responses are slow

## [1.4.0] - 2025-04-14

### Added
- Advanced search functionality with:
  - Boolean operators (AND, OR, NOT)
  - Phrase matching with quotes
  - Tag filtering with `tag:` syntax
  - Date range filtering
- New search engine architecture:
  - Query parser for tokenizing search expressions
  - Boolean expression evaluation engine
  - Relevance scoring based on content matches, title matches, and recency
- Comprehensive test suite for advanced search capabilities

### Improved
- Enhanced search results with better scoring and ranking
- More flexible search syntax allowing complex queries
- Better handling of empty queries with tag or date filters
- Better error reporting for invalid search queries
- More descriptive search results including relevance information

### Fixed
- Issues with empty search results when using tag filters
- Date range filtering not working correctly
- Thread safety issues in search operations
