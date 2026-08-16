# CareGuide 다음 작업 체크리스트

## 완료

- [x] Phase 0 안전·소유권·privacy·architecture inventory
- [x] Phase 1 Research/Welfare/Chat local HTTP evidence
- [x] ADR-013 Accepted와 aggregate/capability/selector/process owner 결정

## 승인된 다음 범위 — Phase 2 Chat

- [ ] REST/SSE v1 characterization fixture 작성
- [ ] Chat domain/application/port seam 구현
- [ ] MongoDB/Ollama/legacy Agent adapter 조립
- [ ] `CHAT_IMPLEMENTATION=legacy|hex`, 기본값 `legacy`
- [ ] ActorContext·EmergencySafetyPolicy 선행 gate 유지
- [ ] legacy/hex parity, cross-user, error/cancel/idempotency tests
- [ ] legacy/new telemetry와 rollback drill
- [ ] local MongoDB + Ollama message/stream 실제 HTTP artifact
- [ ] Ruff, backend unit/integration, frontend test/build/lint
- [ ] doc links, architecture imports, PII scan, `git diff --check`
- [ ] 동일 SHA·run-id manifest와 최종 Phase 2 보고

## 금지/보류

- [ ] Phase 3 Health는 별도 승인 전 시작하지 않음
- [ ] RemoteAgent/compatibility facade는 telemetry 확인 전 삭제하지 않음
- [ ] hosted/paid provider와 결제 기능을 추가하지 않음
- [ ] 기존 REST/SSE v1 계약을 Phase 2에서 변경하지 않음
