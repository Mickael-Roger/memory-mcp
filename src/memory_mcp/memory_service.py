from datetime import datetime
from typing import Any

from .embedder import create_embedder, Embedder
from .faiss_store import FAISSStore
from .sqlite_store import MemoryRecord, SQLiteStore


class MemoryService:
    def __init__(
        self,
        sqlite_store: SQLiteStore | None = None,
        faiss_store: FAISSStore | None = None,
        embedder: Embedder | None = None,
    ):
        self._sqlite = sqlite_store or SQLiteStore()
        self._faiss = faiss_store or FAISSStore()
        self._embedder = embedder or create_embedder()

    def add_memory(
        self,
        text: str,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = self._sqlite.add(
            text=text,
            user_id=user_id,
            metadata=metadata,
        )
        embedding = self._embedder.embed(text)
        vector_id = self._faiss.add(record.id, embedding)
        self._sqlite.update_vector_id(record.id, vector_id)
        return {
            "memory_id": record.id,
            "text": record.text,
            "metadata": record.metadata,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }

    def search_memories(
        self,
        query: str,
        user_id: str | None = None,
        limit: int = 10,
        threshold: float | None = None,
    ) -> dict[str, Any]:
        embedding = self._embedder.embed(query)
        results = self._faiss.search(embedding, limit=limit, threshold=threshold)
        memories = []
        for memory_id, score in results:
            record = self._sqlite.get(memory_id)
            if record and (user_id is None or record.user_id == user_id):
                memories.append(
                    {
                        "memory_id": record.id,
                        "text": record.text,
                        "metadata": record.metadata,
                        "score": score,
                        "created_at": record.created_at.isoformat() if record.created_at else None,
                    }
                )
        return {"results": memories}

    def get_memories(
        self,
        user_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        records, total = self._sqlite.get_many(user_id=user_id, limit=limit, offset=offset)
        memories = []
        for record in records:
            memories.append(
                {
                    "memory_id": record.id,
                    "text": record.text,
                    "metadata": record.metadata,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                    "updated_at": record.updated_at.isoformat() if record.updated_at else None,
                }
            )
        return {
            "memories": memories,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        record = self._sqlite.get(memory_id)
        if not record:
            return None
        return {
            "memory_id": record.id,
            "text": record.text,
            "metadata": record.metadata,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }

    def update_memory(
        self,
        memory_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        existing_record = self._sqlite.get(memory_id)
        if not existing_record:
            return None

        record = self._sqlite.update(memory_id, text, metadata=metadata)
        if not record:
            return None

        embedding = self._embedder.embed(text)
        self._faiss.delete(memory_id)
        vector_id = self._faiss.add(memory_id, embedding)
        self._sqlite.update_vector_id(memory_id, vector_id)

        return {
            "memory_id": record.id,
            "text": record.text,
            "metadata": record.metadata,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }

    def delete_memory(self, memory_id: str) -> bool:
        self._faiss.delete(memory_id)
        return self._sqlite.delete(memory_id)
