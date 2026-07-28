# Server API

This document provides technical documentation for the Simplenote MCP Server API.

## Overview

The Simplenote MCP Server implements the Model Context Protocol (MCP) to provide seamless integration between Simplenote and MCP clients like Claude Desktop. The server exposes tools for note management and resources for note discovery.

## Server Class

::: simplenote_mcp.server.server
    options:
      show_source: true
      heading_level: 3

## Core Components

### Authentication

The server handles authentication with Simplenote using email and password credentials:

```python
from simplenote_mcp.server.server import run_main

# The server is configured through environment variables
# SIMPLENOTE_EMAIL and SIMPLENOTE_PASSWORD
```

### Configuration

Server configuration is managed through environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SIMPLENOTE_EMAIL` | Required | Simplenote account email |
| `SIMPLENOTE_PASSWORD` | Required | Simplenote account password |
| `LOG_LEVEL` | `INFO` | Logging level |
| `CACHE_SIZE` | `1000` | Maximum cached notes |
| `CACHE_TTL` | `300` | Cache TTL in seconds |
| `SYNC_INTERVAL` | `60` | Sync interval in seconds |

## Tools

The server provides the following MCP tools:

### Note Management Tools

#### create_note

Creates a new note in Simplenote.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "content": {
      "type": "string",
      "description": "The content of the note"
    },
    "tags": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Tags to assign to the note"
    }
  },
  "required": ["content"]
}
```

**Returns:**
```json
{
  "note_id": "string",
  "message": "Note created successfully"
}
```

#### update_note

Updates an existing note's content or tags.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "note_id": {
      "type": "string",
      "description": "The ID of the note to update"
    },
    "content": {
      "type": "string",
      "description": "New content for the note"
    },
    "tags": {
      "type": "array",
      "items": {"type": "string"},
      "description": "New tags for the note"
    }
  },
  "required": ["note_id"]
}
```

#### delete_note

Deletes a note from Simplenote.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "note_id": {
      "type": "string",
      "description": "The ID of the note to delete"
    }
  },
  "required": ["note_id"]
}
```

#### get_note

Retrieves a specific note by ID.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "note_id": {
      "type": "string",
      "description": "The ID of the note to retrieve"
    }
  },
  "required": ["note_id"]
}
```

### Search Tools

#### search_notes

Advanced search through notes with support for boolean operators and filtering.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Search query with optional boolean operators"
    },
    "tags": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Filter by specific tags"
    },
    "limit": {
      "type": "integer",
      "default": 20,
      "description": "Maximum number of results"
    },
    "include_deleted": {
      "type": "boolean",
      "default": false,
      "description": "Include deleted notes in results"
    }
  },
  "required": ["query"]
}
```

**Search Features:**
- Boolean operators: `AND`, `OR`, `NOT`
- Phrase matching with quotes: `"exact phrase"`
- Tag filtering
- Wildcard support with `*`

#### list_tags

Lists all available tags from notes.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "limit": {
      "type": "integer",
      "default": 100,
      "description": "Maximum number of tags to return"
    }
  }
}
```

#### get_notes_by_tag

Retrieves all notes with a specific tag.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "tag": {
      "type": "string",
      "description": "The tag to search for"
    },
    "limit": {
      "type": "integer",
      "default": 50,
      "description": "Maximum number of results"
    }
  },
  "required": ["tag"]
}
```

### Utility Tools

#### get_note_count

Returns the total number of notes in the account.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {}
}
```

#### sync_notes

Forces synchronization with Simplenote to get latest changes.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {}
}
```

## Resources

The server exposes notes as MCP resources for discovery and access.

### Resource Schema

Each note resource follows this structure:

```json
{
  "uri": "simplenote://note/{note_id}",
  "name": "Note Title or Preview",
  "description": "First few lines of note content",
  "mimeType": "text/plain"
}
```

### Resource URIs

Resources use the `simplenote://` URI scheme:

- `simplenote://note/{note_id}` - Individual note
- `simplenote://tag/{tag_name}` - Notes with specific tag
- `simplenote://search/{query}` - Search results

## Error Handling

The server implements comprehensive error handling:

### Common Error Types

#### AuthenticationError
Raised when Simplenote credentials are invalid or expired.

```python
{"error": "AuthenticationError", "message": "Invalid email or password", "code": 401}
```

#### NoteNotFoundError
Raised when a requested note doesn't exist.

```python
{
    "error": "NoteNotFoundError",
    "message": "Note with ID 'abc123' not found",
    "code": 404,
}
```

#### RateLimitError
Raised when Simplenote API rate limits are exceeded.

```python
{
    "error": "RateLimitError",
    "message": "Rate limit exceeded, please try again later",
    "code": 429,
}
```

#### NetworkError
Raised when network connectivity issues occur.

```python
{"error": "NetworkError", "message": "Failed to connect to Simplenote API", "code": 503}
```

## Caching System

The server implements intelligent caching for improved performance:

### Cache Configuration

```python
cache_config = {
    "size": 1000,  # Maximum cached notes
    "ttl": 300,  # Time-to-live in seconds
    "strategy": "lru",  # Least Recently Used eviction
}
```

### Cache Behavior

- **Read-through**: Automatically caches notes when accessed
- **Write-through**: Updates cache when notes are modified
- **TTL-based**: Automatically expires stale entries
- **LRU eviction**: Removes least recently used notes when full

## Performance Considerations

### Optimization Strategies

1. **Bulk Operations**: Use batch APIs when available
2. **Selective Sync**: Only sync modified notes
3. **Lazy Loading**: Load note content on demand
4. **Request Coalescing**: Combine multiple requests

### Rate Limiting

The server respects Simplenote's rate limits:

- **Authentication**: 10 requests per minute
- **Note Operations**: 100 requests per minute
- **Search**: 50 requests per minute

### Memory Management

```python
# Configure memory usage
memory_config = {
    "cache_size": 1000,  # Notes in memory
    "max_content_size": 1024 * 1024,  # 1MB per note
    "cleanup_interval": 300,  # Cleanup every 5 minutes
}
```

## Security Features

### Credential Protection

- Credentials stored in environment variables only
- No credential logging or persistence
- Automatic credential validation

### API Security

- HTTPS-only communication with Simplenote
- Request signing and validation
- Automatic session management

### Data Privacy

- Local caching with configurable retention
- No third-party data sharing
- Secure credential handling

## Development API

For developers extending the server:

### Custom Tool Registration

```python
from simplenote_mcp.server import SimplenoteServer

server = SimplenoteServer()


@server.tool("custom_tool")
async def custom_tool(args: dict) -> dict:
    """Custom tool implementation."""
    return {"result": "success"}
```

### Event Hooks

```python
@server.on_note_created
async def on_note_created(note_id: str, note_data: dict):
    """Called when a note is created."""
    pass


@server.on_note_updated
async def on_note_updated(note_id: str, note_data: dict):
    """Called when a note is updated."""
    pass
```

### Custom Resource Providers

```python
@server.resource_provider("custom://")
async def custom_resource_provider(uri: str) -> dict:
    """Custom resource provider."""
    return {"uri": uri, "name": "Custom Resource", "content": "Custom content"}
```

## API Reference Links

- [Cache System](cache.md) - Caching implementation details
- [Search Engine](search.md) - Advanced search functionality
- [Configuration](../configuration.md) - Server configuration options
- [Usage Guide](../usage.md) - Practical usage examples

## Versioning

The server API follows semantic versioning:

- **Major**: Breaking changes to API contracts
- **Minor**: New features, backward compatible
- **Patch**: Bug fixes, no API changes

Current API version: `1.8.1`

## Changelog

See [CHANGELOG.md](../changelog.md) for detailed version history and API changes.
