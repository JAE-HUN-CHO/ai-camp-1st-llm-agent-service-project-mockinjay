"""External research search protocol."""

from typing import Protocol


class ExternalSearchProvider(Protocol):
    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """Fetch normalized research records from an external provider."""
