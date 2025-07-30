# Usage Guide

This guide covers how to use the Simplenote MCP Server with Claude Desktop and other MCP clients.

## Getting Started

Once you have installed and configured the Simplenote MCP Server, you can start using it immediately with Claude Desktop. The server provides a rich set of tools and resources for managing your Simplenote notes.

## Available Tools

### Note Management

#### `create_note`
Create a new note in your Simplenote account.

**Parameters:**
- `content` (string, required): The content of the note
- `tags` (array of strings, optional): Tags to assign to the note

**Example usage in Claude Desktop:**
```
Create a new note with the content "Meeting notes for project X" and tag it with "work" and "meetings"
```

#### `update_note`
Update an existing note's content or tags.

**Parameters:**
- `note_id` (string, required): The ID of the note to update
- `content` (string, optional): New content for the note
- `tags` (array of strings, optional): New tags for the note

**Example usage:**
```
Update the note with ID "abc123" to add the tag "completed"
```

#### `delete_note`
Delete a note from your Simplenote account.

**Parameters:**
- `note_id` (string, required): The ID of the note to delete

**Example usage:**
```
Delete the note with ID "xyz789"
```

#### `get_note`
Retrieve the content and metadata of a specific note.

**Parameters:**
- `note_id` (string, required): The ID of the note to retrieve

**Example usage:**
```
Show me the content of note "abc123"
```

### Search and Discovery

#### `search_notes`
Search through your notes using advanced search capabilities.

**Parameters:**
- `query` (string, required): Search query
- `tags` (array of strings, optional): Filter by specific tags
- `limit` (integer, optional): Maximum number of results (default: 20)
- `include_deleted` (boolean, optional): Include deleted notes (default: false)

**Search Features:**
- **Boolean operators**: Use `AND`, `OR`, `NOT` for complex searches
- **Phrase matching**: Use quotes for exact phrases: `"project meeting"`
- **Tag filtering**: Search within specific tags
- **Wildcard support**: Use `*` for partial matches

**Example usage:**
```
Search for notes containing "python" and "tutorial"
Find all notes tagged with "work" that mention "deadline"
Search for the exact phrase "quarterly review"
```

#### `list_tags`
Get all available tags from your notes.

**Parameters:**
- `limit` (integer, optional): Maximum number of tags to return

**Example usage:**
```
Show me all my note tags
```

#### `get_notes_by_tag`
Find all notes that have a specific tag.

**Parameters:**
- `tag` (string, required): The tag to search for
- `limit` (integer, optional): Maximum number of results

**Example usage:**
```
Show me all notes tagged with "recipes"
```

### Utility Tools

#### `get_note_count`
Get the total number of notes in your account.

**Example usage:**
```
How many notes do I have?
```

#### `sync_notes`
Force synchronization with your Simplenote account to get the latest changes.

**Example usage:**
```
Sync my notes with Simplenote
```

## Working with Resources

The Simplenote MCP Server exposes your notes as MCP resources, making them discoverable and accessible to Claude Desktop.

### Resource URLs

Each note is accessible as a resource with the URL format:
```
simplenote://note/{note_id}
```

### Resource Discovery

Claude Desktop can automatically discover your notes. You can:

- Ask Claude to "list my recent notes"
- Reference notes by their titles or content
- Have Claude search through your notes contextually

## Common Usage Patterns

### Daily Note Management

```
Create a daily journal entry:
"Create a new note with today's date as the title and tag it with 'journal'"

Update an existing note:
"Add this meeting summary to my project notes"

Organize notes:
"Tag all my recipe notes with 'cooking'"
```

### Research and Knowledge Management

```
Search across your knowledge base:
"Find all notes about machine learning algorithms"

Create structured notes:
"Create a note about Python best practices with sections for syntax, performance, and testing"

Link related information:
"Find notes related to the project I'm working on"
```

### Task and Project Management

```
Track project progress:
"Create a note for the new website project and tag it with 'projects' and 'web-dev'"

Review completed tasks:
"Show me all notes tagged with 'completed'"

Plan upcoming work:
"Find all notes tagged with 'todo' and 'urgent'"
```

## Advanced Search Examples

### Boolean Operators

```
# Find notes with both terms
"Search for notes containing 'python AND machine learning'"

# Find notes with either term
"Search for notes about 'javascript OR typescript'"

# Exclude specific terms
"Find notes about 'web development' but NOT 'backend'"
```

### Phrase Matching

```
# Exact phrase search
"Find notes with the exact phrase 'quarterly business review'"

# Multiple phrases
"Search for notes containing 'project status' AND 'deadline approaching'"
```

### Tag-Based Filtering

```
# Search within specific tags
"Search for 'algorithm' in notes tagged with 'computer-science'"

# Multiple tag filtering
"Find notes tagged with both 'work' and 'meeting'"

# Tag exclusion
"Search all notes except those tagged with 'archive'"
```

### Date and Metadata Searches

```
# Recent notes
"Show me notes created in the last week"

# Modified notes
"Find notes I've updated recently"

# Large notes
"Show me my longest notes"
```

## Integration with Claude Desktop

### Natural Language Commands

Claude Desktop understands natural language commands for note management:

```
"Create a grocery list note"
"Find my recipe for chocolate cake"
"Update my todo list to mark the presentation as complete"
"Show me all my work-related notes from this week"
"Delete the old meeting notes from last month"
```

### Contextual Assistance

Claude can use your notes as context for conversations:

```
"Based on my project notes, what should I focus on next?"
"Help me summarize my research notes on renewable energy"
"Create a presentation outline from my conference notes"
```

### Batch Operations

```
"Tag all my cooking notes with 'recipes'"
"Find and organize all my travel planning notes"
"Create a summary of all my meeting notes from this month"
```

## Performance Tips

### Optimize Search Queries

- Use specific terms rather than generic ones
- Combine tags with content search for better filtering
- Limit results when dealing with large note collections

### Cache Management

- The server automatically caches frequently accessed notes
- Sync periodically to ensure you have the latest data
- Use offline mode for testing without API calls

### Rate Limiting

- The server automatically handles Simplenote API rate limits
- Avoid rapid-fire requests for better performance
- Use batch operations when possible

## Troubleshooting

### Common Issues

1. **Notes not appearing**: Run sync to get latest changes
2. **Search not finding notes**: Try simpler search terms or check spelling
3. **Authentication errors**: Verify your credentials in the configuration

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
export LOG_LEVEL=DEBUG
```

### Testing Commands

```
# Test basic functionality
"How many notes do I have?"

# Test search
"Search for any note containing 'test'"

# Test note creation
"Create a simple test note"
```

## Best Practices

### Note Organization

- Use consistent tagging schemes
- Keep note titles descriptive
- Regularly clean up old or obsolete notes

### Search Strategy

- Start with broad searches, then narrow down
- Use tags to categorize and filter content
- Combine multiple search techniques for best results

### Security

- Regularly review and update your Simplenote password
- Monitor your note access patterns
- Keep your server installation updated

## Getting Help

If you encounter issues or need assistance:

1. Check the [troubleshooting section](configuration.md#troubleshooting-configuration)
2. Review the [API documentation](api/server.md)
3. Open an issue on [GitHub](https://github.com/docdyhr/simplenote-mcp-server/issues)
4. Check the [changelog](changelog.md) for recent updates

## Next Steps

- Explore the [API Reference](api/server.md) for technical details
- Read about [Configuration](configuration.md) options
- Learn about [Contributing](contributing.md) to the project
