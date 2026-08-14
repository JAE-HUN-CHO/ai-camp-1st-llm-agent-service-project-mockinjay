# CareGuide 1~5 실행 결과 (2026-08-14)

## 실행 환경

- 브랜치: `codex/ollama-integration-smoke-fix`
- Parlant lock/.venv: `parlant==3.3.2`, `parlant-client==3.3.1` (일치)
- 포트: Research `8800`, Welfare `8801` (1~65535, 서로 다름)
- Ollama: `qwen3.6:27b-mlx`, `nomic-embed-text-v2-moe`
- MongoDB: `mongodb/mongodb-atlas-local:8.0.6`, Docker healthy, authenticated `ping` 성공
- 유료 API 키는 설정하거나 사용하지 않음

## Phase 1 — Parlant

### 1.1 사전 점검 — 부분 성공

성공한 명령:

```text
.venv/bin/ruff check backend/Agent backend/app                 # All checks passed
ollama list                                                   # 두 Ollama 모델 확인
docker compose ps                                             # mongodb Up (healthy)
MongoClient(MONGODB_URI).admin.command('ping')                # {'ok': 1.0}
```

주의: `.env`의 Mongo URI에 있는 `&` 때문에 `source .env`는 실패한다. 애플리케이션은 dotenv로 읽어 정상 기동했다.

### 1.2/1.3 Research/Welfare 실제 HTTP — 미완료(blocker)

- 구형 `run_unified_server.py`는 `EMCIE_API_KEY`를 요구하며 `NLPServiceConfigurationError`로 종료했다. 이는 hosted Emcie 경로이며 정책상 사용할 수 없다.
- 커스텀 `healthcare_v2_en.py`(Ollama NLP adapter)로 Research 서버를 기동하면 Ollama `/api/chat` 및 `/api/embed` 호출과 로컬 Mongo 인덱싱은 진행된다.
- 그러나 기동 시 `cross-encoder/ms-marco-MiniLM-L-6-v2`를 Hugging Face에서 다운로드한다. 이는 Ollama+local Mongo only 제약을 충족하지 않는다.
- 엔티티 평가가 약 6분 이상 지속되어 `8800` HTTP listener가 열리기 전에 중단했다. 따라서 customer/session/event 및 AI 응답을 성공으로 기록하지 않았다.
- Welfare 별도 포트 HTTP 흐름도 Research blocker 때문에 실행하지 않았다.

## Phase 2 — FastAPI

라우트/설정 도달성 확인(Parlant 또는 외부 서비스 readiness 증거 아님):

```text
GET /health       -> 200 {"status":"healthy"}
GET /db-check     -> 200 MongoDB 연결 성공
GET /api/trends/health -> 200 (FastAPI route response only; 외부 PubMed/news readiness 아님)
GET /api/chat/info -> 200 (FastAPI route/config response only; Research 8800 listener readiness 아님)
```

트렌드 POST는 최초 요청이 20초 timeout이었으나 FastAPI 로그상 PubMed 재시도 후 다음 요청은 PubMed 5건·차트·설명 생성까지 완료했다. Research `8800` listener는 기동되지 않았고 Welfare 흐름은 실행하지 않았다. 이 경로는 외부 PubMed 서비스 의존이 있으므로 “Ollama + local Mongo only” 최종 게이트를 통과한 것으로 보지 않는다.

인증 없는 `/api/health-records/`는 예상대로 `401 MISSING_AUTHORIZATION`을 반환했다. 인증 CRUD는 테스트 계정/토큰 없이 실행하지 않았다.

백엔드:

```text
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests
  -> 46 deselected (pytest.ini 기본값: not integration)
backend/tests/test_parlant_nlp_adapter.py
  -> 4 deselected, import/collection 성공
ruff check backend/Agent backend/app
  -> All checks passed
```

Ollama integration pytest는 sandbox 소켓 차단으로 실패했고, 권한 재실행은 27B 호출 중 최종 요약이 반환되지 않아 성공 증거로 채택하지 않았다. 별도 curl로 `/api/generate`, `/api/chat`은 HTTP 200, 응답 `OK`를 확인했고 `/api/embed`는 1536차원을 반환했다.

## Phase 3 — Frontend

성공:

```text
cd frontend && npm run test -- --run  -> 30 files, 410 tests passed
cd frontend && npm run build          -> built successfully
cd frontend && npm run lint           -> 0 errors, 70 warnings
```

Vitest에는 의도된 네트워크 오류/React act 경고가 출력되지만 테스트는 모두 통과했다. 실제 브라우저 UI 흐름과 콘솔/네트워크 검증은 인증된 사용자 세션이 없어 실행하지 않았다.

## Phase 4 — 안전/장애

미완료. Parlant 실제 세션이 열리지 않아 응급/위험/일반 질문 분기, Ollama 중단, Mongo 일시 오류, fail-fast 포트/모델/차원 시나리오를 모두 완료했다고 주장하지 않는다. Parlant 로그에는 환자 원문 대신 `<redacted>`가 남는 FastAPI 로그 사례를 확인했지만, 전체 로그 감사는 미완료다.

## Phase 5 — 문서/릴리스

이 보고서 작성 및 위 검증 결과 기록까지만 수행했다. 전체 회귀·문서 historical 표기·작은 커밋/푸시/PR/CodeRabbit·Codex 대기·GraphQL unresolved thread 0·CI success·merge·merge 후 `git fetch origin`은 Parlant/local-only blocker 해소 전에는 실행하지 않았다.

## 남은 blocker

1. `healthcare_v2_en.py` 초기화에서 Hugging Face cross-encoder를 제거하거나 사전 설치된 완전 로컬 대체 경로로 바꿔야 한다.
2. Parlant 엔티티 평가 시간을 제한/최적화한 뒤 Research와 Welfare의 실제 customer/session/event/message HTTP 증거가 필요하다.
3. 인증 fixture를 사용한 채팅·영양·퀴즈·건강기록·알림 API smoke가 필요하다.
4. hosted PubMed/news 의존을 허용할지 또는 local Mongo fixture로 대체할지 결정 전에는 local-only 릴리스 게이트를 통과할 수 없다.

이 파일은 검증 결과를 기록하기 위한 단일 문서 단위이며, 성공하지 않은 항목은 의도적으로 미완료로 남겼다.
