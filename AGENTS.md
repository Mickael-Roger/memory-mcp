# Memory MCP - Local Memory Server for OpenCode

## Overview

A local MCP (Model Context Protocol) server providing persistent memory capabilities for the OpenCode coding agent. Built on Mem0 OSS stack with FAISS for vector storage and SQLite for metadata.

**Key Design Decision**: Since memory tools are called by an LLM that already has full context, this server stores memories **without LLM inference** (`infer=False`). The calling agent provides pre-structured memory content.

## Architecture

```
┌─────────────────┐     MCP      ┌──────────────────────────────────┐
│   OpenCode      │─────────────▶│      Memory MCP Server            │
│   (LLM Agent)   │◀────────────│                                  │
└─────────────────┘              │  ┌────────────┐   ┌───────────┐   │
                                 │  │  MCP Tools │──▶│  Memory  │   │
                                 │  └────────────┘   │  Service │   │
                                 │                   └─────┬─────┘   │
                                 │                         │         │
                                 │         ┌───────────────┼─────┐   │
                                 │         ▼               ▼     │   │
                                 │  ┌───────────┐    ┌─────────┐ │   │
                                 │  │  FAISS    │    │ SQLite  │ │   │
                                 │  │ (vectors)│    │(metadata│ │   │
                                 │  └───────────┘    └─────────┘ │   │
                                 └──────────────────────────────────┘
                                                             │
                                 ┌─────────────────────────────┘
                                 ▼
                          ┌─────────────┐
                          │ Embedding   │
                          │ Service     │
                          │ (External)  │
                          └─────────────┘
```

## Tech Stack

- **MCP Server**: Python + `mcp` package (FastMCP)
- **Vector Store**: FAISS (local, CPU)
- **Metadata Store**: SQLite
- **Embedding**: Configurable via env vars (OpenAI, Ollama, HuggingFace)

## Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `MEMORY_USER_ID` | Yes | Default user/entity ID for all operations | - |
| `MEMORY_DATA_DIR` | No | Base directory for persistent data (FAISS index + SQLite DB) | `./data` |
| `EMBEDDING_PROVIDER` | Yes | Embedding provider (`openai`, `ollama`, `huggingface`) | - |
| `EMBEDDING_MODEL` | No | Model name (provider-specific) | Provider default |
| `EMBEDDING_API_KEY` | No | API key for embedding service | - |
| `EMBEDDING_BASE_URL` | No | Custom endpoint URL (for Ollama, local HF) | - |
| `EMBEDDING_DIMENSION` | No | Embedding vector dimension | 1536 (OpenAI) |

**Note**: FAISS index is stored at `{MEMORY_DATA_DIR}/faiss_index` and SQLite DB at `{MEMORY_DATA_DIR}/memory.db`

## MCP Tools

### add_memory
Save text or conversation history for a user/agent.

**Input**:
```json
{
  "text": "string (required) - Memory content to store",
  "metadata": "object (optional) - Additional filters/categories"
}
```

**Output**:
```json
{
  "memory_id": "string - Unique identifier",
  "text": "string - Stored content",
  "metadata": "object - Applied metadata",
  "created_at": "ISO8601 timestamp"
}
```

### search_memories
Semantic search across existing memories with filters.

**Input**:
```json
{
  "query": "string (required) - Natural language search query",
  "limit": "integer (optional) - Max results, default 10",
  "threshold": "float (optional) - Similarity threshold"
}
```

**Output**:
```json
{
  "results": [
    {
      "memory_id": "string",
      "text": "string",
      "metadata": "object",
      "score": "float - Similarity score",
      "created_at": "ISO8601 timestamp"
    }
  ]
}
```

### get_memories
List memories with structured filters and pagination.

**Input**:
```json
{
  "limit": "integer (optional) - Max results, default 50",
  "offset": "integer (optional) - Pagination offset, default 0"
}
```

**Output**:
```json
{
  "memories": [...],
  "total": "integer - Total count",
  "limit": "integer",
  "offset": "integer"
}
```

### get_memory
Retrieve one memory by its memory_id.

**Input**:
```json
{
  "memory_id": "string (required)"
}
```

### update_memory
Overwrite a memory's text after confirming the ID.

**Input**:
```json
{
  "memory_id": "string (required)",
  "text": "string (required) - New content"
}
```

### delete_memory
Delete a single memory by memory_id.

**Input**:
```json
{
  "memory_id": "string (required)"
}
```

## Data Model

### Memory (SQLite)
```sql
CREATE TABLE memories (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    text TEXT NOT NULL,
    metadata TEXT,  -- JSON
    vector_id INTEGER,  -- FAISS index position
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_memories_user_id ON memories(user_id);
CREATE INDEX idx_memories_created_at ON memories(created_at);
```

### FAISS Index
- Flat index with inner product (cosine similarity via normalized vectors)
- Persisted to disk at `{MEMORY_DATA_DIR}/faiss_index`
- Metadata mapping via SQLite `vector_id`

## Project Structure

```
memory-mcp/
├── src/
│   └── memory_mcp/
│       ├── __init__.py
│       ├── server.py          # MCP server entry point
│       ├── config.py          # Environment variable handling
│       ├── memory_service.py  # Core memory operations
│       ├── embedder.py        # Embedding service abstraction
│       ├── faiss_store.py     # FAISS vector operations
│       ├── sqlite_store.py    # SQLite metadata operations
│       ├── file_lock.py       # File locking for concurrent access
│       └── tools.py           # MCP tool definitions
├── tests/
├── data/                      # FAISS index + SQLite DB
├── pyproject.toml
└── uv.lock
```

## Implementation Phases

### Phase 1: Foundation
- [x] Project setup (pyproject, dependencies)
- [x] Config module (env vars)
- [x] SQLite store (CRUD for memories metadata)
- [x] FAISS store (vector add/search)
- [x] Embedder abstraction (OpenAI/Ollama/HF)

### Phase 2: Core Service
- [x] MemoryService combining FAISS + SQLite
- [x] ID generation (uuid)
- [x] Metadata filtering

### Phase 3: MCP Integration
- [x] FastMCP server setup
- [x] Tool definitions (add_memory, search_memories, etc.)
- [x] Error handling
- [x] File locking for concurrent access

### Phase 4: Testing & Polish
- [ ] Unit tests
- [ ] Integration tests
- [ ] Documentation

## Embedding Providers

### OpenAI
```bash
export EMBEDDING_PROVIDER=openai
export EMBEDDING_API_KEY=sk-...
export EMBEDDING_MODEL=text-embedding-3-small
```

### Ollama (Local)
```bash
export EMBEDDING_PROVIDER=ollama
export EMBEDDING_BASE_URL=http://localhost:11434
export EMBEDDING_MODEL=nomic-embed-text
```

### HuggingFace (Local)
```bash
export EMBEDDING_PROVIDER=huggingface
export EMBEDDING_BASE_URL=http://localhost:8080
export EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## Design Decisions

1. **No LLM inference**: The calling agent already has context. Storing raw text keeps it simple and fast.

2. **SQLite over graph**: User requested no graph DB. SQLite is sufficient for metadata and relationships.

3. **FAISS persistence**: Index is saved to disk for fast restart without re-indexing.

4. **user_id from env**: Single-user local use case. All operations scoped to configured user.

5. **Simple ID scheme**: UUID-based IDs without version prefixes (no v1/v2 distinction needed for OSS).

## Concurrent Access

Multiple OpenCode instances can run concurrently and share the same memory store. File locking (`fcntl.flock`) ensures serialized access to FAISS index and SQLite database:

- **Lock files**: `{MEMORY_DATA_DIR}/faiss_index.lock` and `{MEMORY_DATA_DIR}/memory.db.lock`
- **Write operations**: Always exclusive (other writers wait)
- **Read operations**: Safe for SQLite; FAISS reads don't require locking
- **Performance**: For local MCP with single agent, file locking overhead is negligible
