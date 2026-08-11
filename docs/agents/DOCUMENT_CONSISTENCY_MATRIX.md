# CareGuide 문서 기준선 및 충돌 처리

이 문서는 구현 문서, 계획 문서, 과거 리포트가 현재 런타임 계약과 서로 다른 말을 할
때 적용할 우선순위를 고정한다. 문서를 삭제하거나 과거 기록을 현재 상태로 위장하지
않는다.

## 현재 기준 (normative)

| 영역 | 기준 |
|---|---|
| 실행 계약 | `AGENTS.md`, `docs/AGENTS.md` |
| 도메인/경계 | `docs/agents/domain.md`, `docs/agents/BOUNDARY_MAP.md` |
| cache | `docs/agents/CACHE_POLICY.md` |
| 결정 | `docs/adr/README.md`, Accepted ADR-004/005/006/008/009/010/011 |
| API | `backend/app/main.py`, `scripts/check_api_contract.py`, `scripts/check_frontend_parity.py` |
| 환경 | `.env.example`, `backend/.env.example`, `backend/requirements.txt`, `backend/requirements.lock` |
| 검증 | `tests/`, `frontend/src/**/*.test.*`, `eval/` |

현재 구현 계약은 다음과 같다.

- product frontend는 `frontend/` 하나이며, 보존용 원본은 `logs/rollback/` 아래에만 둔다.
- LLM과 embedding은 Ollama만 사용한다: `qwen3.6:27b-mlx`, `nomic-embed-text-v2-moe`.
- 데이터베이스와 vector source of truth는 local MongoDB Atlas Local이며 vector 계약은
  ADR-005의 1536차원 cosine이다.
- 결제 SDK/UI/endpoint는 없다.
- 임상시험 응답 cache는 Mongo `clinical_trials_cache`가 공유 계층이고, 메모리 cache는
  best-effort 단기 tier다.

## 역사적·참고 문서 (non-normative)

`docs/converted/`, `docs/raw_docs/`, `docs/project-plans/`, `docs/data/`,
`docs/backend/`, `docs/frontend/`와 날짜가 있는 `PHASE*`, `*_REPORT`, `*_SUMMARY`,
`*_STATUS` 문서는 당시의 설계·실행 증거다. 이 문서에 남은 `new_frontend`, OpenAI,
Pinecone, Anthropic, Atlas hosted 등의 표현은 현재 설정을 지시하지 않는다.

과거 문서를 인용해 구현을 변경할 때는 먼저 이 문서의 현재 기준과 Accepted ADR을
확인하고, 결정 변경이 필요하면 기존 Accepted ADR을 수정하지 말고 새 ADR을 추가한다.

## 검증 규칙

1. 코드/환경/테스트가 문서와 다르면 normative 문서를 먼저 고친다.
2. historical 문서의 경로·provider 표현은 삭제하지 않고 historical 상태를 유지한다.
3. 실제 경로와 API parity는 `scripts/check_frontend_parity.py`와
   `scripts/check_api_contract.py`로 확인한다.
4. 정적 provider 검사는 runtime Python 코드와 `.env*`를 대상으로 하며, 문서의 역사적
   언급은 실패로 처리하지 않는다.
5. normative 문서의 상대 링크는 `scripts/check_doc_links.py`로 검증한다.
