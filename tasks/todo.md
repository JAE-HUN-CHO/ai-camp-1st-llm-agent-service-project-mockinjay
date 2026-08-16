# CareGuide 1~5 실행 체크리스트

## Phase 1 — Parlant HTTP

- [ ] 1.1 Parlant lock/모델/Mongo/포트 사전 점검
- [ ] 1.2 Research Parlant customer/session/message 실제 테스트
- [ ] 1.3 Medical Welfare Parlant customer/session/message 실제 테스트
- [ ] Checkpoint 1 통과 및 증거 기록

## Phase 2 — FastAPI 통합

- [ ] 2.1 MongoDB/Ollama/FastAPI health smoke
- [ ] 2.2 채팅·영양·트렌드 실제 API 테스트
- [ ] 2.3 퀴즈·건강기록·알림 실제 API 테스트
- [ ] Checkpoint 2 통과 및 임시 fixture 정리

## Phase 3 — Frontend

- [ ] 3.1 Vitest/build/lint
- [ ] 3.2 프로필·채팅·퀴즈·건강기록·커뮤니티 UI 흐름
- [ ] Checkpoint 3 통과

## Phase 4 — 안전/운영

- [ ] 4.1 응급·의료 안전 시나리오
- [ ] 4.2 Ollama/Mongo/포트/worker 장애·재시도
- [ ] Checkpoint 4 통과 및 민감 로그 점검

## Phase 5 — 문서/릴리스

- [ ] 5.1 문서 일관성 업데이트
- [ ] 5.2 전체 회귀 및 최종 smoke
- [ ] 5.3 작은 커밋 → push → CodeRabbit/Codex → merge → fetch
- [ ] 최종 완료 조건 충족
