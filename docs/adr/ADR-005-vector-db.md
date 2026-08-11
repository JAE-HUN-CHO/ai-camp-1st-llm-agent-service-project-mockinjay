# ADR-005: Vector Database Selection

- **Status**: Accepted (revised: local MongoDB Docker)
- **Date**: 2026-05-23
- **Decided by**: Project owner, 2026-05-23
- **Related**: `docs/converted/KidneyWise_TechSpec.md`, Requirements v0.96 정책서, `docs/converted/_ANALYSIS_REPORT.md` Section 5

## Context

벡터 DB 선택이 문서 간 충돌한다:

| 출처 | 명시 벡터 DB |
|---|---|
| **KidneyWise_TechSpec.md** | MongoDB Atlas Vector Search (1536차원 cosine similarity) |
| **Requirements v0.96 정책서** | Pinecone |
| **현재 코드** | MongoDB 연결 코드 존재 (Atlas Vector Search 인덱스 설정 미확인). Pinecone 클라이언트 import 없음 |

이 결정이 미루어지면:
- 임베딩 인덱싱 스크립트(`scripts/build_vector_index.py` 등) 작성 불가
- PubMed RAG, 정책 문서 RAG 모두 차단됨
- KNO-005(다중 비교), KNO-007(트렌드) 등 P0 기능에 직접 영향

## Decision

**개발/MVP 단계에서 MongoDB(local Docker)의 Vector Search 기능을 사용한다.**

- 운영 환경: `docker-compose`로 띄우는 로컬 MongoDB (community + Atlas Local 또는 Atlas CLI deployment).
- 벡터 인덱스: `pubmed_embeddings.vector_index`, 1536-d cosine, `text-embedding-3-small`.
- **Atlas(클라우드)는 MVP 출시 범위 밖**. 프로덕션 배포는 별도 ADR에서 결정.

근거:
1. **사용자 결정**: 프로젝트 오너가 로컬 MongoDB(Docker) 진행을 명시적으로 지시.
2. **Tech Spec 일치**: 1536차원 + cosine 스키마는 그대로 유효.
3. **개발 비용 0원**: 클라우드 비용·결제 정보 등록 불필요.
4. **단일 드라이버**: `pymongo` 하나로 일반 쿼리 + 벡터 쿼리.
5. **Pinecone 미선택**: 별도 서비스 운영 부담 + MVP 데이터 규모(< 100만 문서)에서 불필요.
6. **이전 경로**: 후속 단계에서 같은 컬렉션을 그대로 Atlas Cloud / 자체 호스팅 클러스터로 옮길 수 있음 (lock-in 낮음).

## Local setup (정식)

`docker-compose.yml` 발췌:

```yaml
services:
  mongodb:
    image: mongodb/mongodb-atlas-local:latest   # vector search 지원 로컬 이미지
    ports: ["27017:27017"]
    volumes: ["./.mongo-data:/data/db"]
    environment:
      MONGODB_INITDB_ROOT_USERNAME: careguide
      MONGODB_INITDB_ROOT_PASSWORD: careguide_local
```

(communtiy 이미지로는 `$vectorSearch`가 미지원이므로 `mongodb-atlas-local`을 사용한다.)

## Schema (확정)

```
Collection: pubmed_embeddings
{
  _id: ObjectId,
  pmid: str,
  title: str,
  abstract: str,
  publication_year: int,
  embedding: [1536 x float],  // text-embedding-3-small
  created_at: datetime
}

Index: vector_index
- type: vectorSearch
- field: embedding
- numDimensions: 1536
- similarity: cosine
```

## Consequences

**Positive**
- 단일 DB 운영, 단일 드라이버
- 클라우드 비용 0
- 오프라인 개발 가능

**Negative**
- 로컬 데이터 손실 리스크 → `./.mongo-data` 정기 백업 스크립트 필요
- 프로덕션 트래픽·HA·백업·모니터링은 후속 ADR에서 별도 설계 필요
- Pinecone의 namespace·hybrid search 기능 미지원 → 후속에 hybrid search 필요해지면 재평가

**Follow-up tasks**
1. `docker-compose.yml`에 `mongodb-atlas-local` 서비스 추가 (없으면)
2. `scripts/build_vector_index.py` 작성: 컬렉션 생성 + `vector_index` 생성 + idempotent 재실행
3. `scripts/embed_pubmed.py` (배치, retry, resume-from-checkpoint)
4. 정책서·복지문서 임베딩 컬렉션 분리 여부 결정 (현재 권장: `policy_embeddings` 별도 컬렉션)
5. 운영 배포용 ADR-XXX 별도 작성 (managed vs self-hosted)
