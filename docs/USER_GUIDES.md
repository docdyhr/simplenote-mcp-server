# Simplenote MCP Server - User Guides

This document provides guides for various use cases of the Simplenote MCP Server.

## Table of Contents

- [Simplenote MCP Server - User Guides](#simplenote-mcp-server---user-guides)
  - [Table of Contents](#table-of-contents)
  - [1. Prerequisites](#1-prerequisites)
  - [2. Basic Interaction with the MCP Server](#2-basic-interaction-with-the-mcp-server)
    - [Listing Available Tools](#listing-available-tools)
    - [Understanding Tool Schemas](#understanding-tool-schemas)
  - [3. Use Case: Creating a New Note](#3-use-case-creating-a-new-note)
    - [Using the `create_note` Tool](#using-the-create_note-tool)
    - [Example Request and Response](#example-request-and-response)
  - [4. Use Case: Retrieving and Reading a Note](#4-use-case-retrieving-and-reading-a-note)
    - [Using the `get_note` Tool](#using-the-get_note-tool)
    - [Understanding Note Structure](#understanding-note-structure)
  - [5. Use Case: Updating an Existing Note](#5-use-case-updating-an-existing-note)
    - [Using the `update_note` Tool](#using-the-update_note-tool)
    - [Handling Note Versions](#handling-note-versions)
  - [6. Use Case: Searching Notes](#6-use-case-searching-notes)
    - [Using the `search_notes` Tool](#using-the-search_notes-tool)
    - [Search Query Syntax](#search-query-syntax)
    - [Interpreting Search Results](#interpreting-search-results)
  - [7. Use Case: Deleting a Note](#7-use-case-deleting-a-note)
    - [Using the `delete_note` Tool](#using-the-delete_note-tool)
    - [Understanding Soft vs. Permanent Deletion](#understanding-soft-vs-permanent-deletion)
  - [8. Use Case: Listing Resources (Notes)](#8-use-case-listing-resources-notes)
    - [Using `list_resources`](#using-list_resources)
    - [Filtering and Sorting (if available)](#filtering-and-sorting-if-available)
  - [9. Integrating with an AI Assistant (e.g., Claude)](#9-integrating-with-an-ai-assistant-eg-claude)
    - [Enabling the Simplenote MCP Server](#enabling-the-simplenote-mcp-server)
    - [Natural Language Commands for Notes](#natural-language-commands-for-notes)
    - [Example Prompts and Interactions](#example-prompts-and-interactions)
  - [10. Advanced: Using Prompts](#10-advanced-using-prompts)
    - [Understanding `create_note_prompt`](#understanding-create_note_prompt)
    - [Understanding `search_notes_prompt`](#understanding-search_notes_prompt)
  - [11. Troubleshooting Common Scenarios](#11-troubleshooting-common-scenarios)
    - [Authentication Errors](#authentication-errors)
    - [Tool Not Found](#tool-not-found)
    - [Incorrect Input Schema](#incorrect-input-schema)

---

## 1. Prerequisites

Before using these guides, ensure that:

* The Simplenote MCP Server is [installed and configured correctly](../README.md#installation) as per the main `README.md`.
* You have your `SIMPLENOTE_EMAIL` and `SIMPLENOTE_PASSWORD` environment variables set.
* The server is running.
* You have a way to send MCP requests to the server (e.g., through Claude Desktop, a custom client, or a tool like `curl` if you know the Stdio MCP protocol details).

## 2. Basic Interaction with the MCP Server

*(Details to be added: How to discover tools, check server health, etc.)*

### Listing Available Tools

*(Details to be added)*

### Understanding Tool Schemas

*(Details to be added)*

## 3. Use Case: Creating a New Note

*(Details to be added for creating notes, including parameters like content, tags.)*

### Using the `create_note` Tool

*(Details to be added)*

### Example Request and Response

*(Details to be added)*

## 4. Use Case: Retrieving and Reading a Note

*(Details to be added for fetching specific notes by ID.)*

### Using the `get_note` Tool

*(Details to be added)*

### Understanding Note Structure

*(Details to be added)*

## 5. Use Case: Updating an Existing Note

*(Details to be added for modifying notes, including content, tags, and version handling.)*

### Using the `update_note` Tool

*(Details to be added)*

### Handling Note Versions

*(Details to be added)*

## 6. Use Case: Searching Notes

*(Details to be added for using the search functionality, query syntax, and interpreting results.)*

### Using the `search_notes` Tool

The `search_notes` tool allows you to find notes based on keywords, tags, and date ranges.

When filtering by tags:

* **Case-Insensitive**: Tag matching is case-insensitive. For example, searching for `tag:work` will find notes tagged with `Work`, `work`, or `WORK`.
* **Untagged Notes**: You can find notes that have no tags by using the special filter `tags:untagged`.
* **Multiple Tags**: If you provide multiple tags (comma-separated), the search will return notes that contain *all* the specified tags. For example, `tags:project,important` will find notes tagged with both "project" (or its case variants) AND "important" (or its case variants).

### Search Query Syntax

The `search_notes` tool supports a query parameter for keywords and a `tags` parameter for tag-based filtering.

* **Keywords**: The `query` parameter accepts text that will be searched for in the content of your notes.
* **Tags**: The `tags` parameter accepts a comma-separated list of tags.
  * To find notes with specific tags, provide the tag names (e.g., `Work`, `Personal`). Matching is case-insensitive.
  * To find notes with no tags, use the special keyword `untagged`.
  * Example: `tags:Urgent,ProjectAlpha` will find notes tagged with both "Urgent" and "ProjectAlpha" (case-insensitively).
  * Example: `tags:untagged` will find all notes that have no tags.

### Interpreting Search Results

*(Details to be added)*

## 7. Use Case: Deleting a Note

*(Details to be added for deleting notes, and the implications of soft vs. permanent delete if applicable at the MCP level.)*

### Using the `delete_note` Tool

*(Details to be added)*

### Understanding Soft vs. Permanent Deletion

*(Details to be added)*

## 8. Use Case: Listing Resources (Notes)

*(Details to be added for listing all notes/resources, including any filtering or pagination.)*

### Using `list_resources`

The `list_resources` tool can be used to retrieve a list of your notes. It supports filtering by a single tag.

When filtering by a tag:

* **Case-Insensitive**: Tag matching is case-insensitive. For example, providing `tag:work` will list notes tagged with `Work`, `work`, or `WORK`.
* **Untagged Notes**: You can list notes that have no tags by using the special filter `tag:untagged`.

### Filtering and Sorting (if available)

The `list_resources` tool currently supports filtering by a single tag via the `tag` parameter.

* To filter by a specific tag, provide the tag name (e.g., `MyTag`). Matching is case-insensitive.
* To list only notes that have no tags, use the special value `untagged`.
* Example: `tag:travel` will list notes tagged with "travel" (or "Travel", "TRAVEL", etc.).
* Example: `tag:untagged` will list all notes that are not tagged.

Sorting options are not explicitly available through parameters in `list_resources`; notes are typically returned in the order determined by the Simplenote API (often by modification date).

## 9. Integrating with an AI Assistant (e.g., Claude)

*(Details to be added for typical interactions when the server is used via an AI assistant.)*

### Enabling the Simplenote MCP Server

*(Details to be added)*

### Natural Language Commands for Notes

*(Details to be added)*

### Example Prompts and Interactions

*(Details to be added)*

## 10. Advanced: Using Prompts

*(Details to be added for developers or advanced users who might leverage the defined MCP prompts directly.)*

### Understanding `create_note_prompt`

*(Details to be added)*

### Understanding `search_notes_prompt`

*(Details to be added)*

## 11. Troubleshooting Common Scenarios

*(Links to the main README.md troubleshooting section, or specific tips related to use cases.)*

### Authentication Errors

*(Details to be added)*

### Tool Not Found

*(Details to be added)*

### Incorrect Input Schema

*(Details to be added)*

---

*This guide is a work in progress. More details will be added to each section.*
