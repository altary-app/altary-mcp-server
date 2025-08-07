# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Altary MCP Server - a Model Context Protocol (MCP) server that integrates Claude Code with the Altary error management service (https://altary.web-ts.dev). The server provides tools for retrieving project information, fetching errors with AI analysis, and completing error resolution with AI-powered similarity detection.

## Common Development Commands

### Development Setup
```bash
# Install in development mode
pip install -e ".[dev]"

# Install dependencies only
pip install -e .
```

### Testing and Running
```bash
# Run unit tests
python -m pytest

# Test MCP server directly
python -m altary_mcp.server

# Run as CLI tool (after installation)
altary-mcp-server
```

## Architecture

### Core Components

- **`server.py`**: Main MCP server implementation using stdio_server protocol. Defines 7 tools for Altary integration and handles tool execution routing.

- **`client.py`**: HTTP client (`AltaryClient`) for Altary API communication. Handles authentication, project retrieval, error fetching, and error completion with similarity detection.

- **`config.py`**: Configuration management (`AltaryConfig`) using JSON storage at `~/.altary/config.json`. Manages auth tokens, project IDs, and API endpoints.

### Key Design Patterns

- **Configuration as Properties**: `AltaryConfig` uses property setters that automatically save to disk
- **Async HTTP Client**: Uses `httpx.AsyncClient` with 30-second timeout for all API calls  
- **MCP Tool Schema**: Each tool defines JSON schema for input validation
- **Error Handling**: Comprehensive exception handling with user-friendly Japanese error messages

### API Integration

The server integrates with three main Altary API endpoints:
- `GET /users/getUserProjects` - Project listing
- `GET /issues/getError/{project_id}` - Error retrieval with AI analysis
- `POST /issues/completeErrorWithSimilar/{error_id}` - Error completion with similarity detection

Authentication uses custom `X-Claude-Token` header with validation through project API calls.

### MCP Tools Available

1. `get_user_projects` - List user projects
2. `get_errors` - Fetch project errors with AI analysis  
3. `complete_error` - Complete error with similar error detection
4. `setup_auth` - Handle authentication (browser or token)
5. `set_default_project` - Set default project ID
6. `show_config` - Display current configuration
7. `clear_config` - Reset all configuration

## Installation Methods

### Preferred: Claude Code MCP Integration
```bash
claude mcp add altary -- uvx --from git+https://github.com/altary-app/altary-mcp-server altary-mcp-server
```

### Manual Installation
```bash
git clone https://github.com/altary-app/altary-mcp-server.git
cd altary-mcp-server
pip install -e .
```

## Configuration Storage

- Configuration stored in `~/.altary/config.json`
- Contains API base URL, auth token, and default project ID
- Auto-creates config directory and file as needed