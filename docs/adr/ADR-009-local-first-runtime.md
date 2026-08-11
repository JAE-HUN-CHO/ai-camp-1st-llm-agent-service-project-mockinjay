# ADR-009: Local-First Runtime and Package Policy

- **Status**: Proposed
- **Date**: 2026-08-11
- **Related**: [ADR-005](./ADR-005-vector-db.md), [ADR-008](./ADR-008-single-frontend-root.md), [`BOUNDARY_MAP.md`](../agents/BOUNDARY_MAP.md)

## Context

CareGuide는 개발·테스트 단계에서 외부 LLM과 클라우드 벡터 DB에 강하게 의존하면 재현성이 떨어지고 비용·네트워크 상태가 테스트 결과에 영향을 받는다. 동시에 오래된 패키지와 중복 frontend 구조가 AI가 읽어야 하는 맥락을 늘린다.

## Proposed Decision

### Local-first runtime

- 기본 LLM 실행은 로컬 모델 adapter를 사용한다.
- 기본 embedding도 로컬 실행 가능한 adapter를 우선한다.
- 기본 DB는 로컬 MongoDB이며, vector 검색도 ADR-005의 로컬 MongoDB 방향을 따른다.
- 외부 PubMed/ClinicalTrials.gov는 필요한 데이터 소스로만 사용하고, 결과는 local cache를 통해 재현 가능하게 한다.
- OpenAI 등 외부 LLM은 명시적인 opt-in adapter로 유지한다.

### Package policy

- 실행 시점에 무제한 `latest`를 사용하지 않는다.
- 업그레이드 시점의 최신 안정 버전과 호환되는 패키지를 조사한다.
- Python과 Node 의존성을 lockfile/compiled requirements로 고정한다.
- major upgrade마다 build, lint, unit, integration, smoke 검증을 통과시킨다.
- 기능에 사용하지 않는 dependency는 제거한다.

## Rationale

- local model/DB는 네트워크·비용·API key에 덜 의존한다.
- adapter를 통해 local과 external implementation을 교체할 수 있다.
- lockfile은 “최신”과 “재현 가능성”의 충돌을 해결한다.

## Consequences

### Positive

- 오프라인에 가까운 개발·테스트 가능
- 외부 provider 장애가 핵심 회귀 테스트를 막지 않음
- provider 교체가 한 seam에 집중됨
- 패키지 버전과 동작의 재현성 확보

### Negative

- 로컬 모델의 품질·메모리 요구량을 별도로 검증해야 함
- 초기 모델 다운로드와 로컬 DB 준비 시간이 필요함
- 최신 major upgrade의 breaking change 대응 비용이 발생함

## Acceptance Criteria

- API key 없이 핵심 unit/integration 테스트가 실행된다.
- 로컬 MongoDB에서 schema/index/TTL/vector 검증이 실행된다.
- local LLM adapter mock 또는 실제 로컬 모델로 채팅·Agent smoke가 실행된다.
- 외부 provider를 끈 상태에서도 frontend build와 backend test가 통과한다.
- package versions가 lockfile에 고정되어 같은 환경에서 재현된다.

## Follow-ups

1. Python/Node 지원 버전과 최신 안정 패키지 후보 조사
2. LLM, embedding, vector 검색의 후보 seam 검토
3. Ollama 또는 동등한 local runtime smoke 경로 결정
4. MongoDB local runtime 실행 방법 문서화
