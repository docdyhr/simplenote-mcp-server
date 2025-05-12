# PRD: Simplenote MCP Server for Claude Desktop

**Version:** 1.0.1
**Date:** 2025-04-07
**Status:** Finalized for V1 Release

## 1. Introduction

This document outlines the requirements for the `simplenote-mcp-server`, a Python application built using the **MCP library** (`mcp` package). It acts as a bridge between Claude Desktop (via the Model Context Protocol - MCP) and the Simplenote note-taking service.

The server allows users to interact with their Simplenote notes (list, view, create, update, delete/trash, search, filter by tag) directly from Claude Desktop. Interaction occurs via the official Simplenote API, with changes syncing to the Simplenote Electron app through standard mechanisms. **The server handles note content as raw text, which may include Markdown formatting commonly used in Simplenote; interpretation and generation of Markdown are handled by the client application (Claude Desktop) and the underlying AI model.**

This server implements an **in-memory caching strategy** for performance and uses **Bearer token authentication** for secure client access from Claude Desktop.

## 2. Goals

* Provide a stable, performant MCP server using the **MCP library** (`mcp` package).
* Enable Claude Desktop users to access and manage Simplenote notes seamlessly.
* Implement **Bearer token authentication** for secure client access.
* Correctly implement the **MCP discovery endpoint** (`/api/v1/discovery`) advertising Simplenote capabilities.
* Utilize the `simplenote.py` library for robust interaction with the Simplenote API.
* Implement an **in-memory cache** with background synchronization for fast read access.
* Support **reading note tags** and **filtering notes by tags**.
* Provide clear documentation and scripts for easy setup and deployment on macOS 15+.

## 3. Non-Goals (for V1.0)

* **Direct Electron App UI Manipulation:** No direct control over the Simplenote app's UI.
* **Custom Real-time Bidirectional Sync:** Relies on background polling/sync, not instant push notifications for external changes.
* **Advanced Simplenote Features:** Note sharing, publishing, version history are out of scope.
* **Server-Side Markdown Processing:** The server transmits raw text; it does not parse, validate, or render Markdown itself.
* **Tag Management:** Creating/deleting tags or adding/removing tags from notes via MCP is out of scope.
* **Dedicated User Interface:** This is a backend server only.
* **Multi-User Support:** A single server instance supports only one Simplenote account configuration.
* **Permanent Deletion:** The delete operation only moves notes to the trash.

## 4. User Stories

* **As a Claude Desktop user, I want to list my recent Simplenote notes so that I can quickly see what I've been working on.**
* **As a Claude Desktop user, I want to list only the notes tagged 'project-alpha' so that I can focus on specific project information.**
* **As a Claude Desktop user, I want to ask Claude to find Simplenote notes containing specific keywords so that I can retrieve relevant information for my current task.**
* **As a Claude Desktop user, I want to view the full content (potentially interpreting it as Markdown) and tags of a specific Simplenote note identified by its title or ID so that I can use its content as context.**
* **As a Claude Desktop user, I want to dictate a new note (potentially using Markdown) to Claude and have it saved to Simplenote so that I can quickly capture ideas.**
* **As a Claude Desktop user, I want to ask Claude to update the content of an existing Simplenote note so that I can make corrections or additions.**
* **As a Claude Desktop user, I want to ask Claude to move a specific Simplenote note that I no longer need to the trash.**

## 5. Functional Requirements

### FR1: Server Setup & Configuration
    * MUST be implemented using the MCP library (`mcp` package).
    * MUST maintain the current stdio-based MCP server implementation.
    * MUST support configuration via environment variables.
    * Configuration MUST be via environment variables:
        * `SIMPLENOTE_EMAIL`
        * `SIMPLENOTE_PASSWORD`
        * `SYNC_INTERVAL_SECONDS` (Optional: frequency for background sync, e.g., 120)
    * Maintain existing scripts to start and manage the server.

### FR2: Simplenote Authentication
    * MUST authenticate with the Simplenote API using `SIMPLENOTE_EMAIL` and `SIMPLENOTE_PASSWORD`.
    * MUST handle Simplenote auth failures gracefully (e.g., log error, fail startup or sync).

### FR3: MCP Compliance & Features
    * MUST implement MCP using the `mcp` library conventions.
    * MUST properly advertise its capabilities (Simplenote resources/tools) according to MCP specification.
    * MUST maintain the existing MCP structure for resources and tools.

### FR4: Core Note Operations
    * MCP capabilities MUST be defined using `mcp.types` structures (e.g., Tool, Resource).
    * All operations MUST be implemented using the existing MCP server handlers.
    * **Resource Capabilities**
        * **List Resources**:
            * Retrieve notes from the in-memory cache.
            * MUST include note `tags` (list of strings) in the resource metadata.
            * Support filtering by tags if possible within the current framework.
            * Support limiting the number of notes returned.
        * **Read Resource**:
            * Retrieve full raw `content` and metadata (including `tags`) of a specific note by its URI.
            * Handle "Note Not Found" gracefully.
        * **Search Notes**:
            * Implement as a Tool capability for searching within note contents.
            * Perform case-insensitive keyword search across note content and titles.
            * Return matching notes with relevant metadata.
    * **Tool Capabilities**
        * **Create Note**:
            * Accept note content and optional tags.
            * Create the new note via the Simplenote API.
            * Return success confirmation with the new note ID.
        * **Update Note**:
            * Accept note ID, updated content, and optional tags.
            * Update the specified note via the Simplenote API.
            * Handle "Note Not Found" gracefully.
            * Return success confirmation.
        * **Delete Note**:
            * Accept note ID to be deleted.
            * Move the specified note to the Simplenote trash via the API (using `trash_note`).
            * Handle "Note Not Found" gracefully.
            * Return success confirmation.

### FR5: Data Representation
    * A consistent data structure MUST represent Simplenote notes in MCP responses, including fields like `id`, `content` (as raw string), `creationDate`, `modificationDate`, `tags: List[str]`.
    * Use the existing `mcp.types` classes for data representation.

### FR6: Error Handling
    * MUST gracefully handle common errors (Simplenote API errors, network issues, invalid requests, auth failures).
    * Implement appropriate error logging and reporting through the MCP protocol.

### FR7: Client Security
    * MUST use the existing Claude Desktop MCP security model.
    * Leverage environment variables for credentials management.
    * Follow security best practices for handling authentication credentials.

### FR8: Caching & Synchronization
    * MUST load all notes into an in-memory cache on server startup.
    * MUST implement a background task for periodic synchronization.
    * The sync task SHOULD use the Simplenote API's `index_since` mechanism to fetch only changes since the last sync marker.
    * The sync task MUST update the in-memory cache with creates, updates, and deletes detected from the API.
    * The sync interval SHOULD be configurable (env var `SYNC_INTERVAL_SECONDS`).

## 6. Non-Functional Requirements

* **NFR1: Performance:**
    * Respond to MCP requests for listing notes or retrieving cached note data in **< 50ms** (after initial load).
    * Individual cached note retrieval **< 30ms**.
    * API fallback/sync operations < 500ms typically (network dependent).
    * Initial full load of ~100 notes at startup should complete within a reasonable time (e.g., < 5 seconds, network dependent).
* **NFR2: Security:**
    * Secure credential handling (`SIMPLENOTE_*` via env vars).
    * Secure client authentication (Bearer token via `SERVER_AUTH_TOKEN` env var).
    * Input validation via Pydantic.
    * Keep dependencies up-to-date.
    * **HTTPS strongly recommended for production deployment** (setup outside scope of this project's run script).
* **NFR3: Usability:**
    * Straightforward setup using existing scripts.
    * Clear documentation (README, Integration Guide) covering setup, configuration, and usage.
* **NFR4: Reliability:**
    * Stable server operation with the current MCP implementation.
    * Graceful handling of API errors and synchronization issues.
    * Informative logging.
* **NFR5: Compatibility:**
    * Python 3.8+.
    * Tested primarily on macOS 15+ (but should be platform-agnostic).
    * Dependencies clearly listed in `requirements.txt`.

## 7. Design Considerations

* **Framework:** MCP library (`mcp` package).
* **Simplenote Interaction:** `simplenote.py` library.
* **Note Content:** Server handles content as raw text strings. Interpretation/generation of Markdown within this text is the responsibility of the MCP client (Claude Desktop / AI model).
* **Client Security:** Credentials managed via environment variables.
* **Caching Strategy:** In-memory cache holding all note data (content and metadata).
    * **Initial Load:** Full fetch during server initialization.
    * **Reads:** Served directly from memory.
    * **Writes:** Update API and immediately update cache.
    * **Synchronization:** Periodic background task using `index_since`.
* **Asynchronicity:** Leverage `async`/`await` for background tasks.

## 8. Open Questions / Future Considerations
* **(Future) Content Type Hinting:** Explore using MCP resource metadata or prompt definitions to explicitly signal to the AI model that note content should be treated as Markdown.
* ~~**(Future) Tag Management:** Implement MCP tools/endpoints to add/remove tags from notes.~~ (Implemented in v1.1.0)
* **(Future) Permanent Deletion:** Add an optional, explicit MCP tool/action for permanent note deletion (distinct from the default trash operation).
* **(Future) Advanced Search:** Support more complex search queries if the Simplenote API allows (e.g., boolean logic, tag-specific search).
* **(Future) Performance Monitoring:** Integrate metrics collection (e.g., Prometheus client) for cache stats, response times, API calls.
* **(Future) Pagination:** Support pagination for listing notes if scaling to handle significantly more than a few hundred notes.
* **(Future) Docker Packaging:** Provide a Dockerfile for containerized deployment.

## 9. Release Criteria (MVP - V1.0)

* All Functional Requirements (FR1-FR8) implemented and tested.
* End-to-end manual testing with Claude Desktop confirms core user stories (List, Get, Create, Update, Trash, Search, Filter by Tag) work correctly.
* In-memory caching and background synchronization are functional.
* Core Non-Functional Requirements (NFR1-NFR5) met for deployment.
* Documentation (README, Integration Guide) covers setup, configuration, running the server, and basic usage.
* Existing scripts successfully set up dependencies and run the server on macOS.
