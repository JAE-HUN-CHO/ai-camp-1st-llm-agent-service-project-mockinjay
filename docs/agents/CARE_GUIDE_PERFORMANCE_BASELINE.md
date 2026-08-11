# CareGuide performance baseline

Date: 2026-08-12

This is a measurement record for the reorganization gate. It deliberately
separates measurements that can run deterministically in this repository from
provider-dependent measurements that still require a benchmark environment.

## Verified measurements

| Surface | Measurement | Result | Evidence |
|---|---|---:|---|
| Frontend artifact | `frontend/dist` size after production build | 1.7 MiB | `du -sh frontend/dist` |
| Frontend artifact | Largest Vite chunk | ~610 KiB warning | `frontend` build output (`TrendsPageEnhanced`) |
| Frontend delivery | HTTP SPA route smoke | 6/6 pass | `pytest -q tests/e2e/test_frontend_delivery.py` |
| Backend deterministic path | Unit suite | 42 pass | `pytest -q` after stream/index contract coverage |
| Cache behavior | Clinical-trial hit, key isolation, expiry, stale fallback | 4/4 pass | `tests/backend/unit/test_clinical_trial_cache.py` |
| Vector runtime | Atlas Local vector index | READY, 1536d cosine | `test_mongo_vector_runtime.py` with Atlas Local 8.0.6 |
| Mongo room/history indexes | Idempotent index creation and live listing | 4 named indexes present | `create_chat_indexes` against Atlas Local |
| Chat stream contract overhead | 25 fake-adapter HTTP/SSE requests | p50 0.451 ms; p95 0.760 ms | `scripts/benchmark_runtime.py`, `eval/performance_baseline.json` |
| Local generation | Ollama `qwen2.5:0.5b`, 5 iterations | p50 184.492 ms; p95 1309.939 ms | `scripts/benchmark_local_providers.py`, `eval/local_provider_performance.json` |
| Local embedding | Ollama `nomic-embed-text`, lossless 768d→1536d adapter | p50 26.041 ms; p95 154.907 ms | `eval/local_provider_performance.json` |
| Indexed Mongo room list | Atlas Local, 100-room synthetic fixture | p50 0.607 ms; p95 0.764 ms | `scripts/benchmark_mongodb_queries.py`, `eval/mongodb_query_performance.json` |
| Indexed Mongo history lookup | Atlas Local, five histories per room | p50 0.470 ms; p95 0.596 ms | `eval/mongodb_query_performance.json` |
| Frontend preview delivery | Vite preview, 30 requests across six routes | p50 0.437 ms; p95 1.139 ms | `scripts/benchmark_frontend_delivery.py`, `eval/frontend_delivery_performance.json` |
| Browser navigation/paint | Headless Chrome CDP, six canonical routes | FCP 84–436 ms | `scripts/profile_frontend_browser.py`, `eval/frontend_browser_profile.json` |

## Query and cache review

- The room list path performs one `conversation_history.find_one` per returned
  room to enrich the last message. This remains a known N+1 candidate; the
  new `(room_id, timestamp)` index bounds each lookup while an aggregation
  replacement is deferred until a representative query-plan comparison.
- The live Mongo index smoke proves the required vector index is queryable. A
  full `explain()` capture for every feature query is not yet available.
- Provider-computation caches have deterministic key/TTL/stale-fallback tests
  for clinical trials. Redis-backed research cache remains opt-in and was not
  started in the local runtime.

## Measurements intentionally deferred

- LLM token latency and provider-backed chat stream p50/p95: the local provider
  benchmark covers Ollama request latency, but not streamed token cadence or
  end-to-end persistence.
- Frontend interaction/rerender profiling: the Chrome artifact covers
  navigation and first paint, not a full interaction trace.
- Mongo query p95/N+1 proof: the fixture benchmark is indexed and synthetic;
  representative production-volume `explain()` captures remain deferred.

`scripts/benchmark_runtime.py` provides a repeatable local baseline for the
deterministic route contract. Provider-backed measurements remain MEDIUM
follow-ups and must be rerun with representative fixtures before production
capacity decisions.
