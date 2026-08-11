"""LLM provider protocol for local and opt-in external implementations."""

from collections.abc import AsyncIterator
from typing import Protocol


class LLMProvider(Protocol):
    async def generate(self, prompt: str) -> str:
        """Generate one complete response."""

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        """Yield response fragments in order."""
