from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator

from .memory_service import MemoryService

mcp = FastMCP("memory-mcp")
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


@mcp.tool()
def add_memory(
    text: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    input_data = AddMemoryInput(text=text, metadata=metadata)
    service = get_memory_service()
    return service.add_memory(text=input_data.text, metadata=input_data.metadata)


@mcp.tool()
def search_memories(
    query: str,
    limit: int = 10,
    threshold: float | None = None,
) -> dict[str, Any]:
    input_data = SearchMemoriesInput(query=query, limit=limit, threshold=threshold)
    service = get_memory_service()
    return service.search_memories(
        query=input_data.query,
        limit=input_data.limit,
        threshold=input_data.threshold,
    )


@mcp.tool()
def get_memories(
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    input_data = GetMemoriesInput(limit=limit, offset=offset)
    service = get_memory_service()
    return service.get_memories(limit=input_data.limit, offset=input_data.offset)


@mcp.tool()
def get_memory(memory_id: str) -> dict[str, Any] | None:
    input_data = GetMemoryInput(memory_id=memory_id)
    service = get_memory_service()
    return service.get_memory(memory_id=input_data.memory_id)


@mcp.tool()
def update_memory(
    memory_id: str,
    text: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    input_data = UpdateMemoryInput(memory_id=memory_id, text=text, metadata=metadata)
    service = get_memory_service()
    return service.update_memory(
        memory_id=input_data.memory_id,
        text=input_data.text,
        metadata=input_data.metadata,
    )


@mcp.tool()
def delete_memory(memory_id: str) -> bool:
    input_data = DeleteMemoryInput(memory_id=memory_id)
    service = get_memory_service()
    return service.delete_memory(memory_id=input_data.memory_id)
