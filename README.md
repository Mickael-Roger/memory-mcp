# Memory MCP

Local Memory MCP Server for OpenCode - A persistent memory layer for AI coding agents.

## Features

- Local-only memory storage (no external services except embeddings)
- FAISS vector search for semantic memory retrieval
- SQLite for metadata persistence
- MCP protocol for integration with OpenCode
- Concurrent access via file locking

## Quick Start

```bash
# Set environment variables
export MEMORY_USER_ID=your_user_id
export EMBEDDING_PROVIDER=openai  # or ollama, huggingface
export EMBEDDING_API_KEY=your_api_key

# Run the server
python -m memory_mcp.server
```

## OpenCode Configuration

Add to your OpenCode MCP configuration file:

```json
{
  "mcp": {
    "memory": {
      "type": "local",
      "enabled": true,
      "command": ["uvx", "--from", "opencode-memory", "memory-mcp", "--stdio"],
      "environment": {
        "MEMORY_USER_ID": "user_name",
        "MEMORY_DATA_DIR": "{env:HOME}/.memory",
        "EMBEDDING_PROVIDER": "openai",
        "EMBEDDING_API_KEY": "your_api_key"
      }
    }
  }
}
```

Or after installing via pip:

```bash
uvx opencode-memory
```

```bash
#!/bin/bash
export MEMORY_USER_ID=your_user_id
export MEMORY_DATA_DIR=./data
export EMBEDDING_PROVIDER=openai
export EMBEDDING_API_KEY=your_api_key
exec python -m memory_mcp.server
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MEMORY_USER_ID` | Yes | User/entity ID for operations |
| `MEMORY_DATA_DIR` | No | Base directory for data (default: `./data`) |
| `EMBEDDING_PROVIDER` | Yes | `openai`, `ollama`, or `huggingface` |
| `EMBEDDING_API_KEY` | No | API key for embedding service |
| `EMBEDDING_BASE_URL` | No | Custom endpoint for Ollama/HF |
| `EMBEDDING_MODEL` | No | Model name |
| `EMBEDDING_DIMENSION` | No | Vector dimension (default: 1536) |
