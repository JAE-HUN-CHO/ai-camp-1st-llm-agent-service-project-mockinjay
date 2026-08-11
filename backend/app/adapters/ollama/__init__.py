"""Ollama local-model adapters."""

from .embedding import OllamaEmbeddingProvider, expand_vector_losslessly

__all__ = ["OllamaEmbeddingProvider", "expand_vector_losslessly"]
