# Router 최종 개선사항 (2차 검토 반영)

**작성일**: 2025-11-23
**버전**: 1.2
**기반 문서**: ROUTER_IMPROVEMENTS.md
**검토 반영**: Expert Review 2차 2025-11-23

---

## 📋 목차

1. [한국어 형태소 분석 도입](#1-한국어-형태소-분석-도입)
2. [OpenTelemetry 세부 구현](#2-opentelemetry-세부-구현)
3. [예외 및 로깅 포맷 일관성](#3-예외-및-로깅-포맷-일관성)
4. [TaskGroup vs asyncio.gather 사용 가이드](#4-taskgroup-vs-asynciogather-사용-가이드)
5. [프로덕션 체크리스트](#5-프로덕션-체크리스트)

---

## 1. 한국어 형태소 분석 도입

### 1.1 현재의 한계

**기존 키워드 추출** (`ROUTER_IMPROVEMENTS.md`):
```python
def _extract_keywords_simple(self, text: str) -> Set[str]:
    """간단한 키워드 추출 (상위 빈도 명사)"""
    words = text.split()
    keywords = sorted(
        [w for w in set(words) if len(w) >= 3],
        key=lambda w: text.count(w),
        reverse=True
    )[:5]
    return set(keywords)
```

**문제점**:
- 띄어쓰기 기반으로만 분리 → 조사, 어미가 포함됨
- "저염식이" → "저염식" + "이" 분리 못함
- "칼륨 함량" → "칼륨"과 "함량"을 별도 단어로 인식 못함
- 복합어, 연어 처리 불가

### 1.2 한국어 NLP 도구 비교

| 도구 | 장점 | 단점 | 추천 용도 |
|------|------|------|----------|
| **KoNLPy (Mecab)** | 빠름, 정확함 | 설치 복잡 (C++ 의존) | 프로덕션 |
| **KoNLPy (Okt)** | 설치 쉬움 | 느림 | 개발/테스트 |
| **Kiwi** | 매우 빠름, 정확함 | 새 라이브러리 | 프로덕션 (권장) |
| **soynlp** | 통계 기반, 신조어 발견 | 학습 필요 | 연구/분석 |

### 1.3 Kiwi 기반 개선안 (권장)

**설치**:
```bash
pip install kiwipiepy
```

**파일**: `backend/Agent/utils/korean_nlp.py`

```python
from kiwipiepy import Kiwi
from typing import Set, List, Dict
from functools import lru_cache

class KoreanNLP:
    """한국어 자연어 처리 유틸리티 (Kiwi 기반)"""

    _instance = None
    _kiwi = None

    @classmethod
    def get_instance(cls):
        """싱글톤 인스턴스 (Kiwi 초기화 비용 절감)"""
        if cls._instance is None:
            cls._instance = cls()
            cls._kiwi = Kiwi()
        return cls._instance

    def extract_keywords(
        self,
        text: str,
        top_k: int = 5,
        pos_filter: Set[str] = None
    ) -> Set[str]:
        """
        형태소 분석 기반 키워드 추출

        Args:
            text: 입력 텍스트
            top_k: 상위 K개 키워드
            pos_filter: 품사 필터 (기본값: 명사, 동사, 형용사)

        Returns:
            Set[str]: 추출된 키워드
        """
        if pos_filter is None:
            # NNG: 일반명사, NNP: 고유명사, VV: 동사, VA: 형용사
            pos_filter = {'NNG', 'NNP', 'VV', 'VA'}

        # 형태소 분석
        tokens = self._kiwi.tokenize(text)

        # 품사 필터링 및 빈도 계산
        word_freq: Dict[str, int] = {}
        for token in tokens:
            if token.tag in pos_filter and len(token.form) >= 2:
                word_freq[token.form] = word_freq.get(token.form, 0) + 1

        # 상위 K개 추출
        keywords = sorted(
            word_freq.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]

        return set([word for word, _ in keywords])

    def extract_noun_phrases(self, text: str) -> List[str]:
        """
        명사구 추출 (연속된 명사)

        예시:
        "만성 신장 질환" → ["만성", "신장", "질환", "만성 신장 질환"]
        """
        tokens = self._kiwi.tokenize(text)
        noun_tags = {'NNG', 'NNP'}

        noun_phrases = []
        current_phrase = []

        for token in tokens:
            if token.tag in noun_tags:
                current_phrase.append(token.form)
            else:
                if len(current_phrase) >= 2:
                    # 2개 이상 연속된 명사 → 명사구
                    noun_phrases.append(' '.join(current_phrase))
                current_phrase = []

        # 마지막 명사구 처리
        if len(current_phrase) >= 2:
            noun_phrases.append(' '.join(current_phrase))

        return noun_phrases

    def normalize_text(self, text: str) -> str:
        """
        텍스트 정규화 (조사 제거, 원형 복원)

        예시:
        "저염식이 효과적입니다" → "저염식 효과적"
        """
        tokens = self._kiwi.tokenize(text)

        # 조사 제거, 용언은 원형으로
        normalized = []
        for token in tokens:
            if token.tag not in {'JKS', 'JKC', 'JKG', 'JKO', 'JKB', 'JKV', 'JKQ', 'JX', 'JC'}:
                # 동사/형용사는 원형 사용
                if token.tag in {'VV', 'VA'}:
                    normalized.append(token.form)
                else:
                    normalized.append(token.form)

        return ' '.join(normalized)
```

### 1.4 ResponseAggregator 개선

**파일**: `backend/Agent/application/response_aggregator.py`

```python
from Agent.utils.korean_nlp import KoreanNLP

class ResponseAggregator:
    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service
        self.korean_nlp = KoreanNLP.get_instance()

    def _extract_required_keywords(
        self,
        agent_results: List[Dict]
    ) -> Dict[str, Set[str]]:
        """
        각 에이전트 응답에서 핵심 키워드 추출 (형태소 분석 기반)

        개선:
        - 조사 제거 ("저염식이" → "저염식")
        - 명사구 추출 ("만성 신장 질환" → 하나의 키워드)
        - 동사/형용사 원형 추출 ("효과적입니다" → "효과적")
        """
        required_keywords = {}

        for item in agent_results:
            agent = item["agent"]
            answer = item["result"].get("answer", "")

            # 1. 일반 키워드 추출 (명사, 동사, 형용사)
            keywords = self.korean_nlp.extract_keywords(answer, top_k=10)

            # 2. 명사구 추출 (복합 개념)
            noun_phrases = self.korean_nlp.extract_noun_phrases(answer)

            # 3. 통합
            all_keywords = keywords.union(set(noun_phrases))

            required_keywords[agent] = all_keywords

        return required_keywords

    def _validate_aggregated_response(
        self,
        response: str,
        agent_results: List[Dict]
    ) -> bool:
        """
        통합 응답 검증 (형태소 분석 기반)

        개선:
        - 정규화된 텍스트로 비교
        - 명사구 일치 검증
        """
        # 1. 응답 정규화
        normalized_response = self.korean_nlp.normalize_text(response)

        # 2. 키워드 추출
        required_keywords = self._extract_required_keywords(agent_results)

        # 3. 검증
        missing_keywords = []

        for agent_type, keywords in required_keywords.items():
            # 정규화된 응답에서 키워드 찾기
            found_count = 0
            for kw in keywords:
                # 원본 키워드 또는 정규화된 키워드로 검색
                if kw in response or kw in normalized_response:
                    found_count += 1

            # 최소 50% 이상의 키워드가 포함되어야 함
            if found_count < len(keywords) * 0.5:
                missing_keywords.append((agent_type, keywords))

        if missing_keywords:
            logger.warning(f"Missing keywords from agents: {missing_keywords}")
            return False

        return True
```

### 1.5 성능 최적화

```python
# 캐싱으로 반복 분석 방지
from functools import lru_cache

class KoreanNLP:
    @lru_cache(maxsize=1000)
    def extract_keywords_cached(self, text: str, top_k: int = 5) -> tuple:
        """캐싱된 키워드 추출 (해시 가능하도록 tuple 반환)"""
        keywords = self.extract_keywords(text, top_k)
        return tuple(sorted(keywords))
```

---

## 2. OpenTelemetry 세부 구현

### 2.1 전체 아키텍처

```
┌─────────────────────────────────────────────────┐
│           FastAPI Application                    │
│  (OpenTelemetry FastAPI Instrumentation)        │
└───────────────────┬─────────────────────────────┘
                    │ Trace Context Propagation
                    ▼
┌─────────────────────────────────────────────────┐
│              QueryRouter                        │
│  Span: query_router.route_and_process          │
└───────────────────┬─────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌───────────────┐      ┌────────────────┐
│IntentClassifier│      │ResponseAggregator│
│ Span: classify │      │ Span: aggregate │
└───────┬───────┘      └────────┬───────┘
        │                       │
        ▼                       ▼
┌─────────────────────────────────────────────────┐
│           Agent Parallel Execution              │
│  Span: multi_intent_processing                  │
│    ├─ Span: agent.nutrition                     │
│    ├─ Span: agent.research_paper                │
│    └─ Span: agent.quiz                          │
└─────────────────────────────────────────────────┘
```

### 2.2 초기 설정

**파일**: `backend/Agent/infrastructure/telemetry.py`

```python
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter  # 개발용
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

def setup_telemetry(app, service_name: str = "careguide-agents"):
    """
    OpenTelemetry 초기화

    Args:
        app: FastAPI 앱 인스턴스
        service_name: 서비스 이름 (Jaeger UI에 표시)
    """
    # 1. Resource 정의 (서비스 메타데이터)
    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: service_name,
        ResourceAttributes.SERVICE_VERSION: "1.0.0",
        ResourceAttributes.DEPLOYMENT_ENVIRONMENT: os.getenv("ENV", "development")
    })

    # 2. TracerProvider 설정
    provider = TracerProvider(resource=resource)

    # 3. Exporter 설정
    if os.getenv("ENV") == "production":
        # 프로덕션: OTLP Exporter (Jaeger/Tempo)
        otlp_exporter = OTLPSpanExporter(
            endpoint=os.getenv("OTLP_ENDPOINT", "http://localhost:4317"),
            insecure=True
        )
        processor = BatchSpanProcessor(otlp_exporter)
    else:
        # 개발: Console Exporter (로그 출력)
        console_exporter = ConsoleSpanExporter()
        processor = BatchSpanProcessor(console_exporter)

    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # 4. FastAPI 자동 계측
    FastAPIInstrumentor.instrument_app(app)

    # 5. HTTPX 자동 계측 (외부 HTTP 호출)
    HTTPXClientInstrumentor().instrument()

    return provider


# Tracer 인스턴스 (전역)
tracer = trace.get_tracer(__name__)
```

### 2.3 컨텍스트 전파 (Trace ID)

**파일**: `backend/Agent/core/remote_agent.py`

```python
from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

class RemoteAgent(BaseAgent):
    async def _send_message(self, session_id: str, message: str):
        """
        Parlant 세션에 메시지 전송 (Trace ID 전파)
        """
        # 1. 현재 스팬 컨텍스트 가져오기
        current_span = trace.get_current_span()

        # 2. HTTP 헤더에 Trace ID 주입
        headers = {}
        TraceContextTextMapPropagator().inject(headers)

        # 3. Parlant API 호출 (헤더 포함)
        response = await self.http_client.post(
            f"{self.base_url}/sessions/{session_id}/messages",
            json={"message": message},
            headers=headers  # traceparent 헤더 포함
        )

        return response
```

**Trace ID 예시**:
```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
             └─ version
                └─ trace-id (32자리 16진수)
                                               └─ parent-id (16자리)
                                                                  └─ flags
```

### 2.4 샘플링 정책

**파일**: `backend/Agent/infrastructure/telemetry.py`

```python
from opentelemetry.sdk.trace.sampling import (
    TraceIdRatioBased,
    ParentBased,
    ALWAYS_ON,
    ALWAYS_OFF
)

def get_sampler():
    """
    샘플링 정책 정의

    프로덕션:
    - 10% 샘플링 (비용 절감)
    - 에러는 항상 수집 (ParentBased)

    개발:
    - 100% 샘플링
    """
    env = os.getenv("ENV", "development")

    if env == "production":
        # 부모 스팬이 샘플링되면 자식도 샘플링
        # 그렇지 않으면 10% 확률
        return ParentBased(
            root=TraceIdRatioBased(0.1)  # 10% 샘플링
        )
    else:
        return ALWAYS_ON  # 개발: 전체 수집


# TracerProvider 생성 시 적용
provider = TracerProvider(
    resource=resource,
    sampler=get_sampler()
)
```

### 2.5 커스텀 속성 및 이벤트

```python
from opentelemetry import trace

class QueryRouter:
    async def route_and_process(
        self,
        user_input: str,
        session_id: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """통합 라우팅 (상세 추적)"""

        with tracer.start_as_current_span("query_router.route_and_process") as span:
            # 1. 속성 설정
            span.set_attribute("session_id", session_id)
            span.set_attribute("input_length", len(user_input))
            span.set_attribute("user_profile", context.get("user_profile", "general"))

            # 2. 이벤트 기록 (주요 단계)
            span.add_event("intent_classification_started")

            intent_result = await self.intent_classifier.classify(user_input)

            span.add_event("intent_classification_completed", {
                "intent_type": intent_result["intent_type"],
                "num_intents": len(intent_result.get("sub_intents", []))
            })

            # 3. 병렬 처리
            if intent_result["intent_type"] == "multi":
                span.add_event("multi_intent_processing_started", {
                    "num_queries": len(intent_result["decomposed_queries"])
                })

                result = await self._process_multi_intent(...)

                span.add_event("multi_intent_processing_completed", {
                    "successful_agents": len(result.get("intents", [])),
                    "failed_agents": len(result.get("failed_intents", []))
                })

            # 4. 성공 상태
            span.set_status(Status(StatusCode.OK))
            span.set_attribute("success", result.get("success", False))

            return result
```

### 2.6 Jaeger UI 연동

**Docker Compose 설정**:
```yaml
# docker-compose.yml
version: '3.8'

services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # Jaeger UI
      - "4317:4317"    # OTLP gRPC
      - "4318:4318"    # OTLP HTTP
    environment:
      - COLLECTOR_OTLP_ENABLED=true
```

**환경 변수**:
```bash
# .env
OTLP_ENDPOINT=http://localhost:4317
ENV=development
```

**접속**:
- Jaeger UI: http://localhost:16686
- 서비스 선택: `careguide-agents`
- Trace ID로 검색 가능

---

## 3. 예외 및 로깅 포맷 일관성

### 3.1 예외 계층 구조 정의

**파일**: `backend/Agent/core/exceptions.py`

```python
from typing import Optional, Any

class AgentError(Exception):
    """
    에이전트 예외 기본 클래스

    모든 에이전트 예외는 이 클래스를 상속해야 함
    """

    def __init__(
        self,
        message: str,
        error_code: str = None,
        original_error: Exception = None,
        metadata: dict = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.original_error = original_error
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        """예외를 딕셔너리로 변환 (로깅, API 응답용)"""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "metadata": self.metadata,
            "original_error": str(self.original_error) if self.original_error else None
        }


# 인프라 계층 예외
class InfrastructureError(AgentError):
    """인프라 계층 오류"""
    pass

class DatabaseConnectionError(InfrastructureError):
    """데이터베이스 연결 오류"""
    def __init__(self, message: str, db_type: str = None, original_error: Exception = None):
        super().__init__(
            message,
            error_code="DB_CONNECTION_ERROR",
            original_error=original_error,
            metadata={"db_type": db_type}
        )

class ExternalServiceError(InfrastructureError):
    """외부 서비스 오류"""
    def __init__(self, message: str, service: str, original_error: Exception = None):
        super().__init__(
            message,
            error_code="EXTERNAL_SERVICE_ERROR",
            original_error=original_error,
            metadata={"service": service}
        )


# 에이전트 계층 예외
class AgentServerUnavailableError(AgentError):
    """에이전트 서버 연결 불가"""
    def __init__(self, message: str, agent_type: str = None, original_error: Exception = None):
        super().__init__(
            message,
            error_code="AGENT_SERVER_UNAVAILABLE",
            original_error=original_error,
            metadata={"agent_type": agent_type}
        )

class AgentTimeoutError(AgentError):
    """에이전트 타임아웃"""
    def __init__(self, message: str, timeout_seconds: float = None, original_error: Exception = None):
        super().__init__(
            message,
            error_code="AGENT_TIMEOUT",
            original_error=original_error,
            metadata={"timeout_seconds": timeout_seconds}
        )

class AgentResponseParseError(AgentError):
    """에이전트 응답 파싱 에러"""
    def __init__(self, message: str, events: list = None, original_error: Exception = None):
        super().__init__(
            message,
            error_code="AGENT_RESPONSE_PARSE_ERROR",
            original_error=original_error,
            metadata={"event_count": len(events) if events else 0}
        )

class AgentCircuitOpenError(AgentError):
    """서킷 브레이커 오픈"""
    def __init__(self, message: str, agent_type: str = None):
        super().__init__(
            message,
            error_code="AGENT_CIRCUIT_OPEN",
            metadata={"agent_type": agent_type}
        )


# 비즈니스 로직 예외
class IntentClassificationError(AgentError):
    """의도 분류 실패"""
    def __init__(self, message: str, user_input: str = None, original_error: Exception = None):
        super().__init__(
            message,
            error_code="INTENT_CLASSIFICATION_ERROR",
            original_error=original_error,
            metadata={"input_length": len(user_input) if user_input else 0}
        )

class ResponseAggregationError(AgentError):
    """응답 통합 실패"""
    def __init__(self, message: str, num_results: int = None, original_error: Exception = None):
        super().__init__(
            message,
            error_code="RESPONSE_AGGREGATION_ERROR",
            original_error=original_error,
            metadata={"num_results": num_results}
        )
```

### 3.2 로깅 표준 포맷

**파일**: `backend/Agent/infrastructure/logging_config.py`

```python
import logging
import json
from datetime import datetime
from typing import Any, Dict

# 로그 레벨 정의
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

class StructuredFormatter(logging.Formatter):
    """
    구조화된 JSON 로그 포맷터

    표준 필드:
    - timestamp: ISO 8601 형식
    - level: 로그 레벨
    - logger: 로거 이름
    - message: 메시지
    - event: 이벤트 타입 (optional)
    - trace_id: Trace ID (optional)
    - span_id: Span ID (optional)
    - error: 에러 정보 (optional)
    """

    RESERVED_ATTRS = {
        'name', 'msg', 'args', 'created', 'filename', 'funcName',
        'levelname', 'levelno', 'lineno', 'module', 'msecs',
        'message', 'pathname', 'process', 'processName', 'relativeCreated',
        'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info'
    }

    def format(self, record: logging.LogRecord) -> str:
        # 기본 필드
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }

        # Trace ID 추가 (OpenTelemetry)
        from opentelemetry import trace
        span = trace.get_current_span()
        if span.is_recording():
            ctx = span.get_span_context()
            log_data["trace_id"] = format(ctx.trace_id, '032x')
            log_data["span_id"] = format(ctx.span_id, '016x')

        # 에러 정보
        if record.exc_info:
            log_data["error"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "stack_trace": self.formatException(record.exc_info)
            }

        # 추가 필드 (extra)
        for key, value in record.__dict__.items():
            if key not in self.RESERVED_ATTRS and not key.startswith('_'):
                log_data[key] = value

        return json.dumps(log_data, ensure_ascii=False, default=str)


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """
    로깅 설정

    Args:
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 로그 파일 경로 (None이면 콘솔만)
    """
    level = LOG_LEVELS.get(log_level.upper(), logging.INFO)

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(console_handler)

    # 파일 핸들러 (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)

    return root_logger
```

### 3.3 로깅 사용 예시

```python
import logging
from Agent.core.exceptions import AgentTimeoutError

logger = logging.getLogger(__name__)

try:
    result = await agent.process(...)
except AgentTimeoutError as e:
    # 예외 정보를 로그에 기록
    logger.error(
        "Agent timeout error",
        extra={
            "event": "agent_timeout",
            "agent_type": e.metadata.get("agent_type"),
            "timeout_seconds": e.metadata.get("timeout_seconds"),
            "session_id": session_id
        },
        exc_info=True  # 스택 트레이스 포함
    )
    raise
```

**로그 출력 예시**:
```json
{
  "timestamp": "2025-11-23T10:30:45.123456Z",
  "level": "ERROR",
  "logger": "Agent.application.router",
  "message": "Agent timeout error",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "event": "agent_timeout",
  "agent_type": "research_paper",
  "timeout_seconds": 30.0,
  "session_id": "abc123",
  "error": {
    "type": "AgentTimeoutError",
    "message": "research_paper server timeout after 30s",
    "stack_trace": "Traceback (most recent call last):\n  ..."
  }
}
```

---

## 4. TaskGroup vs asyncio.gather 사용 가이드

### 4.1 결정 트리

```
사용자가 Python 3.11 이상을 사용하는가?
│
├─ YES → TaskGroup 사용 (권장)
│         - 예외 그룹핑 (ExceptionGroup)
│         - except* 문법
│         - 자동 취소 및 정리
│
└─ NO  → asyncio.gather 사용
          - return_exceptions=True
          - 수동 예외 처리
```

### 4.2 마이그레이션 가이드

**파일**: `backend/Agent/application/router.py`

```python
import sys
from typing import Dict, Any, List, Optional

class QueryRouter:
    def __init__(self, agent_manager, intent_classifier, response_aggregator):
        self.agent_manager = agent_manager
        self.intent_classifier = intent_classifier
        self.response_aggregator = response_aggregator

        # Python 버전에 따라 메서드 선택
        if sys.version_info >= (3, 11):
            self._process_multi_intent = self._process_multi_intent_taskgroup
        else:
            self._process_multi_intent = self._process_multi_intent_gather

    # Python 3.11+ 구현
    async def _process_multi_intent_taskgroup(
        self,
        decomposed_queries: List[Dict],
        session_id: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """TaskGroup 사용 (Python 3.11+)"""
        # ROUTER_IMPROVEMENTS.md 참조
        # ...

    # Python 3.10 이하 구현
    async def _process_multi_intent_gather(
        self,
        decomposed_queries: List[Dict],
        session_id: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """asyncio.gather 사용 (Python 3.10 이하)"""
        # ROUTER_DESIGN.md 참조
        # ...
```

### 4.3 장단점 비교표

| 기능 | asyncio.gather | TaskGroup (3.11+) |
|------|---------------|-------------------|
| **예외 처리** | 수동 (`isinstance` 체크) | 자동 (`except*` 문법) |
| **예외 그룹핑** | 불가능 | ExceptionGroup으로 자동 그룹핑 |
| **작업 취소** | 수동 (`task.cancel()`) | 자동 취소 |
| **디버깅** | 작업 이름 추적 어려움 | `create_task(name=...)` 지원 |
| **가독성** | 중간 | 높음 |
| **Python 버전** | 3.7+ | 3.11+ |
| **권장 용도** | 레거시 코드, 3.10 이하 | 신규 코드, 3.11 이상 |

---

## 5. 프로덕션 체크리스트

### 5.1 코드 품질

- [ ] **한국어 NLP 통합**
  - [ ] Kiwi 또는 Mecab 설치
  - [ ] `KoreanNLP` 클래스 구현
  - [ ] `ResponseAggregator`에 형태소 분석 적용
  - [ ] 키워드 추출 정확도 테스트 (90% 이상)

- [ ] **예외 처리**
  - [ ] 모든 예외가 `AgentError` 상속
  - [ ] `error_code` 필드 정의
  - [ ] `to_dict()` 메서드 구현
  - [ ] 오류 번역 계층 (`ErrorTranslationMiddleware`) 적용

- [ ] **로깅**
  - [ ] JSON 구조화 로깅 적용
  - [ ] Trace ID 포함 (OpenTelemetry)
  - [ ] 민감 정보 마스킹 (사용자 입력 일부만 로깅)
  - [ ] 로그 레벨 환경변수로 설정

### 5.2 성능 및 안정성

- [ ] **병렬 처리**
  - [ ] Python 버전별 분기 (`TaskGroup` vs `gather`)
  - [ ] 타임아웃 설정 (에이전트별 30초)
  - [ ] 부분 성공 허용 (최소 1개 성공 시 응답)

- [ ] **리소스 관리**
  - [ ] HTTP 클라이언트 연결 풀 설정
  - [ ] 서킷 브레이커 적용 (RemoteAgent)
  - [ ] 메모리 캐싱 크기 제한 (`lru_cache` maxsize)

- [ ] **모니터링**
  - [ ] OpenTelemetry 통합
  - [ ] Jaeger/Tempo 연동
  - [ ] 샘플링 정책 설정 (프로덕션 10%)
  - [ ] 대시보드 설정 (Grafana)

### 5.3 테스트

- [ ] **단위 테스트**
  - [ ] 의도 분류 정확도 (YAML 케이스 100% 통과)
  - [ ] 응답 통합 품질 (키워드 포함 검증)
  - [ ] 예외 처리 (모든 예외 타입)

- [ ] **통합 테스트**
  - [ ] 병렬 처리 (2개, 3개 에이전트)
  - [ ] 부분 성공 (1개 실패 시나리오)
  - [ ] 타임아웃 (30초 초과 시나리오)

- [ ] **E2E 테스트**
  - [ ] API 통합 (`/api/agents/query`)
  - [ ] Trace ID 전파 검증
  - [ ] 응답 시간 (P95 < 5초)

### 5.4 문서화

- [ ] **코드 문서**
  - [ ] 주요 클래스 docstring
  - [ ] 복잡한 로직 주석
  - [ ] 타입 힌트 (mypy 검증)

- [ ] **운영 문서**
  - [ ] 배포 가이드
  - [ ] 모니터링 가이드
  - [ ] 트러블슈팅 가이드
  - [ ] API 문서 (OpenAPI)

---

**작성일**: 2025-11-23
**작성자**: Claude Code
**검토 반영**: Expert Review 2차 2025-11-23
**최종 버전**: 1.2
