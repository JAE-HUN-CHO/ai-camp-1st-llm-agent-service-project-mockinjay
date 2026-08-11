# Ollama local runtime status

Checked 2026-08-12 without starting a model, downloading data, or running an
inference request.

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

The HTTP health endpoint was not reachable from this session, so chat and
embedding smoke requests were intentionally not run. Start the local Ollama
daemon/model process before running the integration smoke scripts; `ollama ps`
currently reports no running model.

## Code verification

- Python compileall: passed
- Ollama adapter import/shape smoke: passed
- Backend unit tests: 45 passed
- Backend test collection: 40 deselected integration/E2E tests (no live model or database was started)
- Static provider scan: no OpenAI, Anthropic, Pinecone, OpenRouter, or Cerebras imports/key reads remain in runtime/scripts

The compatibility adapter expands the 768-wide Nomic output to the configured
1536-wide MongoDB index using a cosine-preserving duplication policy. Changing
that width or the MongoDB vector index requires a new ADR; Accepted ADR-005 is
not modified.
