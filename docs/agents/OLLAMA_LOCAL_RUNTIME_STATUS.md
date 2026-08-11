# Ollama local runtime status

Checked 2026-08-12 without downloading data or changing model state.

## Configuration

- Chat model: `qwen3.6:27b-mlx`
- Embedding model: `nomic-embed-text-v2-moe`
- Base URL: `http://localhost:11434`
- Provider API keys: none in `.env` or `.env.example`
- Vector persistence target: local MongoDB vector search

## Installation check

`ollama list` reports both requested models as installed:

- `qwen3.6:27b-mlx` (19 GB)
- `nomic-embed-text-v2-moe:latest` (957 MB)

The local HTTP runtime is listening on `127.0.0.1:11434`. A generation smoke
request returned `LOCAL_OK` from `qwen3.6:27b-mlx`, and an embedding smoke request
returned one 768-wide vector from `nomic-embed-text-v2-moe`. The adapter's
documented 768-to-1536 compatibility step remains required before vector search.

The pinned `mongodb/mongodb-atlas-local:8.0.6` compose service reached `healthy`
and an authenticated `db.adminCommand({ping: 1})` returned `{ ok: 1 }`.

## Code verification

- Python compileall: passed
- Ollama adapter import/shape smoke: passed
- Backend tests: 56 passed, 10 integration/E2E tests deselected by the default unit profile
- Frontend: build passed; Vitest 29 files/406 tests passed; lint 0 errors (existing warnings remain)
- API contract: 6 required paths passed; frontend route/API/asset/test parity passed
- Static provider scan: no OpenAI, Anthropic, Pinecone, OpenRouter, or Cerebras imports/key reads remain in runtime/scripts

The repository-wide Ruff command remains a follow-up gate: the pre-existing tree reports
2,044 backend/app findings (3,369 when legacy scripts and agents are included). The
changed-file high-signal check (`E9`, undefined-name rules) passes; this debt is not a
provider/runtime failure and was not hidden by changing Ruff configuration.

The compatibility adapter expands the 768-wide Nomic output to the configured
1536-wide MongoDB index using a cosine-preserving duplication policy. Changing
that width or the MongoDB vector index requires a new ADR; Accepted ADR-005 is
not modified.
