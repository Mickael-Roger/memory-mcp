import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import get_config
from .file_lock import file_lock

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class MemoryRecord:
    id: str
    user_id: str
    text: str
    metadata: dict | None
    vector_id: int | None
    created_at: datetime
    updated_at: datetime


class SQLiteStore:
    _CREATE_TABLE = """
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            text TEXT NOT NULL,
            memory_metadata TEXT,
            vector_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """
    _CREATE_USER_IDX = "CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id)"
    _CREATE_CREATED_IDX = (
        "CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at)"
    )

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            db_path = get_config().sqlite_db_path
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @property
    def _lock_path(self) -> Path:
        return self._db_path.with_suffix(".lock")

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute(self._CREATE_TABLE)
            conn.execute(self._CREATE_USER_IDX)
            conn.execute(self._CREATE_CREATED_IDX)
            conn.commit()

    def add(
        self,
        text: str,
        user_id: str | None = None,
        metadata: dict | None = None,
        vector_id: int | None = None,
    ) -> MemoryRecord:
        if user_id is None:
            user_id = get_config().memory_user_id

        memory_id = str(uuid.uuid4())
        now = _utcnow().isoformat()

        with file_lock(self._lock_path):
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT INTO memories (id, user_id, text, memory_metadata, vector_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        memory_id,
                        user_id,
                        text,
                        json.dumps(metadata) if metadata else None,
                        vector_id,
                        now,
                        now,
                    ),
                )
                conn.commit()

        return MemoryRecord(
            id=memory_id,
            user_id=user_id,
            text=text,
            metadata=metadata,
            vector_id=vector_id,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )

    def get(self, memory_id: str) -> MemoryRecord | None:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM memories WHERE id = ?",
                (memory_id,),
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_record(row)
            return None

    def get_many(
        self,
        user_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[MemoryRecord], int]:
        if user_id is None:
            user_id = get_config().memory_user_id
        if offset < 0:
            raise ValueError("offset must be non-negative")

        with self._get_conn() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE user_id = ?",
                (user_id,),
            ).fetchone()[0]

            cursor = conn.execute(
                "SELECT * FROM memories WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (user_id, limit, offset),
            )
            rows = cursor.fetchall()
            records = [self._row_to_record(row) for row in rows]

        return records, total

    def update(
        self, memory_id: str, text: str, metadata: dict | None = None
    ) -> MemoryRecord | None:
        with file_lock(self._lock_path):
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "SELECT * FROM memories WHERE id = ?",
                    (memory_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None

                now = _utcnow().isoformat()
                conn.execute(
                    "UPDATE memories SET text = ?, memory_metadata = ?, updated_at = ? WHERE id = ?",
                    (text, json.dumps(metadata) if metadata is not None else None, now, memory_id),
                )
                conn.commit()

                cursor = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
                row = cursor.fetchone()
                if row:
                    return self._row_to_record(row)
                return None

    def delete(self, memory_id: str) -> bool:
        with file_lock(self._lock_path):
            with self._get_conn() as conn:
                cursor = conn.execute("SELECT id FROM memories WHERE id = ?", (memory_id,))
                if not cursor.fetchone():
                    return False
                conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
                conn.commit()
                return True

    def get_by_vector_id(self, vector_id: int) -> MemoryRecord | None:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM memories WHERE vector_id = ?",
                (vector_id,),
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_record(row)
            return None

    def update_vector_id(self, memory_id: str, vector_id: int) -> None:
        with file_lock(self._lock_path):
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE memories SET vector_id = ? WHERE id = ?",
                    (vector_id, memory_id),
                )
                conn.commit()

    def _row_to_record(self, row) -> MemoryRecord:
        metadata = None
        if row["memory_metadata"]:
            try:
                metadata = json.loads(row["memory_metadata"])
            except json.JSONDecodeError as e:
                logger.error(
                    "Failed to decode metadata for memory %s: %s",
                    row["id"],
                    str(e),
                )
        return MemoryRecord(
            id=row["id"],
            user_id=row["user_id"],
            text=row["text"],
            metadata=metadata,
            vector_id=row["vector_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
