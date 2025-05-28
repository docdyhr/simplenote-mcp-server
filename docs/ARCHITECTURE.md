# Simplenote MCP Server - Architecture Overview

This document provides a high-level overview of the Simplenote MCP Server's architecture. Its purpose is to help developers understand the main components and how they interact.

## Core Components

The server is composed of several key components:

1. **MCP Server Framework (`mcp.server`)**:
    * The foundation provided by the `mcp.py` library.
    * Handles the raw MCP (Meta-Claude Protocol) communication over stdio.
    * Manages registration of resources, tools, and prompts.
    * Receives requests from the MCP client (e.g., Claude Desktop) and dispatches them to the appropriate handlers within this application.

2. **Simplenote API Client (`simplenote.Simplenote`)**:
    * An instance of the `simplenote` Python library.
    * Responsible for all direct communication with the official Simplenote API (authentication, fetching notes, updating notes, etc.).
    * Abstracts the underlying HTTP requests to the Simplenote backend.

3. **Application Core (`simplenote_mcp.server.server`)**:
    * This is the main application logic that glues everything together.
    * Initializes the MCP server instance and the Simplenote API client.
    * Defines and registers the tools (`create_note`, `get_note`, `search_notes`, etc.), resources (`list_resources`, `read_resource`), and prompts (`create_note_prompt`, `search_notes_prompt`) with the MCP framework.
    * Contains the handler functions that are invoked when a tool is called or a resource is requested.

4. **Note Cache (`simplenote_mcp.server.cache.NoteCache`)**:
    * An in-memory cache for Simplenote notes.
    * **Purpose**: To reduce latency for read operations (getting notes, searching) and to minimize direct calls to the Simplenote API, respecting rate limits and improving performance.
    * Holds note data (ID, content, tags, modification dates, etc.).
    * Interacts with the Simplenote API Client to populate and update itself.

5. **Background Synchronizer (`simplenote_mcp.server.cache.BackgroundSync`)**:
    * A background thread/task responsible for periodically synchronizing the in-memory `NoteCache` with the Simplenote service.
    * Uses the `index_since` mechanism of the Simplenote API (if available and used by the client library) for efficient delta updates.
    * Handles logic for initial cache population and subsequent incremental updates.
    * Configurable sync interval (e.g., via `SYNC_INTERVAL_SECONDS`).

6. **Tool Implementation Layer**:
    * The specific Python functions that implement the logic for each registered MCP tool (e.g., `handle_create_note`, `handle_search_notes`).
    * These functions typically:
        * Validate input parameters against their JSON schemas.
        * Interact with the `NoteCache` first for read operations.
        * Fall back to or directly use the `Simplenote API Client` for write operations or if data is not in the cache/needs to be fresh.
        * Update the `NoteCache` after successful write operations.
        * Format the response according to MCP specifications.

7. **Configuration Management (`simplenote_mcp.server.config`)**:
    * Loads and provides access to configuration settings.
    * Primarily uses environment variables (e.g., `SIMPLENOTE_EMAIL`, `SIMPLENOTE_PASSWORD`, `LOG_LEVEL`, `SYNC_INTERVAL_SECONDS`).
    * Ensures necessary configurations are present and valid.

8. **Logging System (`simplenote_mcp.server.logging`)**:
    * Implements structured logging throughout the application.
    * Provides contextual information in log messages (e.g., trace IDs, component names).
    * Configurable log levels for verbosity.
    * Outputs logs to stderr and/or log files.

9. **Error Handling (`simplenote_mcp.server.errors`)**:
    * Defines custom error classes (e.g., `AuthenticationError`, `ResourceNotFoundError`, `ServerError`).
    * Provides a centralized way to handle exceptions from the Simplenote API client or internal operations.
    * Formats errors into MCP-compliant error responses.

## Key Interactions & Data Flows

### Example: Request to `search_notes` Tool

1. **MCP Client (e.g., Claude Desktop)** sends a `call_tool` request for `search_notes` with a query payload.
2. **MCP Server Framework** receives the request and routes it to the `handle_search_notes` function in the Application Core.
3. **`handle_search_notes`**:
    * Validates the input query.
    * **(Primary Path)** Accesses the `NoteCache` to perform the search on the locally cached notes. The cache's search implementation might involve iterating through notes, checking content and tags.
    * **(Fallback/Alternative if cache is disabled or specific needs)** If necessary, or if the cache isn't fully authoritative for all search types, it might consult the `Simplenote API Client`. (Note: The current `simplenote.py` client used may not have a direct API search, so server-side filtering of a list is more likely).
    * Constructs a list of matching notes.
    * Formats the result into the MCP `call_tool` response structure.
4. **MCP Server Framework** sends the response back to the MCP Client.

### Example: Request to `create_note` Tool

1. **MCP Client** sends a `call_tool` request for `create_note` with note content and tags.
2. **MCP Server Framework** routes to `handle_create_note`.
3. **`handle_create_note`**:
    * Validates input.
    * Calls the `add_note` method on the `Simplenote API Client`.
    * **Simplenote API Client** makes an HTTP request to the Simplenote service.
    * If successful, the Simplenote service returns the new note data (including its ID and version).
    * **`handle_create_note`** receives this data.
    * Updates the `NoteCache` with the newly created note.
    * Formats the new note data into the MCP response.
4. **MCP Server Framework** sends the response back.

### Background Sync Process

1. The `BackgroundSync` task wakes up periodically.
2. It calls a method on the `Simplenote API Client` (e.g., `get_note_list` with a `since` parameter based on the last sync timestamp) to fetch changes from the Simplenote service.
3. It processes the returned notes (new, updated, deleted) and updates the `NoteCache` accordingly.
    * New notes are added.
    * Existing notes are updated.
    * Notes marked as deleted by the API are updated or removed from the cache as per the server's logic for handling deletions.
4. Updates its last sync timestamp.

## Diagrammatic Representation (Conceptual)

```
+---------------------+      +--------------------------+      +-----------------------+
|   MCP Client        |<---->|   MCP Server Framework   |<---->|    Application Core   |
| (e.g. Claude Desk)  |      |     (mcp.py library)     |      | (server.py, tools.py) |
+---------------------+      +--------------------------+      +-----------+-----------+
                                      ^      |                         |
                                      |      | (Tool Calls/Responses)  | (Handles Tool Logic)
                                      |      |                         |
                                      |      v                         v
+-------------------------+      +----+-------------+      +-----------------------+
| Configuration Management|<-----| Logging System   |<-----|    Error Handling     |
|      (config.py)        |      | (logging.py)     |      |     (errors.py)       |
+-------------------------+      +------------------+      +-----------------------+
                                      ^      ^                         ^
                                      |      |                         |
                                      +------+----Tool Logic Uses----+--+
                                             |
                                             v
                               +-------------------------+
                               |      Note Cache         |
                               |     (cache.py)          |<---+
                               +-------------------------+    | (Sync)
                                      ^      |                 |
                                      |      | (Read/Write Cache)    |
                                      |      v                 |
      +---------------------------------+    +-------------------------+
      | Background Synchronizer         |--->|  Simplenote API Client  |<-----> Simplenote API
      | (cache.py - BackgroundSync)     |    |  (simplenote library)   |
      +---------------------------------+    +-------------------------+
```

*This is a textual representation of a conceptual diagram. Lines indicate primary interactions.*

---

This architectural overview should provide a foundational understanding for developers working on or integrating with the Simplenote MCP Server. For more specific details, refer to the source code and individual module documentation.
