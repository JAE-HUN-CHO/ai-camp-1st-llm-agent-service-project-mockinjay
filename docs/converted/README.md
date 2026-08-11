# Converted requirements and reference documents

`docs/converted/` contains historical requirements, migration notes, and
vendor/reference material. They are not the current runtime contract.

For current behavior, use these sources in order:

1. Accepted ADRs in `docs/adr/` (including ADR-011 for the current runtime
   contract)
2. `AGENTS.md` and `docs/AGENTS.md`
3. `docs/agents/domain.md` and feature-specific current reports
4. Generated OpenAPI and passing route/parity tests

Older documents may mention OpenAI, Pinecone, payment flows, or
`new_frontend/` because they preserve earlier design decisions. Do not use
those references to configure or extend the current product.
