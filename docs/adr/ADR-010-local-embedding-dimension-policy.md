# ADR-010: Local Embedding Dimension Compatibility

- **Status:** Superseded by ADR-011
- **Date:** 2026-08-11
- **Related:** ADR-005, ADR-009

## Context

ADR-005 fixes the local MongoDB vector index at 1536 dimensions with cosine similarity. The local-first smoke path is operational, but the installed Ollama `nomic-embed-text` model returns 768 dimensions. Returning those vectors to the 1536-dimensional index would produce invalid queries or silently corrupt the retrieval contract.

## Decision

The embedding adapter must validate the configured vector width for both fresh and cached local vectors. When a local model returns exactly half of the configured width, the Ollama adapter may apply a documented lossless duplicate-and-scale expansion: `[v, v] / sqrt(2)`. This preserves cosine similarity exactly while satisfying the fixed schema. All other mismatches fail closed. Local generation remains the default adapter path, while provider selection and model replacement remain opt-in. Cache namespaces include model and width so vectors from an incompatible prior model cannot be reused accidentally.

This proposal does not alter ADR-005's accepted index schema. A local 1536-dimensional model may be adopted later only after a separate compatibility and retrieval-quality verification.

## Consequences

- Invalid local vectors are rejected before reaching MongoDB Vector Search.
- Ollama `nomic-embed-text` (768d) can serve the 1536d index through the cosine-preserving expansion; retrieval quality must still be evaluated against representative documents.
- Cache entries are naturally invalidated when model or dimension configuration changes.
