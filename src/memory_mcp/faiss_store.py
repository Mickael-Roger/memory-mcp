import logging
from pathlib import Path

import faiss
import numpy as np

from .config import get_config
from .file_lock import file_lock

logger = logging.getLogger(__name__)


class FAISSStore:
    def __init__(self, index_path: Path | None = None, dimension: int | None = None):
        if index_path is None:
            config = get_config()
            index_path = config.faiss_index_path
            dimension = config.embedding_dimension
        else:
            if dimension is None:
                dimension = get_config().embedding_dimension

        self._index_path = index_path
        self._dimension = dimension
        self._index: faiss.IndexFlatIP | None = None
        self._id_to_vector_id: dict[str, int] = {}
        self._vector_id_to_id: dict[int, str] = {}
        self._deleted_vector_ids: set[int] = set()

    @property
    def _lock_path(self) -> Path:
        return self._index_path.with_suffix(".lock")

    def _ensure_index(self) -> faiss.IndexFlatIP:
        if self._index is None:
            self._index_path.parent.mkdir(parents=True, exist_ok=True)
            if self._index_path.exists():
                self._index = faiss.read_index(str(self._index_path))
                self._load_mapping()
            else:
                self._index = faiss.IndexFlatIP(self._dimension)
        return self._index

    def _load_mapping(self) -> None:
        mapping_file = self._index_path.with_suffix(".mapping")
        if mapping_file.exists():
            import json

            with open(mapping_file, "r") as f:
                data = json.load(f)
                self._id_to_vector_id = data.get("id_to_vector_id", {})
                self._vector_id_to_id = {
                    int(k): v for k, v in data.get("vector_id_to_id", {}).items()
                }
                self._deleted_vector_ids = set(data.get("deleted_vector_ids", []))

    def _save_mapping(self) -> None:
        mapping_file = self._index_path.with_suffix(".mapping")
        import json

        with open(mapping_file, "w") as f:
            json.dump(
                {
                    "id_to_vector_id": self._id_to_vector_id,
                    "vector_id_to_id": {str(k): v for k, v in self._vector_id_to_id.items()},
                    "deleted_vector_ids": list(self._deleted_vector_ids),
                },
                f,
            )

    def add(self, memory_id: str, embedding: list[float]) -> int:
        with file_lock(self._lock_path):
            index = self._ensure_index()
            vector = np.array([embedding], dtype=np.float32)
            faiss.normalize_L2(vector)
            vector_id = index.ntotal
            index.add(vector)
            self._id_to_vector_id[memory_id] = vector_id
            self._vector_id_to_id[vector_id] = memory_id
            if vector_id in self._deleted_vector_ids:
                self._deleted_vector_ids.discard(vector_id)
            self._save_mapping()
            faiss.write_index(index, str(self._index_path))
            logger.debug("Added vector %d for memory %s", vector_id, memory_id)
            return vector_id

    def search(
        self, embedding: list[float], limit: int = 10, threshold: float | None = None
    ) -> list[tuple[str, float]]:
        index = self._ensure_index()
        query = np.array([embedding], dtype=np.float32)
        faiss.normalize_L2(query)
        distances, indices = index.search(query, limit * 2)
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            if idx in self._deleted_vector_ids:
                continue
            if threshold is not None and dist < threshold:
                continue
            memory_id = self._vector_id_to_id.get(int(idx))
            if memory_id and memory_id not in self._deleted_vector_ids:
                results.append((memory_id, float(dist)))
            if len(results) >= limit:
                break
        return results

    def delete(self, memory_id: str) -> bool:
        with file_lock(self._lock_path):
            if memory_id not in self._id_to_vector_id:
                return False
            vector_id = self._id_to_vector_id[memory_id]
            self._deleted_vector_ids.add(vector_id)
            del self._id_to_vector_id[memory_id]
            if vector_id in self._vector_id_to_id:
                del self._vector_id_to_id[vector_id]
            self._save_mapping()
            faiss.write_index(self._ensure_index(), str(self._index_path))
            logger.debug("Deleted vector %d for memory %s", vector_id, memory_id)
            return True

    def get_vector_id(self, memory_id: str) -> int | None:
        if memory_id in self._deleted_vector_ids:
            return None
        return self._id_to_vector_id.get(memory_id)

    def count(self) -> int:
        index = self._ensure_index()
        return index.ntotal - len(self._deleted_vector_ids)

    def rebuild_index(self) -> None:
        with file_lock(self._lock_path):
            if self._index is None:
                return
            index = self._ensure_index()
            all_vectors = []
            id_mapping: dict[str, int] = {}
            vector_id_to_id: dict[int, str] = {}

            for memory_id, old_vector_id in list(self._id_to_vector_id.items()):
                if old_vector_id in self._deleted_vector_ids:
                    continue
                vec = faiss.downcast_vector(index.at(int(old_vector_id)))
                vec_np = faiss.vector_to_array(vec).reshape(1, -1)
                new_vector_id = len(all_vectors)
                all_vectors.append(vec_np[0])
                id_mapping[memory_id] = new_vector_id
                vector_id_to_id[new_vector_id] = memory_id

            new_index = faiss.IndexFlatIP(self._dimension)
            if all_vectors:
                new_index.add(np.array(all_vectors, dtype=np.float32))

            deleted_count = len(self._deleted_vector_ids)
            self._index = new_index
            self._id_to_vector_id = id_mapping
            self._vector_id_to_id = vector_id_to_id
            self._deleted_vector_ids.clear()
            self._save_mapping()
            faiss.write_index(new_index, str(self._index_path))
            logger.info("FAISS index rebuilt, removed %d orphaned vectors", deleted_count)
