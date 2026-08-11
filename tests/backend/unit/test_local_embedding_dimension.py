"""Local embedding providers must not emit vectors incompatible with ADR-005."""

import asyncio

import numpy as np
import pytest

from backend.Agent.research_paper.server.nlp_service import TextEmbedding3SmallEmbedder


def _embedder(model: str = "test-local", dimensions: int = 1536) -> TextEmbedding3SmallEmbedder:
    instance = TextEmbedding3SmallEmbedder.__new__(TextEmbedding3SmallEmbedder)
    instance.dimensions = dimensions
    instance.local_model_name = model
    instance.local_cache_model = f"local/{model}/{dimensions}d"
    instance.cache = None
    instance.cache_hits = 0
    instance.total_local_calls = 0
    return instance


def test_local_embedding_dimension_guard_rejects_incompatible_vectors() -> None:
    embedder = _embedder()

    with pytest.raises(ValueError, match="returned 768 dimensions"):
        embedder._validate_vector_dimension(np.zeros((1, 768)))


def test_local_embedding_dimension_guard_accepts_atlas_width() -> None:
    embedder = _embedder()

    embedder._validate_vector_dimension(np.zeros((2, 1536)))


def test_local_embedding_path_fails_closed_before_returning_wrong_vectors() -> None:
    embedder = _embedder()

    class WrongWidthProvider:
        async def embed(self, *_args, **_kwargs):
            return [np.zeros(768).tolist()]

    embedder._ollama_provider = WrongWidthProvider()
    with pytest.raises(ValueError, match="returned 768 dimensions"):
        asyncio.run(embedder._embed_local(["kidney diet"]))
