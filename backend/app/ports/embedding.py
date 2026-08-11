"""Embedding provider protocol used by research/vector features."""

from collections.abc import Sequence
from typing import Protocol


class EmbeddingProvider(Protocol):
    dimensions: int

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one vector per input text at the configured width."""
