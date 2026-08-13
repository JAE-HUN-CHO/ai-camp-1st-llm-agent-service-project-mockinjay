# ADR-012: Notification Delivery Outbox and Explicit Ollama Toggle

- **Status:** Proposed
- **Date:** 2026-08-13
- **Related:** ADR-011

## Context

Community comments and likes complete their primary database writes before a
notification is delivered. A provider failure must not turn that successful
operation into a retry-prone HTTP 500, but it also must not be silently lost.
The chat API also needs an explicit contract for whether the application-scoped
Ollama service is available so the legacy router path remains testable.

## Decision

1. Failed community notification deliveries are recorded in the
   `notification_outbox` collection with the serialized payload, status,
   attempt count, error, and next retry time.
2. A bounded application-lifespan worker retries due outbox events with
   exponential backoff and marks successful deliveries as `delivered`.
   Primary community writes remain successful when delivery and outbox
   recording are unavailable; the failure is logged for operational visibility.
3. `OLLAMA_ENABLED` is an explicit runtime toggle. It defaults to enabled to
   preserve ADR-011's local-first behavior. When disabled, `AgentRuntime.chat_service`
   returns `None` and chat routes may use their existing router fallback.

## Consequences

- Notification delivery is eventually consistent and retryable without
  duplicating the user-visible comment or like operation.
- The outbox worker is process-local; deployments requiring multi-process
  delivery must add a distributed lease or external queue before scaling out.
- Ollama remains the default provider, while tests and local fallback scenarios
  can explicitly disable it without relying on a truthy service property.
