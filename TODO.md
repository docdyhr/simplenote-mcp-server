# TODO: Simplenote MCP Server Development Plan

This file outlines the tasks needed to implement the Simplenote MCP Server according to the requirements in [PRD.md](./PRD.md).

## 1. Server Enhancements

- [x] **Improve Existing MCP Implementation**
  - [x] Enhance error handling and logging
  - [x] Add better documentation for existing functionality
  - [x] Optimize performance for resource listing and retrieval

- [x] **Environment Configuration**
  - [x] Add support for SYNC_INTERVAL_SECONDS environment variable
  - [x] Improve logging with configurable verbosity levels
  - [x] Add more robust error recovery mechanisms

## 2. Caching Implementation

- [x] **In-Memory Cache**
  - [x] Design note cache data structure
  - [x] Implement cache manager class
  - [x] Add cache state logging and statistics

- [x] **Initial Data Loading**
  - [x] Optimize initial note loading process
  - [x] Add progress reporting during initial load
  - [x] Handle large collections efficiently

- [x] **Background Synchronization**
  - [x] Implement background task for periodic sync
  - [x] Use `index_since` mechanism for efficient updates
  - [x] Handle sync failures gracefully with retry logic

## 3. Resource Capabilities

- [x] **Enhanced Resource Listing**
  - [x] Add support for filtering by tags
  - [x] Include note tags in resource metadata 
  - [x] Support limiting the number of returned notes
  - [x] Add sorting options if possible

- [x] **Improved Resource Reading**
  - [x] Enhance error handling for note retrieval
  - [x] Add more robust metadata extraction
  - [x] Optimize for performance with caching

## 4. Tool Capabilities

- [x] **Search Functionality**
  - [x] Enhance search tool to use the in-memory cache
  - [x] Implement case-insensitive keyword search
  - [x] Support combined content and title searching
  - [x] Return comprehensive metadata with search results

- [x] **Note Management Tools**
  - [x] Improve create_note with better tag handling
  - [x] Enhance update_note with validation
  - [x] Refine delete_note to use trash_note properly
  - [x] Add proper error handling for all operations

## 5. Data Representation

- [x] **MCP Types Implementation**
  - [x] Ensure correct usage of mcp.types structures
  - [x] Standardize note representation format
  - [x] Add complete metadata to responses

## 6. Error Handling & Logging

- [x] **Enhanced Error Handling**
  - [x] Improve error logging and categorization
  - [x] Add recoverable vs. non-recoverable error handling
  - [x] Create clearer error messages for users

- [x] **Logging System**
  - [x] Add structured logging throughout the code
  - [x] Create separate log files for different concerns
  - [x] Implement log rotation to prevent large files

## 7. Testing

- [x] **Unit Tests**
  - [x] Test cache operations
  - [x] Test Simplenote API interaction
  - [x] Test error handling

- [x] **Integration Tests**
  - [x] Test end-to-end flows with Simplenote API
  - [x] Test caching and synchronization
  - [x] Test with Claude Desktop interaction

## 8. Documentation

- [x] **Update README.md**
  - [x] Update installation instructions
  - [x] Document environment variables
  - [x] Explain the caching mechanism
  - [x] Add troubleshooting section

- [x] **Create Integration Guide**
  - [x] Guide for Claude Desktop integration
  - [x] Example usage patterns
  - [x] Best practices for using the server

## 9. Future Enhancements (V2.0+)

- [x] **Tag Management**
  - [x] Add/remove tags from notes

- [ ] **Permanent Deletion**
  - [ ] Implement permanent delete functionality

- [x] **Advanced Search** (Completed in v1.4.0)
  - [x] Boolean logic in search (AND, OR, NOT operators)
  - [x] Tag-specific search with tag: syntax
  - [x] Date range filtering with date: syntax
  - [x] Phrase matching with quoted phrases

- [ ] **Pagination**
  - [ ] Add pagination for large note collections

- [ ] **Performance Monitoring**
  - [ ] Track cache stats, response times, API calls

- [x] **Docker Packaging**
  - [x] Create Dockerfile
  - [x] Document Docker deployment

## 11. Code Quality Improvements

### Immediate Improvements

- [x] **Modern Type Annotations**
  - [x] Replace `typing.Dict`, `typing.List`, `typing.Set` with built-in `dict`, `list`, `set`
  - [x] Run `ruff check --select=UP006 --fix .` to autofix

- [x] **Docstring Formatting**
  - [x] Add missing periods at end of docstrings
  - [x] Add blank lines after section headers (Args:, Returns:, etc.)
  - [x] Use consistent formatting across all docstrings
  - [x] Run `ruff check --select=D400,D415,D413 --fix .`

- [x] **Exception Handling**
  - [x] Store error messages in variables instead of using string literals
  - [x] Improve exception hierarchy and reusability

### Medium-term Improvements

- [x] **Function Return Type Annotations**
  - [x] Add return type annotations to all public functions
  - [x] Use `-> None` for functions that don't return anything

- [x] **Sort `__all__` Lists**
  - [x] Keep `__all__` lists alphabetically sorted
  - [x] Run `ruff check --select=RUF022 --fix .`

- [ ] **Upgrade Test Assertions**
  - [ ] Use pytest-style assertions for better error messages
  - [ ] Add more descriptive assertion messages

- [x] **Function Parameter Type Annotations**
  - [x] Add type annotations for function parameters
  - [x] Improve static type checking support

### Longer-term Improvements

- [ ] **Refactor Complex Functions**
  - [ ] Break down `handle_call_tool` into smaller, focused functions
  - [ ] Improve code organization and readability

- [ ] **Reduce Code Duplication**
  - [ ] Extract repeated tag management patterns into helper functions
  - [ ] Create a `get_note_by_id` helper for cache/API lookups

- [ ] **Structured Logging**
  - [ ] Use structured logging more consistently
  - [ ] Improve log organization and searchability

- [ ] **Error Categorization**
  - [ ] Refine error categorization system
  - [ ] Make errors more specific and actionable

### Infrastructure Improvements

- [ ] **Configuration for Linting Rules**
  - [ ] Add a `.ruff.toml` configuration file
  - [ ] Define project-specific linting rules

- [ ] **Pre-commit Hooks**
  - [ ] Set up pre-commit hooks for automatic linting
  - [ ] Include black, ruff, and mypy in the hooks

- [ ] **CI Pipeline Enhancement**
  - [ ] Add dedicated linting step to CI pipeline
  - [ ] Generate code quality trend reports

## 10. Project Management

- [x] **Version 1.0 Release**
  - [x] Ensure all functional requirements met
  - [x] Performance testing
  - [x] Documentation finalized
  - [x] Manual testing with Claude Desktop

All requirements for version 1.0 have been completed! 🎉