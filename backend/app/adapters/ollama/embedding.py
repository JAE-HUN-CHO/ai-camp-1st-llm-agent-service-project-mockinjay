"""Ollama embedding adapter with an explicit 1536d compatibility policy."""

from __future__ import annotations

import math
import os
from collections.abc import Sequence

import httpx


def expand_vector_losslessly(vector: Sequence[float], target_dimensions: int) -> list[float]:
    """Expand a vector while preserving cosine similarity exactly.

    A vector can be duplicated and divided by ``sqrt(2)`` when the target is
    exactly twice its source width. Dot products and norms receive the same
    scale factor, so cosine similarity is unchanged. Other width conversions
    fail closed instead of silently padding or truncating semantic data.
    """

    values = [float(value) for value in vector]
    source_dimensions = len(values)
    if source_dimensions == target_dimensions:
        return values
    if source_dimensions == 0 or target_dimensions != source_dimensions * 2:
        raise ValueError(
            f"Cannot adapt Ollama embedding from {source_dimensions} to {target_dimensions} dimensions"
        )
    scale = 1 / math.sqrt(2)
    return [value * scale for value in values] * 2


class OllamaEmbeddingProvider:
    """Async provider for Ollama's ``/api/embed`` endpoint."""

    def __init__(
        self,
        model: str = "nomic-embed-text-v2-moe",
        dimensions: int = 1536,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.model = model
        self.dimensions = dimensions
        self.base_url = (base_url or os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")).rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await self._client.post(
            f"{self.base_url}/api/embed",
            json={"model": self.model, "input": list(texts)},
        )
        response.raise_for_status()
        payload = response.json()
        raw_embeddings = payload.get("embeddings")
        if not isinstance(raw_embeddings, list) or len(raw_embeddings) != len(texts):
            raise ValueError("Ollama returned an invalid embedding batch")
        return [expand_vector_losslessly(vector, self.dimensions) for vector in raw_embeddings]

    async def close(self) -> None:
        await self._client.aclose()
