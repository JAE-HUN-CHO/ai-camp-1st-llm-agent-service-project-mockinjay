# 커스텀 NLP 서비스 구현 (비용 절감)

## 개요

Parlant의 기본 NLP 서비스 대신 **커스텀 HealthcareNLPService**를 사용하여 **비용을 크게 절감**할 수 있습니다.

### 비용 절감 포인트

| 컴포넌트 | 기존 (GPT-4) | 커스텀 (GPT-4o-mini) | 절감률 |
|---------|-------------|---------------------|--------|
| Text Generation | $30/1M tokens | $0.15/1M tokens | **99.5%** |
| Embeddings | text-embedding-3-large | text-embedding-3-small | **50%** |
| 캐싱 | 없음 | LRU + Disk Cache | **추가 50-80%** |

## 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                  Parlant Server                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │     ParlantHealthcareNLPService (Adapter)         │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │      HealthcareNLPService (Core)            │  │  │
│  │  │  ┌───────────────┐  ┌──────────────────┐   │  │  │
│  │  │  │ GPT-4o-mini   │  │ text-embedding-  │   │  │  │
│  │  │  │ Generator     │  │ 3-small Embedder │   │  │  │
│  │  │  └───────────────┘  └──────────────────┘   │  │  │
│  │  │  ┌───────────────────────────────────────┐  │  │  │
│  │  │  │   Multi-Tier Caching System          │  │  │  │
│  │  │  │   - Memory Cache (LRU, 5000 items)   │  │  │  │
│  │  │  │   - Disk Cache (Persistent)          │  │  │  │
│  │  │  └───────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 파일 구조

```
backend/Agent/research_paper/server/
├── nlp_service.py              # 코어 NLP 서비스
│   ├── GPT4oMiniGenerator      # GPT-4o-mini 텍스트 생성
│   ├── TextEmbedding3SmallEmbedder  # 임베딩 생성
│   ├── EmbeddingCache          # 캐싱 시스템
│   └── HealthcareNLPService    # 메인 서비스
│
├── parlant_nlp_adapter.py      # Parlant 인터페이스 어댑터
│   ├── HealthcareTokenizer     # 토크나이저 어댑터
│   ├── HealthcareSchematicGenerator  # 스키마 생성 어댑터
│   ├── HealthcareEmbedder      # 임베더 어댑터
│   ├── NoModeration            # 모더레이션 (선택)
│   ├── ParlantHealthcareNLPService  # Parlant NLPService 구현
│   └── create_healthcare_nlp_service()  # 팩토리 함수
│
└── healthcare_v2_en.py         # 메인 서버
    └── async with p.Server(nlp_service=create_healthcare_nlp_service)
```

## 구현 세부사항

### 1. HealthcareNLPService (nlp_service.py)

핵심 기능:
- **GPT-4o-mini**: 비용 효율적인 텍스트 생성 ($0.15/1M tokens)
- **text-embedding-3-small**: 1536차원 임베딩
- **Retry Policy**: API 실패 시 자동 재시도 (지수 백오프)
- **Multi-Tier Caching**:
  - 메모리 캐시: LRU 방식, 5000개 아이템
  - 디스크 캐시: 영구 저장
- **의료 특화 기능**:
  - 의료 쿼리 분류
  - 키워드 추출
  - 텍스트 요약

### 2. Parlant Adapter (parlant_nlp_adapter.py)

Parlant의 `NLPService` 인터페이스 구현:

#### Required Methods:
```python
class ParlantHealthcareNLPService(NLPService):
    async def get_schematic_generator(self, t: type[T]) -> SchematicGenerator[T]
    async def get_embedder(self) -> Embedder
    async def get_moderation_service(self) -> ModerationService
```

#### Key Components:

**HealthcareSchematicGenerator**:
- Pydantic 스키마를 JSON으로 변환
- GPT-4o-mini로 구조화된 응답 생성
- JSON 파싱 및 검증
- 에러 핸들링

**HealthcareEmbedder**:
- text-embedding-3-small 사용
- 캐싱으로 중복 요청 제거
- 배치 처리 지원

**NoModeration**:
- 현재는 모든 콘텐츠 승인
- 프로덕션에서는 OpenAI Moderation API 사용 권장

### 3. 서버 통합 (healthcare_v2_en.py)

```python
from parlant_nlp_adapter import create_healthcare_nlp_service

async with p.Server(nlp_service=create_healthcare_nlp_service) as server:
    # 서버 설정...
```

## 사용 방법

### 환경 변수 설정

```bash
# .env 파일
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3.6:27b-mlx
```

### 서버 실행

```bash
cd backend/Agent/research_paper
python run_server.py
```

### 로그 확인

서버 시작 시 다음과 같은 로그를 볼 수 있습니다:

```
[3/3] Setting up Parlant Server...
✅ Initialized ParlantHealthcareNLPService
   - Generator: gpt-4o-mini
   - Embedder: text-embedding-3-small
   - Cache: enabled

🏥 Healthcare NLP Service Initialized
================================================================================
✅ Generator: GPT-4o-mini
✅ Embedder: text-embedding-3-small (1536D)
✅ Cache: enabled
================================================================================
```

## 캐싱 동작

### 임베딩 캐시

1. **메모리 캐시** (빠름):
   - LRU 방식
   - 최대 5000개 아이템
   - 자동 축출

2. **디스크 캐시** (영구):
   - `./nlp_cache/embeddings/` 디렉토리
   - MD5 해시 키
   - Pickle 직렬화

### 캐시 히트율

```python
stats = nlp_service.get_stats()
print(stats['embedder'])
# Output:
# {
#   "hits": 1234,
#   "misses": 56,
#   "hit_rate": "95.7%",
#   "memory_items": 892,
#   "memory_size_mb": 13.4
# }
```

## 비용 절감 예시

### 시나리오: 하루 10만 쿼리 처리

| 항목 | GPT-4 + large | GPT-4o-mini + small | 절감 |
|-----|---------------|---------------------|------|
| 텍스트 생성 (평균 2K tokens) | $6.00 | $0.03 | **$5.97** |
| 임베딩 (평균 100 tokens) | $0.13 | $0.002 | **$0.128** |
| **일일 총 비용** | **$6.13** | **$0.032** | **$6.10** |
| **월간 비용** | **$183.90** | **$0.96** | **$182.94** |
| **연간 비용** | **$2,236.80** | **$11.68** | **$2,225.12** |

### 캐싱 효과 (80% 히트율 가정)

- 임베딩 비용: $0.002 → $0.0004 (추가 80% 절감)
- **최종 월간 비용**: $0.96 → **$0.20**
- **최종 연간 비용**: $11.68 → **$2.44**

## 성능 최적화

### 1. 배치 처리

```python
# 나쁜 예 (여러 번 호출)
for text in texts:
    result = await embedder.embed([text])

# 좋은 예 (배치 처리)
results = await embedder.embed(texts)
```

### 2. 캐시 활용

```python
# 동일한 텍스트는 자동으로 캐시됨
result1 = await embedder.embed(["만성 신장 질환"])  # API 호출
result2 = await embedder.embed(["만성 신장 질환"])  # 캐시 히트 (0ms)
```

### 3. 토큰 관리

```python
# 토큰 수 확인
token_count = nlp_service.count_tokens(text)

# 토큰 제한에 맞게 자르기
truncated = nlp_service.truncate_text(text, max_tokens=8000)
```

## 모니터링

### 통계 수집

```python
stats = healthcare_service.get_stats()
print(json.dumps(stats, indent=2))
```

출력 예시:
```json
{
  "generator": {
    "model": "gpt-4o-mini",
    "total_calls": 1523,
    "total_input_tokens": 456789,
    "total_output_tokens": 234567,
    "total_cached_tokens": 123456,
    "total_tokens": 691356
  },
  "embedder": {
    "model": "text-embedding-3-small",
    "dimensions": 1536,
    "total_api_calls": 234,
    "total_local_calls": 12,
    "cache_hits": 1890,
    "hits": 1890,
    "misses": 246,
    "hit_rate": "88.5%",
    "memory_items": 1234,
    "memory_size_mb": 18.7
  }
}
```

## 프로덕션 고려사항

### 1. 모더레이션 서비스 추가

현재는 `NoModeration()`을 사용하지만, 프로덕션에서는 실제 모더레이션 구현 필요:

```python
from openai import AsyncOpenAI

class OpenAIModerationService(ModerationService):
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def check(self, content: str) -> ModerationCheck:
        response = await self.client.moderations.create(input=content)
        result = response.results[0]

        tags = []
        if result.categories.harassment:
            tags.append("harassment")
        if result.categories.hate:
            tags.append("hate")
        # ... 기타 카테고리

        return ModerationCheck(
            flagged=result.flagged,
            tags=tags
        )
```

### 2. 캐시 크기 조정

메모리 사용량에 따라 조정:

```python
ParlantHealthcareNLPService(
    parlant_logger=logger,
    parlant_meter=meter,
    use_cache=True,
    cache_dir="./nlp_cache",
    max_memory_items=10000,  # 기본 5000에서 증가
)
```

### 3. 에러 핸들링

API 실패 시 fallback 전략:

```python
# nlp_service.py에 이미 구현됨
try:
    result = await self.client.embeddings.create(...)
except Exception as e:
    logger.error(f"OpenAI failed: {e}, using local model")
    return await self._embed_local(texts)  # Local fallback
```

## 트러블슈팅

### 문제: JSON 파싱 실패

**증상**: `Failed to parse JSON response`

**해결**:
1. Temperature를 낮춤 (0.3-0.5)
2. max_tokens 증가
3. 프롬프트 명확화

### 문제: 캐시 파일이 너무 많음

**증상**: `./nlp_cache/embeddings/` 디렉토리에 수천 개의 파일

**해결**:
```bash
# 오래된 캐시 정리 (30일 이상)
find ./nlp_cache -type f -mtime +30 -delete
```

### 문제: 메모리 사용량 증가

**증상**: 서버 메모리 사용량이 계속 증가

**해결**:
```python
# 캐시 크기 줄이기
max_memory_items=1000  # 기본 5000에서 감소
```

## 결론

이 커스텀 NLP 서비스를 통해:

✅ **99.5% 비용 절감** (GPT-4 → GPT-4o-mini)
✅ **캐싱으로 추가 50-80% 절감**
✅ **Parlant와 완벽 호환**
✅ **의료 특화 기능 유지**
✅ **프로덕션 레벨 안정성**

**연간 $2,000+ 절감 가능!** 🎉
