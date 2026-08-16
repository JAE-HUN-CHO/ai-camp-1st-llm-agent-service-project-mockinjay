# Phase 0 architecture inventory and owner decisions

**Status:** Phase 0 evidence used to accept ADR-013
**Base snapshot:** `fda93b9dbb8107ecbffa593041c9417f822a6688`
**Post-gate evidence:** run `20260815T143102Z`, worktree fingerprint
`d5f1f73380f1f107e6ed2861032fc89b929f32553e5fe5ee3145a85fa45dfb04`
**Canonical runtime:** `frontend/` → `backend/app/main.py:app` → local Ollama/local Docker MongoDB

This document records the implementation found by reading the accepted ADRs and
then re-checking the registered FastAPI graph, Python imports, entrypoints and tests.
The machine-readable full route list is produced by
`scripts/inventory_architecture.py`; it contained 137 registered routes at the
Phase 0 baseline. Generated JSON is stored in the verification run directory.
The local manifest is
`logs/verification/fda93b9dbb8107ecbffa593041c9417f822a6688/20260815T143102Z/manifest.json`.
Because `logs/` is ignored, this inventory identifies the verified dirty worktree by base SHA, run ID,
and fingerprint together; it does not claim that the base commit alone contains the post-gate state.

## Route → service/runtime → schema/storage → test inventory

| Route family | Actor/resource owner | Service/runtime path | Schema or collection | Contract/evidence test |
|---|---|---|---|---|
| `/api/auth/*`, `/api/users/*` | JWT actor / UserAccount | auth/user service | `users` | `test_auth_*`, `test_account_deletion.py` |
| `/api/chat/message`, `/api/chat/stream` | JWT actor + ActorContext room/session | EmergencySafetyPolicy → `AgentRuntime`; default `OllamaChatService`, compatibility RouterAgent | request JSON; `conversation_history`, `chat_rooms` | `test_ollama_chat_endpoints.py`, `test_chat_stream_contract.py`, `test_actor_context.py` |
| `/api/chat/rooms*`, `/api/chat/history*` | JWT actor + room/session owner | context system / DB manager | `chat_rooms`, `conversation_history` | `test_room_ownership.py`, `test_rooms_*` |
| `/api/chat/{research,welfare}/*` | JWT actor + ActorContext before proxy | authenticated local Parlant proxy | Parlant customer/session/event IDs | `smoke_parlant_http.py`, `smoke_api_chat.py` |
| `/api/health-records/*` | JWT actor / HealthRecord | endpoint + Motor boundary | `health_records` | `test_health_record_db_async.py`, `test_health_record_contract.py` |
| `/api/mypage/health*` | JWT actor / HealthProfile | mypage service | `health_profiles` | API contract tests |
| dormant `/api/health*` | health; no merge authorized | legacy repository | separate legacy shape | no new writes until Phase 3 decision |
| `/api/community/*` | JWT actor / Post, Comment, Like | community router/service | posts/comments/likes/outbox | community/cache/notification tests |
| `/api/diet-care/*`, `/api/nutrition/*` | JWT actor / DietLog | diet-care service + Nutrition capability | diet/nutrition collections | diet API/recipe/nutrition tests |
| `/api/quiz/*`, points routes | JWT actor / Quiz + PointLedger | Quiz agent and points service | `user_points`, `point_transactions` | quiz/points idempotency tests |
| `/api/research*`, trend routes | JWT actor / Research | local Research agent, PubMed adapters | paper/vector/cache collections | agent runtime/vector tests |
| `/api/clinical-trials/list`, `/detail` | public information / ClinicalTrialsInformation | ClinicalTrials.gov adapter; local Ollama only for faithful field translation | source fields + source URL + disclaimer; `clinical_trials_cache` | `test_clinical_trial_cache.py` |
| notifications | JWT actor / Notification | notification service + in-process outbox worker | notifications/outbox | `test_notification_outbox.py` |

The JSON inventory additionally records method, exact path, endpoint symbol,
response model, declared dependency and expected content type for every route.
Unversioned chat aliases are explicitly present: JSON/SSE `/message`, SSE
`/stream`, rooms/history, and three catch-all proxy routes.

## Capability, port, adapter and Agent mapping

| Capability | Application owner | Inbound | Outbound / runtime | Fake test | Real smoke | Phase 0 classification |
|---|---|---|---|---|---|---|
| Chat / `ollama_rag` | chat | REST/SSE | local Ollama + local Mongo vector | Ollama endpoint/service tests | `smoke_api_chat.py` | keep; default legacy implementation |
| Medical welfare | welfare capability, chat facade | REST/SSE/proxy | `MedicalWelfareAgent` → local Parlant 8801 | emergency/readiness tests | `smoke_parlant_http.py` | keep compatibility client |
| Research paper | research | REST/SSE/proxy | `ResearchPaperAgent` → local Parlant 8800 | emergency/readiness tests | `smoke_parlant_http.py` | keep compatibility client |
| Nutrition | diet migration owner, nutrition public name | REST/Agent | local Mongo/Ollama | nutrition tests | later runtime smoke | delegate toward `diet` in its approved future slice |
| Quiz | quiz; points mutations owned by rewards | REST/Agent | local Mongo | quiz/points tests | later runtime smoke | keep, remove raw DB only in Phase 6 |
| Trend visualization | research | REST/Agent | local Mongo/PubMed | research/vector tests | later runtime smoke | delegate toward research |
| ClinicalTrials information | research | REST | ClinicalTrials.gov + faithful local translation | source contract test | provider/API smoke later | interpretation deleted |

`app/features/chat/runtime.py` and `research/runtime.py` are in use. Other
`app/features/*` packages are naming anchors. `app/ports/{llm,embedding,vector,external_search}.py`
are defined contracts without complete production wiring. Ollama adapters are in
use or extension seams; empty Mongo/cache adapter packages are defined-only.
This is not evidence of a completed hexagonal migration.

## Aggregate owner and vocabulary decisions for ADR-013 review

These Phase 0 owner decisions are incorporated into Accepted ADR-013. They
authorize no destructive schema migration.

| Concept | Canonical owner / vocabulary | Decision |
|---|---|---|
| account | UserAccount / `users` | account owns identity and authentication |
| health records | HealthRecord / `health_records` | keep distinct from profile and dormant health shape |
| health profile | HealthProfile / `health_profiles` | keep distinct; no collection merge |
| chat | ChatRoom + ChatSession / `chat_rooms`, `conversation_history` | ActorContext owns authorization before DB/model/provider |
| rewards | PointLedger / current `user_points`, `point_transactions` | rewards owns mutation policy; additive migration only after approval |
| research quota | DailySearchQuota / intended `daily_search_counter` | research owns it; currently absent, so no implementation claim |
| clinical trials | ClinicalTrialsInformation / `clinical_trials_cache` | source-backed information and faithful translation only |
| diet/nutrition | `diet` feature owner, `nutrition` public capability | delegate gradually; preserve both public contracts |

Additional keep/delegate/delete decisions:

- `ollama_rag`: **keep** as default legacy chat implementation.
- generic `Agent/core/remote_agent.py`: **retain/deprecate**, because it has no
  proven runtime consumer; do not delete before telemetry and usage proof.
- Research/Welfare SDK clients: **keep separately** from raw proxy and customer
  lifecycle service until Phase 4 contract comparison.
- Parlant proxy: **keep as compatibility facade**, never a readiness signal.
- `CHAT_IMPLEMENTATION=legacy|hex`: selector is **designed but not implemented**;
  evaluation belongs in the Phase 2 composition root and defaults to `legacy`.

## Import rule and rollback registry

`scripts/check_architecture_dependencies.py` is the Phase 0 AST gate. It forbids
FastAPI, Motor/PyMongo, Parlant/Ollama SDK, DB and concrete adapter imports from
new `features/*/{domain,application,ports}.py` and `app/ports/*`, and forbids
cross-feature implementation imports. Existing legacy files remain inventory-only
until each file enters an approved slice migration; silently declaring the whole
legacy tree compliant would be a false gate.

Rollback in Phase 0 is file-level and behavior preserving: remove the new safety
facade only if its contract tests fail, retain all existing schema/data, and do
not touch untracked `data/`. Phase 2 selector work was outside this Phase 0 inventory run and is
now the separately authorized next execution scope.

## Sensitive data and local-only inventory

- Access tokens and authenticated user/chat state are memory-only in `frontend/`;
  legacy localStorage keys are deletion-only.
- Raw chat frames, user objects, tokens and health API error objects are not
  written to console by the affected canonical paths.
- application logging redacts named sensitive fields, email, Bearer/JWT tokens
  and PII canaries before console/file handlers.
- Evidence artifacts store status, hashes, lengths and IDs, never raw prompts,
  model responses, email, health details or bearer credentials.
- Hosted/paid provider fallback and payment capability remain prohibited.

## Reproduction

```bash
PYTHONPATH=backend .venv/bin/python scripts/inventory_architecture.py --output <run>/architecture/routes.json
.venv/bin/python scripts/check_architecture_dependencies.py --output <run>/architecture/import-rules.json
```

See [`ARCHITECTURE_ATAM_LITE_TRACEABILITY.md`](./ARCHITECTURE_ATAM_LITE_TRACEABILITY.md)
for risk-to-scenario-to-test-to-artifact traceability.
