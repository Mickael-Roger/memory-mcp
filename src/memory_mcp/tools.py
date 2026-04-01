from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator

from .memory_service import MemoryService

mcp = FastMCP(
    "opencode-memory",
    instructions="Persistent memory for coding agent. Stores user preferences, "
    "coding conventions, project-specific rules, and any information relevant for future "
    "coding sessions. Example: 'For Python projects, always put imports at the top of "
    "source files' or 'User prefers TypeScript over JavaScript for backend'.",
)
_memory_service: MemoryService | None = None

TEXT_MAX_LENGTH = 100_000
MAX_LIMIT = 1000


class AddMemoryInput(BaseModel):
    text: Annotated[str, Field(min_length=1, max_length=TEXT_MAX_LENGTH)]
    metadata: dict[str, Any] | None = None

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text cannot be empty or whitespace only")
        return v


class SearchMemoriesInput(BaseModel):
    query: Annotated[str, Field(min_length=1)]
    limit: Annotated[int, Field(ge=1, le=MAX_LIMIT, default=10)]
    threshold: float | None = None

    @field_validator("threshold")
    @classmethod
    def threshold_range(cls, v: float | None) -> float | None:
        if v is not None and not (-1.0 <= v <= 1.0):
            raise ValueError("threshold must be between -1.0 and 1.0")
        return v


class GetMemoriesInput(BaseModel):
    limit: Annotated[int, Field(ge=1, le=MAX_LIMIT, default=50)]
    offset: Annotated[int, Field(ge=0, default=0)]


class GetMemoryInput(BaseModel):
    memory_id: str


class UpdateMemoryInput(BaseModel):
    memory_id: str
    text: Annotated[str, Field(min_length=1, max_length=TEXT_MAX_LENGTH)]
    metadata: dict[str, Any] | None = None

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text cannot be empty or whitespace only")
        return v


class DeleteMemoryInput(BaseModel):
    memory_id: str


def get_memory_service() -> MemoryService:
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service


@mcp.tool(
    description="Store a new memory. Use to save user preferences, coding conventions, project rules, or any information the AI should remember across sessions. Example: 'User prefers kebab-case for file names'."
)
def add_memory(
    text: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Store a new memory for the user.

    Args:
        text: The memory content to store. Be specific and factual.
               Good: 'Always run tests before committing'
               Bad: 'remember this'
        metadata: Optional categorisation tags like {'category': 'coding_convention'}
    """
    input_data = AddMemoryInput(text=text, metadata=metadata)
    service = get_memory_service()
    return service.add_memory(text=input_data.text, metadata=input_data.metadata)


@mcp.tool(
    description="Search stored memories semantically. Use to find relevant information from previous sessions, user preferences, or project-specific rules. Returns memories sorted by relevance."
)
def search_memories(
    query: str,
    limit: int = 10,
    threshold: float | None = None,
) -> dict[str, Any]:
    """Search memories using natural language query.

    Args:
        query: Natural language search query for what you want to find.
               Example: 'What are the user's Python coding conventions?'
        limit: Maximum number of results to return (default: 10)
        threshold: Minimum similarity score (0-1), lower returns more results
    """
    input_data = SearchMemoriesInput(query=query, limit=limit, threshold=threshold)
    service = get_memory_service()
    return service.search_memories(
        query=input_data.query,
        limit=input_data.limit,
        threshold=input_data.threshold,
    )


@mcp.tool(
    description="List all stored memories with pagination. Use to see all memories or browse through them. Returns memories in reverse chronological order (newest first)."
)
def get_memories(
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List all memories for the current user with pagination.

    Args:
        limit: Maximum number of memories to return (default: 50)
        offset: Number of memories to skip for pagination (default: 0)
    """
    input_data = GetMemoriesInput(limit=limit, offset=offset)
    service = get_memory_service()
    return service.get_memories(limit=input_data.limit, offset=input_data.offset)


@mcp.tool(
    description="Retrieve a specific memory by its ID. Use when you have a memory_id from a previous operation and need to see its full content."
)
def get_memory(memory_id: str) -> dict[str, Any] | None:
    """Get a specific memory by its ID.

    Args:
        memory_id: The unique identifier of the memory to retrieve
    """
    input_data = GetMemoryInput(memory_id=memory_id)
    service = get_memory_service()
    return service.get_memory(memory_id=input_data.memory_id)


@mcp.tool(
    description="Update an existing memory's content. Use when user corrects information or when preferences change. The memory_id must be from a previously stored memory."
)
def update_memory(
    memory_id: str,
    text: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Update an existing memory with new content.

    Args:
        memory_id: ID of the memory to update (must already exist)
        text: New content to replace the existing memory
        metadata: Optional new metadata/categories
    """
    input_data = UpdateMemoryInput(memory_id=memory_id, text=text, metadata=metadata)
    service = get_memory_service()
    return service.update_memory(
        memory_id=input_data.memory_id,
        text=input_data.text,
        metadata=input_data.metadata,
    )


@mcp.tool(
    description="Delete a memory permanently. Use when the stored information is no longer relevant or was stored incorrectly. Cannot be undone."
)
def delete_memory(memory_id: str) -> bool:
    """Delete a memory permanently.

    Args:
        memory_id: ID of the memory to delete
    """
    input_data = DeleteMemoryInput(memory_id=memory_id)
    service = get_memory_service()
    return service.delete_memory(memory_id=input_data.memory_id)
