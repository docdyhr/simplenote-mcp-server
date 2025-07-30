# Simplenote MCP Server Documentation

Welcome to the Simplenote MCP Server documentation!

The Simplenote MCP Server is a Model Context Protocol (MCP) server that provides seamless integration with Simplenote for note management and search capabilities. It allows Claude Desktop and other MCP clients to interact with your Simplenote account through a standardized interface.

## Features

- **Complete Note Management**: Create, read, update, and delete notes in your Simplenote account
- **Advanced Search**: Powerful search capabilities with boolean operators, phrase matching, and tag filtering
- **Real-time Sync**: Automatic synchronization with your Simplenote account
- **Caching System**: Intelligent caching for improved performance
- **Resource Discovery**: Expose your notes as MCP resources for easy access
- **Claude Desktop Integration**: Seamless integration with Claude Desktop for AI-powered note management

## Quick Start

1. **Install the package**:
   ```bash
   pip install simplenote-mcp-server
   ```

2. **Configure your credentials**:
   Set your Simplenote email and password as environment variables:
   ```bash
   export SIMPLENOTE_EMAIL="your-email@example.com"
   export SIMPLENOTE_PASSWORD="your-password"
   ```

3. **Add to Claude Desktop**:
   Update your Claude Desktop configuration file:
   ```json
   {
     "mcpServers": {
       "simplenote": {
         "command": "simplenote-mcp-server",
         "env": {
           "SIMPLENOTE_EMAIL": "your-email@example.com",
           "SIMPLENOTE_PASSWORD": "your-password"
         }
       }
     }
   }
   ```

4. **Start using it**:
   Restart Claude Desktop and start interacting with your Simplenote notes!

## What's Next?

- [**Installation**](installation.md) - Detailed installation instructions
- [**Configuration**](configuration.md) - Configuration options and setup
- [**Usage**](usage.md) - How to use the server and available tools
- [**API Reference**](api/server.md) - Technical documentation for developers

## Available Tools

The server provides the following tools for Claude Desktop:

### Note Management
- `create_note` - Create a new note
- `update_note` - Update an existing note
- `delete_note` - Delete a note
- `get_note` - Retrieve a specific note

### Search & Discovery
- `search_notes` - Search through your notes with advanced filtering
- `list_tags` - Get all available tags
- `get_notes_by_tag` - Find notes by specific tags

### Utility Tools
- `get_note_count` - Get total number of notes
- `sync_notes` - Force synchronization with Simplenote

## Resources

The server exposes your Simplenote notes as MCP resources, making them discoverable and accessible to Claude Desktop. Each note becomes a resource that can be:

- Referenced in conversations
- Used as context for AI responses
- Searched and filtered dynamically
- Updated through the conversation interface

## Security & Privacy

- Credentials are stored securely as environment variables
- All communication with Simplenote uses HTTPS
- Local caching respects your privacy settings
- No data is shared with third parties

## Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/docdyhr/simplenote-mcp-server/issues)
- **Documentation**: Browse this documentation for detailed information
- **Contributing**: See our [contributing guide](contributing.md) to help improve the project

## License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/docdyhr/simplenote-mcp-server/blob/main/LICENSE) file for details.

---

*Documentation last updated: January 31, 2025*
