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

1. `altary_projects` - プロジェクト一覧取得
2. `altary_errors` - エラー一覧取得（AI分析付き）
3. `altary_complete` - エラー完了処理（類似エラー自動完了）
4. `altary_auth` - 認証設定
5. `altary_set_project` - デフォルトプロジェクト設定
6. `altary_config` - 設定表示
7. `altary_clear` - 設定クリア

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