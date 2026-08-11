# CareGuide Cache 배치 및 결합 해소 정책

## 결론

`cache/`를 최상위 제품 경계로 추가하지 않는다. cache의 위치는 값의 수명과 소유자에 따라 결정한다.

```text
Cache value kind                 Owner / location
────────────────────────────────────────────────────────────
Domain-persistent cache         backend feature repository → local MongoDB
                                   (clinical_trials_cache, daily counter, TTL sessions)

Provider/computation cache      backend cache adapter → memory/disk/local DB
                                   (embedding, translation, news, PubMed result)

Frontend UX cache               frontend feature/shared cache → versioned localStorage
                                   (non-sensitive translation/display preference only)

Test/eval fixture               tests/fixtures 또는 eval/gold
                                   (runtime cache로 사용하지 않음)

Runtime evidence                logs/metrics
                                   (cache value를 저장하지 않음)
```

## Cache module의 interface

모든 cache module은 최소한 다음 정보를 명시한다.

- key schema와 namespace
- value schema/version
- TTL 또는 만료 규칙
- scope: request / process / user / shared
- invalidation 방법
- stale 값 허용 여부
- 최대 크기와 eviction 규칙
- PII 포함 여부
- hit/miss/error 관측 방법

key만 만드는 shallow helper를 여러 곳에 만들지 않는다. 실제로 두 adapter가 필요할 때만 seam을 만든다. 예를 들어 `memory adapter`와 `Mongo adapter`가 모두 필요하면 cache interface가 깊어지지만, 하나뿐이면 feature 내부 구현으로 남긴다.

## 권장 배치

### 1. Domain-persistent cache

임상시험, 검색 횟수, 세션 TTL처럼 제품 동작과 데이터 무결성에 영향을 주는 값은 MongoDB가 source of truth다.

```text
backend/app/features/clinical_trials/repository.py
backend/app/features/search_quota/repository.py
backend/app/features/chat/repository.py
        ↓
local MongoDB collections + TTL/index
```

이 값은 `data/cache/` 파일이나 frontend localStorage에 저장하지 않는다.

### 2. Provider/computation cache

embedding·번역·외부 검색 결과처럼 재생성 가능한 값은 backend adapter가 소유한다.

```text
backend/app/cache/                 # 공통 cache interface/정책
backend/app/adapters/cache/        # memory, disk, Mongo adapter
data/cache/                        # gitignored local artifacts only
```

provider adapter가 자신의 cache, retry, timeout, key 생성까지 모두 숨길 수는 있지만, feature 정책과 transport는 알면 안 된다.

### 3. Frontend UX cache

번역 결과나 display preference처럼 민감하지 않고 없어져도 복구 가능한 값만 frontend cache로 둔다.

```text
frontend/src/shared/cache/
frontend/src/features/<feature>/cache/
```

건강기록, access token, chat 원문, point balance는 frontend localStorage cache에 저장하지 않는다.

## 현재 결합 목록

| 위치 | 결합 | 영향 | 분리 seam |
|---|---|---|---|
| `backend/app/api/clinical_trials.py` | HTTP router + 외부 조회 + in-memory cache + 번역 cache | 프로세스별 cache 불일치, 테스트 어려움 | clinical trial repository/cache adapter |
| `backend/app/api/news.py` | HTTP router + 외부 news 조회 + cache + cache clear | transport가 cache 정책을 소유 | news query module + cache adapter |
| `backend/app/services/pubmed_search.py` | PubMed client + translation cache + count cache | provider와 computation cache 변경이 함께 발생 | PubMed adapter / translation cache / count repository |
| `backend/app/db/vector_manager.py` | Pinecone + embedding model + disk cache + LRU | ADR, provider, cache가 한 implementation에 묶임 | VectorSearch adapter / Embedding adapter / Cache adapter |
| `frontend/src/services/translateApi.ts` | HTTP 호출 + localStorage schema + eviction | frontend API module이 persistence까지 담당 | translation client / UX cache |
| `backend/Agent/research_paper/server/cache_manager.py` | global cache instance + server lifecycle | hidden mutable state | injected cache adapter |
| `backend/app/api/chat.py`, `session.py` | global active stream registry | request scope가 process global state로 누수 | stream registry adapter |
| `backend/Agent/core/agent_registry.py` | decorator import order + global registry | composition root가 숨겨짐 | explicit registry adapter |
| `backend/app/db/connection.py`, `mongodb_manager.py` | 두 Mongo connection seam + legacy globals | repository ownership과 lifecycle 중복 | one Mongo adapter / unit-of-work seam |
| nutrition implementations | LangGraph와 Registry/BaseAgent 이중 구현 | 같은 domain 책임의 source of truth 중복 | one Nutrition module + compatibility adapter |

## 해소 순서

1. domain-persistent cache와 best-effort computation cache를 분류한다.
2. router 내부 cache를 feature-owned module로 이동하되 endpoint 경로는 유지한다.
3. vector/embedding cache에서 provider와 cache를 분리한다.
4. global cache·active stream·registry를 composition root에서 주입한다.
5. frontend localStorage cache는 민감도·version·TTL 테스트를 추가한다.
6. hit/miss/expiry를 logs에 기록하되 cache value나 PII는 기록하지 않는다.

## 금지 사항

- cache를 source of truth처럼 사용
- 동일 key/value를 backend와 frontend에서 서로 다른 schema로 저장
- TTL 없는 무제한 process-global dict
- cache miss에서 외부 provider를 무제한 재시도
- cache clear endpoint가 인증·권한 없이 노출
