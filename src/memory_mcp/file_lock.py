import fcntl
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)


class FileLock:
    def __init__(self, lock_path: Path):
        self._lock_path = lock_path
        self._lock_file = None

    def __enter__(self):
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_file = open(self._lock_path, "w")
        fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX)
        logger.debug("Acquired lock: %s", self._lock_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._lock_file:
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
            self._lock_file.close()
            self._lock_file = None
        logger.debug("Released lock: %s", self._lock_path)
        return False

    @property
    def lock_path(self) -> Path:
        return self._lock_path


@contextmanager
def file_lock(lock_path: Path | str) -> Iterator[None]:
    lock_path = Path(lock_path)
    with FileLock(lock_path) as lock:
        yield
