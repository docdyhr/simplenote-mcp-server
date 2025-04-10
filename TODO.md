# TODO: Simplenote MCP Server Development Plan

This file outlines the tasks needed to implement the Simplenote MCP Server according to the requirements in [PRD.md](./PRD.md).

## 1. Project Structure & Framework Transition

- [ ] **Transition to FastMCP/FastAPI**
  - [ ] Add FastMCP and FastAPI as dependencies
  - [ ] Update package structure to accommodate new framework
  - [ ] Create server implementation using FastMCP/FastAPI

- [ ] **Entry Points**
  - [ ] Create uvicorn-based server entry point
  - [ ] Update `setup.py` and `pyproject.toml` for FastMCP requirements
  - [ ] Create `run_server.sh` script for easy setup and startup

## 2. Authentication & Security

- [ ] **Environment Configuration**
  - [ ] Implement `.env` file support 
  - [ ] Add SERVER_PORT, SERVER_AUTH_TOKEN, and SYNC_INTERVAL_SECONDS environment variables

- [ ] **Bearer Token Authentication**
  - [ ] Implement FastAPI dependency for token verification
  - [ ] Add authorization middleware
  - [ ] Create bearer token validation logic

- [ ] **CORS Configuration**
  - [ ] Implement CORS middleware for FastAPI
  - [ ] Configure for development and production

## 3. MCP Endpoint Implementation

- [ ] **MCP Discovery**
  - [ ] Implement `/api/v1/discovery` endpoint
  - [ ] Define FastMCP resources and tools for Simplenote

- [ ] **Resource Endpoints**
  - [ ] GET `/context/simplenote/notes` - List notes with filtering
    - [ ] Support tag filtering
    - [ ] Support limit and sort parameters
  - [ ] GET `/context/simplenote/notes/{note_id}` - Get note by ID
  - [ ] GET `/context/simplenote/search?query=...` - Search notes

- [ ] **Tool Endpoints**
  - [ ] POST `/context/simplenote/notes` - Create note
  - [ ] PUT `/context/simplenote/notes/{note_id}` - Update note
  - [ ] DELETE `/context/simplenote/notes/{note_id}` - Trash note

## 4. Data Models & Validation

- [ ] **Define Pydantic Models**
  - [ ] NoteResource model (with id, content, creationDate, modificationDate, tags)
  - [ ] NoteCreateRequest model
  - [ ] NoteUpdateRequest model
  - [ ] SearchResponse model

- [ ] **Response Serialization**
  - [ ] Implement FastAPI response models
  - [ ] Set up JSON serialization with proper metadata

## 5. Caching & Synchronization

- [ ] **In-Memory Cache**
  - [ ] Design note cache data structure
  - [ ] Implement cache manager class

- [ ] **Initial Data Loading**
  - [ ] Implement FastAPI startup event for initial load
  - [ ] Fetch all notes on server start

- [ ] **Background Synchronization**
  - [ ] Create asyncio background task for sync
  - [ ] Implement `index_since` mechanism
  - [ ] Set up periodic sync with configurable interval

- [ ] **Cache Operations**
  - [ ] Immediate cache updates after API operations
  - [ ] Efficient filtering and search within cache

## 6. Error Handling & Logging

- [ ] **Exception Handlers**
  - [ ] Create FastAPI exception handlers
  - [ ] Map API errors to appropriate HTTP status codes

- [ ] **Logging**
  - [ ] Set up structured logging
  - [ ] Add debug/info/error level logging throughout the codebase
  - [ ] Log API operations and synchronization events

## 7. Testing

- [ ] **Unit Tests**
  - [ ] Test each endpoint
  - [ ] Test cache operations
  - [ ] Test authentication

- [ ] **Integration Tests**
  - [ ] Test end-to-end flows with Simplenote API
  - [ ] Test caching and synchronization

## 8. Documentation

- [ ] **Update README.md**
  - [ ] Update installation instructions
  - [ ] Document environment variables
  - [ ] Document API endpoints

- [ ] **Create Integration Guide**
  - [ ] Guide for Claude Desktop integration
  - [ ] Authentication setup
  - [ ] Example usage patterns

## 9. Future Enhancements (V2.0+)

- [ ] **Tag Management**
  - [ ] Add/remove tags from notes
  - [ ] Create/delete tags

- [ ] **Permanent Deletion**
  - [ ] Implement permanent delete endpoint

- [ ] **Advanced Search**
  - [ ] Boolean logic in search
  - [ ] Tag-specific search

- [ ] **Pagination**
  - [ ] Add pagination to List/Search endpoints

- [ ] **Performance Monitoring**
  - [ ] Integrate Prometheus client for metrics
  - [ ] Track cache stats, response times, API calls

- [ ] **Docker Packaging**
  - [ ] Create Dockerfile
  - [ ] Document Docker deployment

## 10. Project Management

- [ ] **Version 1.0 Release**
  - [ ] Ensure all functional requirements met
  - [ ] Performance testing
  - [ ] Documentation finalized
  - [ ] Manual testing with Claude Desktop