import os
import logging
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

ALLOWED_DATA_DIR_ROOTS = [Path.cwd(), Path("/tmp"), Path.home()]


def _validate_data_dir(path: Path) -> Path:
    resolved = path.resolve()
    for root in ALLOWED_DATA_DIR_ROOTS:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise ValueError(
        f"MEMORY_DATA_DIR must be within allowed paths: {[str(r) for r in ALLOWED_DATA_DIR_ROOTS]}"
    )


class Config(BaseModel):
    memory_user_id: str
    memory_data_dir: Path = Path("./data")
    embedding_provider: str
    embedding_model: str | None = None
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_dimension: int = Field(default=1536, ge=1)

    @property
    def faiss_index_path(self) -> Path:
        return self.memory_data_dir / "faiss_index"

    @property
    def sqlite_db_path(self) -> Path:
        return self.memory_data_dir / "memory.db"


_config: Config | None = None


def load_config() -> Config:
    global _config
    if _config is not None:
        return _config

    memory_user_id = os.environ.get("MEMORY_USER_ID")
    if not memory_user_id:
        raise ValueError("MEMORY_USER_ID environment variable is required")

    embedding_provider = os.environ.get("EMBEDDING_PROVIDER")
    if not embedding_provider:
        raise ValueError("EMBEDDING_PROVIDER environment variable is required")

    memory_data_dir_str = os.environ.get("MEMORY_DATA_DIR", "./data")
    memory_data_dir = _validate_data_dir(Path(memory_data_dir_str))

    embedding_model = os.environ.get("EMBEDDING_MODEL")
    embedding_api_key = os.environ.get("EMBEDDING_API_KEY")
    embedding_base_url = os.environ.get("EMBEDDING_BASE_URL")

    embedding_dimension_str = os.environ.get("EMBEDDING_DIMENSION", "1536")
    try:
        embedding_dimension = int(embedding_dimension_str)
        if embedding_dimension < 1:
            raise ValueError("EMBEDDING_DIMENSION must be positive")
    except ValueError:
        logger.warning(
            "Invalid EMBEDDING_DIMENSION '%s', using default 1536", embedding_dimension_str
        )
        embedding_dimension = 1536

    _config = Config(
        memory_user_id=memory_user_id,
        memory_data_dir=memory_data_dir,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        embedding_api_key=embedding_api_key,
        embedding_base_url=embedding_base_url,
        embedding_dimension=embedding_dimension,
    )

    _config.memory_data_dir.mkdir(parents=True, exist_ok=True)

    return _config


def get_config() -> Config:
    if _config is None:
        return load_config()
    return _config
