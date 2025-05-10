# Simplenote MCP Server - User Guides

This document provides guides for various use cases of the Simplenote MCP Server.

## Table of Contents

1.  [Prerequisites](#prerequisites)
2.  [Basic Interaction with the MCP Server](#basic-interaction-with-the-mcp-server)
    *   [Listing Available Tools](#listing-available-tools)
    *   [Understanding Tool Schemas](#understanding-tool-schemas)
3.  [Use Case: Creating a New Note](#use-case-creating-a-new-note)
    *   [Using the `create_note` Tool](#using-the-create_note-tool)
    *   [Example Request and Response](#example-request-and-response)
4.  [Use Case: Retrieving and Reading a Note](#use-case-retrieving-and-reading-a-note)
    *   [Using the `get_note` Tool](#using-the-get_note-tool)
    *   [Understanding Note Structure](#understanding-note-structure)
5.  [Use Case: Updating an Existing Note](#use-case-updating-an-existing-note)
    *   [Using the `update_note` Tool](#using-the-update_note-tool)
    *   [Handling Note Versions](#handling-note-versions)
6.  [Use Case: Searching Notes](#use-case-searching-notes)
    *   [Using the `search_notes` Tool](#using-the-search_notes-tool)
    *   [Search Query Syntax](#search-query-syntax)
    *   [Interpreting Search Results](#interpreting-search-results)
7.  [Use Case: Deleting a Note](#use-case-deleting-a-note)
    *   [Using the `delete_note` Tool](#using-the-delete_note-tool)
    *   [Understanding Soft vs. Permanent Deletion](#understanding-soft-vs-permanent-deletion)
8.  [Use Case: Listing Resources (Notes)](#use-case-listing-resources-notes)
    *   [Using `list_resources`](#using-list_resources)
    *   [Filtering and Sorting (if available)](#filtering-and-sorting-if-available)
9.  [Integrating with an AI Assistant (e.g., Claude)](#integrating-with-an-ai-assistant-eg-claude)
    *   [Enabling the Simplenote MCP Server](#enabling-the-simplenote-mcp-server)
    *   [Natural Language Commands for Notes](#natural-language-commands-for-notes)
    *   [Example Prompts and Interactions](#example-prompts-and-interactions)
10. [Advanced: Using Prompts](#advanced-using-prompts)
    *   [Understanding `create_note_prompt`](#understanding-create_note_prompt)
    *   [Understanding `search_notes_prompt`](#understanding-search_notes_prompt)
11. [Troubleshooting Common Scenarios](#troubleshooting-common-scenarios)
    *   [Authentication Errors](#authentication-errors)
    *   [Tool Not Found](#tool-not-found)
    *   [Incorrect Input Schema](#incorrect-input-schema)

---

## 1. Prerequisites

Before using these guides, ensure that:
*   The Simplenote MCP Server is [installed and configured correctly](../README.md#installation) as per the main `README.md`.
*   You have your `SIMPLENOTE_EMAIL` and `SIMPLENOTE_PASSWORD` environment variables set.
*   The server is running.
*   You have a way to send MCP requests to the server (e.g., through Claude Desktop, a custom client, or a tool like `curl` if you know the Stdio MCP protocol details).

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
*(Details to be added)*

### Search Query Syntax
*(Details to be added, referring to the capabilities outlined in README.md if applicable, such as boolean logic, tag search, date range.)*

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
*(Details to be added)*

### Filtering and Sorting (if available)
*(Details to be added)*

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
