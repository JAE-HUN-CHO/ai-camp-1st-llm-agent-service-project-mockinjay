"""Vector store protocol independent of the MongoDB adapter implementation."""

from collections.abc import Sequence
from typing import Protocol


class VectorStore(Protocol):
    dimensions: int

    async def search(self, vector: Sequence[float], limit: int = 10) -> list[dict]:
        """Search by a vector and return provider-neutral records."""
