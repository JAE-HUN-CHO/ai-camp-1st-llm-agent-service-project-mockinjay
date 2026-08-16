# CareGuide 1~5 실행·검증 계획

## 목표

현재 merge된 Ollama-only 런타임을 기준으로 남은 1~5 항목을 실제 환경에서
검증한다. 모든 논리 단위는 `계획 → 구현/설정 → 정적 검증 → 단위 테스트 →
실서비스 테스트 → 결과 검증` 순서로 완료한다. 실패하면 다음 단위로 진행하지
않고 원인 수정과 재검증을 반복한다.

## 공통 실행 규칙

각 작업 단위마다 다음 증거를 남긴다.

1. 변경 범위와 성공 기준을 먼저 기록한다.
2. `git diff --check`, 관련 `ruff`/TypeScript 정적 검사를 실행한다.
3. 관련 단위 테스트를 실행한다.
4. MongoDB Docker, Ollama, FastAPI/Parlant 등 실제 로컬 서비스를 기동한다.
5. 실제 HTTP/UI 흐름을 실행하고 상태 코드·응답 핵심 필드를 기록한다.
6. 같은 테스트를 변경 후 다시 실행하고 결과를 비교한다.
7. 작은 논리 단위마다 단일 커밋한다. 실패 증거와 blocker도 기록한다.

## Phase 1: Parlant 전체 HTTP smoke

### Task 1.1: 실행 전 계약 점검

**Acceptance criteria**

- [ ] `backend/requirements.lock`의 Parlant 3.3.x와 현재 `.venv` 버전이 일치한다.
- [ ] `RESEARCH_PORT`와 `WELFARE_PORT`가 유효하고 서로 다르다.
- [ ] Ollama generation/embedding 모델과 MongoDB가 준비되어 있다.

**Verification**

- `.venv/bin/ruff check backend/Agent backend/app`
- `PYTHONPATH=backend .venv/bin/python -c 'import parlant; ...'`
- `ollama list`, MongoDB authenticated ping

### Task 1.2: Research Parlant 실제 흐름

**Acceptance criteria**

- [ ] Research 서버가 인덱싱을 완료하고 지정 포트에서 응답한다.
- [ ] 고객/세션 생성, 메시지 전송, AI 응답 수신이 성공한다.
- [ ] 서버 로그에 Ollama 호출만 나타나며 유료 provider fallback이 없다.

**Verification**

- 서버 startup 로그와 `/api/agents` 또는 OpenAPI 응답
- Parlant client로 customer/session/event 생성
- 응답 status, source, session event를 JSON artifact로 저장

### Task 1.3: Medical Welfare Parlant 실제 흐름

**Acceptance criteria**

- [ ] 복지 서버가 별도 포트에서 기동한다.
- [ ] 복지 질문이 welfare agent/tool 경로를 거쳐 응답한다.
- [ ] Research와 포트·고객 저장소가 충돌하지 않는다.

**Verification**

- Research와 동일한 client smoke를 복지 서버에 실행
- 잘못된 포트·중복 포트 설정 실패 테스트

### Checkpoint 1

- [ ] 두 Parlant HTTP 흐름 모두 실제 성공
- [ ] 실패 시 원인·재현 명령·환경을 기록하기 전 다음 Phase로 이동하지 않음

## Phase 2: FastAPI 핵심 통합 흐름

### Task 2.1: 기반 서비스

- [ ] MongoDB Docker healthy 및 authenticated ping
- [ ] Ollama `/api/generate`, `/api/chat`, `/api/embeddings` 성공
- [ ] FastAPI `/health`, `/db-check` 성공

### Task 2.2: 채팅·영양·트렌드

- [ ] 직접 Ollama 채팅 응답 성공
- [ ] 영양 이미지/분석 API 성공
- [ ] temporal trends API 성공
- [ ] 각 응답에 provider와 핵심 payload가 존재

### Task 2.3: 퀴즈·건강기록·알림

- [ ] daily quiz 생성 및 chat 연동 성공
- [ ] health record 인증 CRUD 성공
- [ ] notification retry worker가 lifespan에서 등록되고 재시도 결과를 기록

### Checkpoint 2

- [ ] 핵심 API smoke 결과표 작성
- [ ] backend targeted pytest 및 ruff 통과
- [ ] 임시 Mongo fixture 정리 확인

## Phase 3: 프론트엔드 실제 검증

### Task 3.1: 자동 검증

- [ ] `cd frontend && npm run lint`
- [ ] `cd frontend && npm run build`
- [ ] `cd frontend && npm run test -- --run`

### Task 3.2: 주요 UI 흐름

- [ ] 로그인/프로필 사용자 유형 변경 후 채팅 프로필 동기화
- [ ] 채팅 → 일일 퀴즈 배너 → 퀴즈 화면 이동
- [ ] 건강기록 조회/생성/삭제
- [ ] 커뮤니티 검색 결과와 cursor pagination

### Checkpoint 3

- [ ] 자동 테스트와 브라우저/실제 API 결과가 일치
- [ ] 콘솔 오류·네트워크 4xx/5xx 없음

## Phase 4: 의료 안전·운영 검증

### Task 4.1: 안전 시나리오

- [ ] 응급 증상 질문이 안전 경로로 분기
- [ ] 위험/의료 질문 false-negative 시나리오를 실제 Parlant 흐름에서 확인
- [ ] 일반 정보 질문이 과도하게 차단되지 않음

### Task 4.2: 장애·재시도

- [ ] Ollama 중단 시 유료 API로 우회하지 않고 명확한 오류 반환
- [ ] Mongo 일시 오류 시 retry worker와 API 오류가 예측 가능
- [ ] 잘못된 포트/모델/임베딩 차원 설정이 fail-fast

### Checkpoint 4

- [ ] 의료 안전 결과와 장애 결과를 재현 가능한 명령으로 기록
- [ ] 보안 로그에 모델 원문·환자 식별정보가 남지 않음

## Phase 5: 문서·최종 릴리스 검증

### Task 5.1: 문서 일관성

- [ ] 현재 문서는 `frontend/`, Ollama-only, local MongoDB를 기준으로 함
- [ ] 과거 OpenAI/Pinecone 문서는 historical로 명시
- [ ] 실제 검증 결과·미검증 항목·환경 제약을 보고서에 반영

### Task 5.2: 최종 회귀

- [ ] backend targeted/full pytest 결과 기록
- [ ] frontend test/build/lint 결과 기록
- [ ] 전체 smoke 재실행 후 이전 결과와 비교

### Task 5.3: Git/리뷰 게이트

- [ ] 논리 단위별 작은 커밋과 clean worktree
- [ ] push 후 CodeRabbit/Codex 리뷰 대기
- [ ] actionable comment 0건 및 unresolved thread 0건 확인
- [ ] 리뷰가 없고 CI가 성공일 때만 merge
- [ ] merge 후 `git fetch origin` 및 `origin/main` 커밋 확인

## 최종 완료 조건

- 1~5의 acceptance criteria가 모두 체크됨
- 실제 서비스 테스트 증거가 각 흐름별로 존재함
- 미실행 항목은 정확한 blocker와 재현 명령이 있음
- 유료 API 키를 사용하지 않음
- 문서와 코드의 런타임 계약이 일치함

## 위험과 대응

| 위험 | 영향 | 대응 |
|---|---|---|
| 로컬 모델 응답이 schema를 따르지 않음 | Parlant indexing 실패 | JSON 추출/재시도·작은 모델 smoke 후 전체 모델 검증 |
| Parlant 인덱싱이 오래 걸림 | HTTP 검증 지연 | startup 단계와 HTTP 단계 분리, 타임아웃 기록 |
| 임베딩 차원 불일치 | 검색·Mongo 저장 실패 | 1536 차원 fail-fast 및 모델 확인 |
| 외부 API 키 없음 | hosted 경로 실패 | Ollama-only로 중단, 유료 fallback 금지 |
| CI/CodeRabbit 지연 | merge 판단 지연 | pending과 completed를 구분해 완료 전 merge 금지 |
