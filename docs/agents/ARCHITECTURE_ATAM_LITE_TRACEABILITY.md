# Phase 0 ATAM-lite risk and traceability matrix

**Scope:** CareGuide Phase 0–1 only
**Decision boundary:** ADR-013 is Accepted; Phase 2 Chat is the only authorized next slice.

| Risk | Quality scenario / stimulus | Response and measurable threshold | Test / command | Artifact | Owner / sensitivity / tradeoff |
|---|---|---|---|---|---|
| R-01 ClinicalTrials generated interpretation harms a patient | A user requests one trial detail in Korean | original fields remain distinct; translation is faithful; source + disclaimer present; generated interpretation/recommendation count 0; contract 100% | `test_detail_contract_preserves_source_and_forbids_generated_interpretation` | `unit.junit.xml`, clinical contract source | research; medical safety highest; less convenient summary |
| R-02 emergency query reaches a model/Agent/provider | Any message/stream/proxy contains gold-set emergency language | deterministic terminal emergency response; false negative 0; downstream call count 0 | emergency policy + Ollama endpoint/Agent tests | `eval/safety-summary.json`, unit JUnit | chat safety owner; favors high recall over precision |
| R-03 cross-user room/session/health mutation | JWT actor supplies another actor's resource ID | reject before model/DB mutation; cross-user cases 100%; unauthorized write 0 | `test_actor_context.py`, health mutation tests | `unit.junit.xml` | chat/health; authorization over permissive recovery |
| R-04 token/chat/health PII escapes | Canary appears in storage, console, application log or evidence writer | zero canary occurrences in all four sinks | logging canary + frontend static/runtime tests + artifact validator | `pii/canary.json`, frontend test output | platform; observability loses raw payloads |
| R-05 false Parlant readiness | Port returns 404/HTML/wrong agent | readiness true only for 200 JSON schema with target id/name | readiness unit tests + live smoke | `http/research.json`, `http/welfare.json` | welfare/research; stricter startup may delay availability |
| R-06 HTTP flow hangs or reports false success | provider never terminates or SSE emits error then DONE | bounded timeout; non-zero exit; terminal success frame and `[DONE]` recorded separately | both smoke scripts | HTTP JSON/NDJSON + manifest exit code | runtime; bounded wait over optimistic demo |
| R-07 hosted provider silently activates | local provider is unavailable | no hosted fallback; fail non-zero; hosted call count 0 | configuration/static scan + live smoke | manifest environment/provider fields | platform; availability sacrificed for local-only contract |
| R-08 architecture inventory drifts | route or import changes | full registered route JSON and AST gate regenerated on same SHA; enforced violations 0 | inventory + dependency scripts | `architecture/*.json` | architecture owner; legacy remains visible debt |
| R-09 dirty worktree makes result irreproducible | verification occurs without commit by explicit instruction | manifest keeps HEAD SHA, exact argv/exit/timestamps and worktree fingerprint | manifest wrapper | `manifest.json` | executor; fingerprint supplements immutable SHA |
| R-10 local Mongo/Ollama/Parlant absent | integration run starts with missing component | stop within timeout, record last success/error/next action, do not claim HTTP complete | explicit integration and live smoke | component/HTTP artifacts | runtime owner; honest partial result |

## Sensitivity points and non-risks

- Emergency phrase breadth is a sensitivity point: narrowing it reduces false
  positives but increases catastrophic false negatives. Phase 0 selects high recall.
- ActorContext ordering is a sensitivity point: owner checks occur before context,
  model, Agent or provider calls. Emergency filtering may run first because it is
  deterministic and makes no external call.
- Readiness agent names and JSON envelope are sensitivity points. A mere listening
  socket, 404, HTML page, initialized SDK client or adapter construction is not ready.
- SSE `[DONE]` is transport termination, not success. A separate terminal success
  frame is required; error + DONE remains failure.
- Public ClinicalTrials text caching and non-sensitive feature flags are not PII
  storage risks. Tokens, authenticated user/chat state and health data are.
- The existing local-only architecture and five capability names are constraints,
  not architecture risks to be optimized away.

## P0 abuse cases

1. Supply another user's `user_id`, room, session or health record identifier.
2. Put emergency text in every public chat entrypoint, including transparent proxies.
3. Put email/JWT/health canaries in logger interpolation and provider exceptions.
4. Return 404 or 200 HTML from a Parlant port to trigger false readiness.
5. Emit SSE error followed by `[DONE]` to trigger false success.
6. Use a non-loopback URL or credential on a smoke command line.
7. Try to reintroduce generated ClinicalTrials significance/recommendations.

Every abuse case is fail-closed in Phase 0–1 or produces a non-zero verification
result. No destructive schema operation is part of a response.
