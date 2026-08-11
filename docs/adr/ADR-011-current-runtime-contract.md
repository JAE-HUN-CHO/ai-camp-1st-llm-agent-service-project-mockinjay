# ADR-011: Current Runtime and Product Contract

- **Status:** Accepted
- **Date:** 2026-08-12
- **Supersedes:** the Proposed frontend/runtime direction in ADR-001, ADR-008, ADR-009, and ADR-010
- **Related:** ADR-004, ADR-005, ADR-006

## Context

The repository was consolidated after the original ADR proposals were written.
The product source is now `frontend/`, the runtime is local-first, and the
checked-in environment examples intentionally contain no hosted-model or vector
provider credentials. Existing historical documents still describe the former
`new_frontend`, OpenAI, and Pinecone arrangements.

## Decision

1. `frontend/` is the only product frontend. `new_frontend/` and
   `stitch_frontend/` are historical rollback material under `logs/rollback/`
   and must not receive new product features.
2. Ollama is the only default model provider:
   - generation: `qwen3.6:27b-mlx`
   - embedding: `nomic-embed-text-v2-moe`
   - endpoint: `http://localhost:11434`
3. MongoDB Atlas Local is the local database/vector runtime. The accepted
   ADR-005 vector contract remains 1536 dimensions with cosine similarity.
   The Ollama adapter validates dimensions and may apply the documented
   cosine-preserving 768-to-1536 expansion; incompatible vectors fail closed.
4. The runtime currently exposes five registered agent capabilities:
   `medical_welfare`, `research_paper`, `nutrition`, `quiz`, and
   `trend_visualization`.
5. Hosted providers and payment integrations remain opt-in/out of scope,
   respectively. No provider key is required by `.env.example`.

## Consequences

- Current setup and API documents must reference `frontend/`, Ollama, and local
  MongoDB. Historical plans may retain old terms only when clearly labeled as
  historical/reference material.
- The contract is checked by route/parity tests, environment scans, and local
  runtime smoke tests.
- Accepted ADR-004, ADR-005, and ADR-006 remain unchanged.
