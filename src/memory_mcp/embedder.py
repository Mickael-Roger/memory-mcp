import ipaddress
import logging
from abc import ABC, abstractmethod
from urllib.parse import urlparse

import requests

from .config import get_config

logger = logging.getLogger(__name__)

BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def validate_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed.")
    host = parsed.hostname.lower() if parsed.hostname else ""
    if host in BLOCKED_HOSTS:
        raise ValueError(f"Blocked host: {host}")
    try:
        addr = ipaddress.ip_address(host)
        if addr.is_loopback or addr.is_private:
            raise ValueError(f"Blocked IP address: {addr}")
    except ValueError:
        pass
    return base_url.rstrip("/")


class Embedder(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        pass


class OpenAIEmbedder(Embedder):
    def __init__(self, api_key: str, model: str, dimension: int):
        self._api_key = api_key
        self._model = model
        self._dimension = dimension

    def embed(self, text: str) -> list[float]:
        embeddings = self.embed_batch([text])
        return embeddings[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)
        response = client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [item.embedding for item in response.data]


class OllamaEmbedder(Embedder):
    def __init__(self, base_url: str, model: str, dimension: int):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dimension = dimension

    def embed(self, text: str) -> list[float]:
        embeddings = self.embed_batch([text])
        return embeddings[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        validate_url(self._base_url)
        response = requests.post(
            f"{self._base_url}/api/embeddings",
            json={"model": self._model, "input": texts},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and "embeddings" in data:
            return data["embeddings"]
        return [data.get("embedding", [])] if isinstance(data, dict) else data


class HuggingFaceEmbedder(Embedder):
    def __init__(self, base_url: str, model: str, dimension: int, api_key: str | None = None):
        if not base_url:
            raise ValueError("EMBEDDING_BASE_URL is required for HuggingFace embedder")
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dimension = dimension
        self._api_key = api_key

    def embed(self, text: str) -> list[float]:
        embeddings = self.embed_batch([text])
        return embeddings[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        validate_url(self._base_url)
        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        response = requests.post(
            f"{self._base_url}",
            headers=headers,
            json={"inputs": texts, "model": self._model},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return data
        return [data.get("embedding", [])] if isinstance(data, dict) else data


def create_embedder() -> Embedder:
    config = get_config()
    provider = config.embedding_provider.lower()
    dimension = config.embedding_dimension

    if provider == "openai":
        if not config.embedding_api_key:
            raise ValueError("EMBEDDING_API_KEY is required for OpenAI embedder")
        return OpenAIEmbedder(
            api_key=config.embedding_api_key,
            model=config.embedding_model or "text-embedding-3-small",
            dimension=dimension,
        )
    elif provider == "ollama":
        if not config.embedding_base_url:
            raise ValueError("EMBEDDING_BASE_URL is required for Ollama embedder")
        return OllamaEmbedder(
            base_url=config.embedding_base_url,
            model=config.embedding_model or "nomic-embed-text",
            dimension=dimension,
        )
    elif provider == "huggingface":
        if not config.embedding_base_url:
            raise ValueError("EMBEDDING_BASE_URL is required for HuggingFace embedder")
        return HuggingFaceEmbedder(
            base_url=config.embedding_base_url,
            model=config.embedding_model or "sentence-transformers/all-MiniLM-L6-v2",
            dimension=dimension,
            api_key=config.embedding_api_key,
        )
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")
