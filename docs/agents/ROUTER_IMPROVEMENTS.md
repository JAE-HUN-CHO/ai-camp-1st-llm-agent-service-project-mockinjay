# Router 설계 개선사항 (전문가 검토 반영)

**작성일**: 2025-11-23
**버전**: 1.1
**기반 문서**: ROUTER_DESIGN.md
**검토 반영**: Expert Review 2025-11-23

---

## 📋 목차

1. [Python 3.11+ TaskGroup 활용](#1-python-311-taskgroup-활용)
2. [Structured Logging 및 오류 번역](#2-structured-logging-및-오류-번역)
3. [asyncio.gather 예외 처리 명시](#3-asynciogather-예외-처리-명시)
4. [종단 간 추적 (OpenTelemetry)](#4-종단-간-추적-opentelemetry)
5. [응답 통합 검증 로직](#5-응답-통합-검증-로직)
6. [테스트 자동화 전략](#6-테스트-자동화-전략)

---

## 1. Python 3.11+ TaskGroup 활용

### 1.1 배경

**현재 방식** (`asyncio.gather` + `return_exceptions=True`):
```python
results = await asyncio.gather(
    *[task for _, _, task in tasks],
    return_exceptions=True
)

# 개별 예외 처리
for result in results:
    if isinstance(result, Exception):
        # 예외 처리
        pass
```

**문제점**:
- 예외 타입별 처리가 복잡함
- 여러 예외를 그룹으로 다루기 어려움
- 예외 계층 구조를 활용하기 어려움

### 1.2 TaskGroup 개선안 (Python 3.11+)

**파일**: `backend/Agent/application/router.py`

```python
import asyncio
from typing import Dict, Any, List

class QueryRouter:
    async def _process_multi_intent_with_taskgroup(
        self,
        decomposed_queries: List[Dict],
        session_id: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """
        Python 3.11+ TaskGroup을 사용한 복합 의도 처리

        장점:
        1. 예외 그룹핑 (ExceptionGroup)
        2. except* 문법으로 타입별 예외 처리
        3. 자동 취소 및 정리
        """
        successful_results = []
        failed_results = []

        try:
            async with asyncio.TaskGroup() as tg:
                tasks = []
                for sub_query in decomposed_queries:
                    # 타임아웃 래핑
                    task = tg.create_task(
                        asyncio.wait_for(
                            self.agent_manager.route_request(
                                agent_type=sub_query["intent"],
                                user_input=sub_query["query"],
                                session_id=session_id,
                                context=context
                            ),
                            timeout=30.0
                        ),
                        name=sub_query["intent"]  # 작업 이름 설정
                    )
                    tasks.append((sub_query["intent"], sub_query["query"], task))

                # TaskGroup은 모든 작업이 완료될 때까지 대기
                # 예외 발생 시 ExceptionGroup으로 감싸서 전달

        except* asyncio.TimeoutError as eg:
            # 타임아웃 예외만 처리
            for exc in eg.exceptions:
                task_name = self._get_task_name_from_exception(exc)
                logger.warning(f"Agent {task_name} timeout after 30s")
                failed_results.append({
                    "agent": task_name,
                    "error": "timeout"
                })

        except* AgentServerUnavailableError as eg:
            # 서버 연결 실패 예외만 처리
            for exc in eg.exceptions:
                task_name = self._get_task_name_from_exception(exc)
                logger.error(f"Agent {task_name} server unavailable: {exc}")
                failed_results.append({
                    "agent": task_name,
                    "error": "server_unavailable"
                })

        except* Exception as eg:
            # 기타 모든 예외
            for exc in eg.exceptions:
                task_name = self._get_task_name_from_exception(exc)
                logger.error(f"Agent {task_name} unexpected error: {exc}", exc_info=exc)
                failed_results.append({
                    "agent": task_name,
                    "error": str(exc)
                })

        # 성공한 작업 수집
        for intent, query, task in tasks:
            if task.done() and not task.cancelled():
                try:
                    result = task.result()
                    if result.get("success"):
                        successful_results.append({
                            "agent": intent,
                            "query": query,
                            "result": result["result"]
                        })
                except Exception:
                    # 이미 except*에서 처리됨
                    pass

        # 부분 성공 허용
        if not successful_results:
            return {
                "success": False,
                "error": "All agents failed",
                "failed_intents": [r["agent"] for r in failed_results]
            }

        # 응답 통합
        aggregated_response = await self.response_aggregator.aggregate(
            successful_results
        )

        return {
            "success": True,
            "type": "multi",
            "intents": [r["agent"] for r in successful_results],
            "individual_results": successful_results,
            "aggregated_response": aggregated_response,
            "partial": len(failed_results) > 0,
            "failed_intents": [r["agent"] for r in failed_results] if failed_results else None
        }

    def _get_task_name_from_exception(self, exc: Exception) -> str:
        """예외에서 작업 이름 추출 (Task.get_name() 사용)"""
        # TaskGroup에서 작업 이름을 추적하는 로직
        # 실제 구현에서는 예외 컨텍스트에서 추출
        return "unknown"
```

### 1.3 TaskGroup vs asyncio.gather 비교

| 특징 | asyncio.gather | TaskGroup (3.11+) |
|------|---------------|-------------------|
| **예외 처리** | `return_exceptions=True` 필요 | 자동으로 ExceptionGroup 생성 |
| **타입별 처리** | 수동 `isinstance()` 체크 | `except*` 문법으로 우아한 처리 |
| **작업 취소** | 수동 취소 필요 | 자동 취소 및 정리 |
| **디버깅** | 작업 이름 추적 어려움 | `create_task(name=...)` 지원 |
| **권장 사용** | Python 3.10 이하 | Python 3.11 이상 |

### 1.4 마이그레이션 전략

```python
# utils/async_helpers.py
import sys

def get_multi_intent_processor():
    """Python 버전에 따라 적절한 프로세서 반환"""
    if sys.version_info >= (3, 11):
        from .router_py311 import process_multi_intent_taskgroup
        return process_multi_intent_taskgroup
    else:
        from .router_legacy import process_multi_intent_gather
        return process_multi_intent_gather
```

---

## 2. Structured Logging 및 오류 번역

### 2.1 Structured Logging 설계

**파일**: `backend/Agent/infrastructure/logging_config.py`

```python
import logging
import json
from datetime import datetime
from typing import Any, Dict

class StructuredLogger:
    """구조화된 JSON 로그 생성"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # JSON 포맷 핸들러
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        self.logger.addHandler(handler)

    def log_agent_request(
        self,
        agent_type: str,
        session_id: str,
        user_input: str,
        context: Dict[str, Any]
    ):
        """에이전트 요청 로그"""
        self.logger.info("agent_request", extra={
            "event": "agent_request",
            "agent_type": agent_type,
            "session_id": session_id,
            "input_length": len(user_input),
            "context_keys": list(context.keys()) if context else [],
            "timestamp": datetime.utcnow().isoformat()
        })

    def log_agent_response(
        self,
        agent_type: str,
        session_id: str,
        success: bool,
        duration_ms: float,
        tokens_used: int = 0
    ):
        """에이전트 응답 로그"""
        self.logger.info("agent_response", extra={
            "event": "agent_response",
            "agent_type": agent_type,
            "session_id": session_id,
            "success": success,
            "duration_ms": duration_ms,
            "tokens_used": tokens_used,
            "timestamp": datetime.utcnow().isoformat()
        })

    def log_agent_error(
        self,
        agent_type: str,
        session_id: str,
        error_type: str,
        error_message: str,
        stack_trace: str = None
    ):
        """에이전트 에러 로그"""
        self.logger.error("agent_error", extra={
            "event": "agent_error",
            "agent_type": agent_type,
            "session_id": session_id,
            "error_type": error_type,
            "error_message": error_message,
            "stack_trace": stack_trace,
            "timestamp": datetime.utcnow().isoformat()
        })


class JsonFormatter(logging.Formatter):
    """JSON 형식 로그 포맷터"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "timestamp": datetime.utcnow().isoformat()
        }

        # extra 필드 병합
        if hasattr(record, "event"):
            log_data.update({
                k: v for k, v in record.__dict__.items()
                if k not in ["name", "msg", "args", "levelname", "levelno", "pathname",
                           "filename", "module", "exc_info", "exc_text", "stack_info",
                           "lineno", "funcName", "created", "msecs", "relativeCreated",
                           "thread", "threadName", "processName", "process", "message"]
            })

        return json.dumps(log_data, ensure_ascii=False)
```

### 2.2 오류 번역 계층 (Error Translation Layer)

**파일**: `backend/Agent/application/middleware/error_middleware.py`

```python
from typing import Dict, Any
from Agent.core.exceptions import (
    AgentError,
    AgentServerUnavailableError,
    AgentTimeoutError,
    InfrastructureError,
    DatabaseConnectionError,
    ExternalServiceError
)

class ErrorTranslationMiddleware:
    """
    인프라 오류를 비즈니스 예외로 번역

    목적:
    1. 비즈니스 로직이 일관된 예외만 처리
    2. 인프라 세부사항 감추기
    3. 사용자 친화적 메시지 생성
    """

    @staticmethod
    def translate_database_error(exc: Exception) -> AgentError:
        """
        MongoDB, Pinecone 등 데이터베이스 오류 번역

        예시:
        - pymongo.errors.ConnectionFailure → DatabaseConnectionError
        - pinecone.exceptions.PineconeException → DatabaseConnectionError
        """
        import pymongo.errors
        import pinecone.exceptions

        if isinstance(exc, pymongo.errors.ConnectionFailure):
            return DatabaseConnectionError(
                "MongoDB 연결 실패. 잠시 후 다시 시도해주세요.",
                original_error=exc
            )
        elif isinstance(exc, pinecone.exceptions.PineconeException):
            return DatabaseConnectionError(
                "벡터 DB 연결 실패. 잠시 후 다시 시도해주세요.",
                original_error=exc
            )
        else:
            return InfrastructureError(
                "데이터베이스 오류가 발생했습니다.",
                original_error=exc
            )

    @staticmethod
    def translate_external_service_error(exc: Exception, service_name: str) -> AgentError:
        """
        외부 서비스 오류 번역

        예시:
        - httpx.ConnectError → ExternalServiceError
        - httpx.TimeoutException → AgentTimeoutError
        """
        import httpx

        if isinstance(exc, httpx.ConnectError):
            return ExternalServiceError(
                f"{service_name} 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.",
                service=service_name,
                original_error=exc
            )
        elif isinstance(exc, httpx.TimeoutException):
            return AgentTimeoutError(
                f"{service_name} 서비스 응답 시간이 초과되었습니다.",
                original_error=exc
            )
        else:
            return ExternalServiceError(
                f"{service_name} 서비스 오류가 발생했습니다.",
                service=service_name,
                original_error=exc
            )


# 커스텀 예외 정의
class InfrastructureError(AgentError):
    """인프라 계층 오류 기본 클래스"""
    pass

class DatabaseConnectionError(InfrastructureError):
    """데이터베이스 연결 오류"""
    pass

class ExternalServiceError(InfrastructureError):
    """외부 서비스 오류"""
    def __init__(self, message: str, service: str, original_error: Exception = None):
        super().__init__(message, original_error)
        self.service = service
```

### 2.3 예외에 추가 정보 남기기 (add_note)

```python
# Python 3.11+
try:
    result = await self.agent_manager.route_request(...)
except AgentError as e:
    # 예외에 추가 컨텍스트 정보 추가
    e.add_note(f"Session ID: {session_id}")
    e.add_note(f"Agent Type: {agent_type}")
    e.add_note(f"User Input Length: {len(user_input)}")
    raise
```

---

## 3. asyncio.gather 예외 처리 명시

### 3.1 기본 동작 문서화

**파일**: `backend/Agent/application/router.py` (주석 추가)

```python
async def _process_multi_intent(
    self,
    decomposed_queries: List[Dict],
    session_id: str,
    context: Optional[Dict]
) -> Dict[str, Any]:
    """
    복합 의도 처리 (asyncio.gather 사용)

    **asyncio.gather 예외 처리 전략**:

    1. **기본 동작** (return_exceptions=False):
       - 하나의 작업에서 예외 발생 시 즉시 예외 전파
       - 다른 작업은 취소되지 않지만 결과를 기다리지 않음
       - 전체 gather가 예외와 함께 실패

    2. **부분 성공 허용** (return_exceptions=True):
       - 예외를 값으로 반환하여 다른 작업이 완료될 때까지 실행
       - 각 결과를 검사하여 성공/실패 분리
       - 최소 1개 성공 시 통합 응답 생성

    **선택 이유**:
    - 영양 에이전트 성공 + 논문 에이전트 실패 시에도 영양 정보 제공
    - 사용자 경험 향상 (전체 실패보다 부분 성공이 나음)
    - 외부 서비스(Parlant) 불안정성 대비

    **참고**:
    - Python 3.11+에서는 TaskGroup + ExceptionGroup 사용 권장
    - 현재는 하위 호환성을 위해 gather 사용
    """
    tasks = []
    for sub_query in decomposed_queries:
        task = self.agent_manager.route_request(
            agent_type=sub_query["intent"],
            user_input=sub_query["query"],
            session_id=session_id,
            context=context
        )
        tasks.append((sub_query["intent"], sub_query["query"], task))

    # return_exceptions=True: 예외를 결과값으로 반환
    # 하나의 에이전트 실패가 다른 에이전트를 방해하지 않음
    results = await asyncio.gather(
        *[
            asyncio.wait_for(task, timeout=30.0)
            for _, _, task in tasks
        ],
        return_exceptions=True  # 부분 성공 허용
    )

    # 성공/실패 분리
    successful_results = []
    failed_results = []

    for (agent_type, query, _), result in zip(tasks, results):
        if isinstance(result, asyncio.TimeoutError):
            logger.warning(f"Agent {agent_type} timeout")
            failed_results.append({"agent": agent_type, "error": "timeout"})

        elif isinstance(result, Exception):
            logger.error(f"Agent {agent_type} failed: {result}")
            failed_results.append({"agent": agent_type, "error": str(result)})

        elif result.get("success"):
            successful_results.append({
                "agent": agent_type,
                "query": query,
                "result": result["result"]
            })

    # ... (나머지 로직)
```

---

## 4. 종단 간 추적 (OpenTelemetry)

### 4.1 OpenTelemetry 통합

**파일**: `backend/Agent/infrastructure/telemetry.py`

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Tracer 설정
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# OTLP Exporter (Jaeger, Zipkin 등)
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# FastAPI 자동 계측
def setup_telemetry(app):
    """FastAPI 앱에 OpenTelemetry 통합"""
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
```

### 4.2 QueryRouter에 추적 추가

```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer(__name__)

class QueryRouter:
    async def route_and_process(
        self,
        user_input: str,
        session_id: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """통합 라우팅 (분산 추적 포함)"""

        # 루트 스팬 시작
        with tracer.start_as_current_span("query_router.route_and_process") as span:
            # 스팬 속성 설정
            span.set_attribute("session_id", session_id)
            span.set_attribute("input_length", len(user_input))

            try:
                # 1. 의도 분류
                with tracer.start_as_current_span("intent_classification") as classify_span:
                    intent_result = await self.intent_classifier.classify(user_input)
                    classify_span.set_attribute("intent_type", intent_result["intent_type"])
                    classify_span.set_attribute("num_intents", len(intent_result.get("sub_intents", [])))

                # 2. 처리 분기
                if intent_result["intent_type"] == "single":
                    result = await self._process_single_intent(...)
                else:
                    result = await self._process_multi_intent(...)

                # 성공 상태 기록
                span.set_status(Status(StatusCode.OK))
                span.set_attribute("success", result.get("success", False))

                return result

            except Exception as e:
                # 실패 상태 기록
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    async def _process_multi_intent(
        self,
        decomposed_queries: List[Dict],
        session_id: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """복합 의도 처리 (각 에이전트 스팬 생성)"""

        with tracer.start_as_current_span("multi_intent_processing") as span:
            span.set_attribute("num_queries", len(decomposed_queries))

            tasks = []
            for sub_query in decomposed_queries:
                # 각 에이전트 호출을 자식 스팬으로 추적
                task = self._call_agent_with_span(
                    agent_type=sub_query["intent"],
                    query=sub_query["query"],
                    session_id=session_id,
                    context=context
                )
                tasks.append((sub_query["intent"], sub_query["query"], task))

            results = await asyncio.gather(*[task for _, _, task in tasks], return_exceptions=True)

            # 성공/실패 통계
            successful_count = sum(1 for r in results if not isinstance(r, Exception) and r.get("success"))
            failed_count = len(results) - successful_count

            span.set_attribute("successful_agents", successful_count)
            span.set_attribute("failed_agents", failed_count)

            # ... (나머지 로직)

    async def _call_agent_with_span(
        self,
        agent_type: str,
        query: str,
        session_id: str,
        context: Optional[Dict]
    ):
        """에이전트 호출 (자식 스팬 생성)"""

        with tracer.start_as_current_span(f"agent.{agent_type}") as span:
            span.set_attribute("agent_type", agent_type)
            span.set_attribute("query", query[:100])  # 처음 100자만

            start_time = time.time()

            try:
                result = await self.agent_manager.route_request(
                    agent_type=agent_type,
                    user_input=query,
                    session_id=session_id,
                    context=context
                )

                duration_ms = (time.time() - start_time) * 1000
                span.set_attribute("duration_ms", duration_ms)
                span.set_attribute("success", result.get("success", False))

                if result.get("success"):
                    span.set_attribute("tokens_used", result["result"].get("tokens_used", 0))

                return result

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
```

### 4.3 Trace ID 전파

```python
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

propagator = TraceContextTextMapPropagator()

# HTTP 헤더에 Trace ID 주입
async def call_remote_agent(url: str, data: Dict):
    headers = {}
    propagator.inject(headers)  # traceparent, tracestate 헤더 추가

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        return response.json()
```

---

## 5. 응답 통합 검증 로직

### 5.1 검증 메서드 구현

**파일**: `backend/Agent/application/response_aggregator.py`

```python
from typing import List, Dict, Set

class ResponseAggregator:
    async def aggregate(self, agent_results: List[Dict]) -> str:
        # 1. 응답 추출
        formatted_results = self._extract_answers(agent_results)

        # 2. GPT-4o 통합
        response = await self.openai_service.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": RESPONSE_AGGREGATION_PROMPT},
                {"role": "user", "content": json.dumps(formatted_results, ensure_ascii=False)}
            ],
            temperature=0.7,
            max_tokens=2000
        )

        aggregated_response = response.choices[0].message.content

        # 3. 검증
        is_valid = self._validate_aggregated_response(aggregated_response, agent_results)

        if not is_valid:
            logger.warning("Aggregated response validation failed")
            # 폴백: 각 에이전트 응답을 단순 나열
            return self._fallback_aggregation(agent_results)

        return aggregated_response

    def _validate_aggregated_response(
        self,
        response: str,
        agent_results: List[Dict]
    ) -> bool:
        """
        통합 응답 검증

        검증 규칙:
        1. 모든 에이전트의 핵심 키워드가 포함되었는지
        2. 최소 길이 충족 (각 에이전트당 100자 이상)
        3. 특정 에이전트의 정보가 누락되지 않았는지
        """
        # 1. 핵심 키워드 추출
        required_keywords = self._extract_required_keywords(agent_results)

        # 2. 응답에 포함 여부 확인
        response_lower = response.lower()
        missing_keywords = []

        for agent_type, keywords in required_keywords.items():
            found = any(kw.lower() in response_lower for kw in keywords)
            if not found:
                missing_keywords.append((agent_type, keywords))

        if missing_keywords:
            logger.warning(f"Missing keywords from agents: {missing_keywords}")
            return False

        # 3. 최소 길이 검증
        min_length = len(agent_results) * 100
        if len(response) < min_length:
            logger.warning(f"Response too short: {len(response)} < {min_length}")
            return False

        return True

    def _extract_required_keywords(
        self,
        agent_results: List[Dict]
    ) -> Dict[str, Set[str]]:
        """
        각 에이전트 응답에서 핵심 키워드 추출

        예시:
        - nutrition: {"칼륨", "나트륨", "레시피"}
        - research_paper: {"논문", "연구", "Journal"}
        """
        required_keywords = {}

        for item in agent_results:
            agent = item["agent"]
            answer = item["result"].get("answer", "")

            # 간단한 키워드 추출 (TF-IDF, NER 등 고급 방법 사용 가능)
            keywords = self._extract_keywords_simple(answer)
            required_keywords[agent] = keywords

        return required_keywords

    def _extract_keywords_simple(self, text: str) -> Set[str]:
        """간단한 키워드 추출 (상위 빈도 명사)"""
        # 실제 구현에서는 형태소 분석기(Mecab, KoNLPy 등) 사용 권장
        words = text.split()
        # 길이 3 이상, 상위 5개
        keywords = sorted(
            [w for w in set(words) if len(w) >= 3],
            key=lambda w: text.count(w),
            reverse=True
        )[:5]
        return set(keywords)

    def _fallback_aggregation(self, agent_results: List[Dict]) -> str:
        """
        폴백: 단순 나열

        GPT-4o 통합이 실패했을 때 사용
        """
        sections = []

        for item in agent_results:
            agent = item["agent"]
            answer = item["result"].get("answer", "")

            # 에이전트별 제목 추가
            agent_names = {
                "nutrition": "영양 정보",
                "research_paper": "관련 논문",
                "medical_welfare": "복지 정보",
                "quiz": "퀴즈"
            }
            title = agent_names.get(agent, agent)

            sections.append(f"## {title}\n\n{answer}")

        return "\n\n---\n\n".join(sections)
```

---

## 6. 테스트 자동화 전략

### 6.1 의도 분류 테스트 케이스 (YAML)

**파일**: `backend/tests/fixtures/intent_classification_cases.yaml`

```yaml
# 단일 의도 케이스
single_intent_cases:
  - input: "당근의 칼륨 함량은?"
    expected:
      intent_type: single
      primary_intent: nutrition
      sub_intents: []

  - input: "신장병 관련 최신 논문 찾아줘"
    expected:
      intent_type: single
      primary_intent: research_paper
      sub_intents: []

  - input: "근처 병원 알려줘"
    expected:
      intent_type: single
      primary_intent: medical_welfare
      sub_intents: []

# 복합 의도 케이스 (2개)
multi_intent_2_cases:
  - input: "저염식 레시피 추천하고, 관련 논문도 찾아줘"
    expected:
      intent_type: multi
      primary_intent: nutrition
      sub_intents: [nutrition, research_paper]
      num_decomposed: 2

  - input: "CKD 3기 식단 알려주고, 병원 정보도 필요해"
    expected:
      intent_type: multi
      primary_intent: nutrition
      sub_intents: [nutrition, medical_welfare]
      num_decomposed: 2

# 복합 의도 케이스 (3개)
multi_intent_3_cases:
  - input: "식단 추천, 논문 검색, 퀴즈 풀기"
    expected:
      intent_type: multi
      primary_intent: nutrition
      sub_intents: [nutrition, research_paper, quiz]
      num_decomposed: 3

# 엣지 케이스
edge_cases:
  - input: "안녕하세요"
    expected:
      intent_type: single
      primary_intent: nutrition  # 기본값
      sub_intents: []

  - input: ""
    expected:
      intent_type: single
      primary_intent: nutrition
      sub_intents: []
```

### 6.2 pytest 테스트 스위트

**파일**: `backend/tests/test_intent_classifier_comprehensive.py`

```python
import pytest
import yaml
from pathlib import Path
from Agent.application.intent_classifier import IntentClassifier

# 테스트 케이스 로드
@pytest.fixture
def test_cases():
    yaml_path = Path(__file__).parent / "fixtures" / "intent_classification_cases.yaml"
    with yaml_path.open() as f:
        return yaml.safe_load(f)

@pytest.mark.asyncio
class TestIntentClassifier:
    async def test_single_intent_cases(self, test_cases, intent_classifier):
        """단일 의도 케이스 테스트"""
        for case in test_cases["single_intent_cases"]:
            result = await intent_classifier.classify(case["input"])

            assert result["intent_type"] == case["expected"]["intent_type"]
            assert result["primary_intent"] == case["expected"]["primary_intent"]
            assert result["sub_intents"] == case["expected"]["sub_intents"]

    async def test_multi_intent_2_cases(self, test_cases, intent_classifier):
        """복합 의도 (2개) 케이스 테스트"""
        for case in test_cases["multi_intent_2_cases"]:
            result = await intent_classifier.classify(case["input"])

            assert result["intent_type"] == case["expected"]["intent_type"]
            assert result["primary_intent"] == case["expected"]["primary_intent"]
            assert set(result["sub_intents"]) == set(case["expected"]["sub_intents"])
            assert len(result["decomposed_queries"]) == case["expected"]["num_decomposed"]

    async def test_multi_intent_3_cases(self, test_cases, intent_classifier):
        """복합 의도 (3개) 케이스 테스트"""
        for case in test_cases["multi_intent_3_cases"]:
            result = await intent_classifier.classify(case["input"])

            assert result["intent_type"] == "multi"
            assert len(result["sub_intents"]) == 3

    async def test_edge_cases(self, test_cases, intent_classifier):
        """엣지 케이스 테스트"""
        for case in test_cases["edge_cases"]:
            result = await intent_classifier.classify(case["input"])

            # 기본값으로 폴백
            assert result["intent_type"] == case["expected"]["intent_type"]
```

### 6.3 응답 통합 품질 테스트

**파일**: `backend/tests/test_response_aggregator_quality.py`

```python
@pytest.mark.asyncio
class TestResponseAggregatorQuality:
    async def test_all_agent_info_included(self, response_aggregator):
        """모든 에이전트 정보가 통합 응답에 포함되는지 검증"""
        agent_results = [
            {
                "agent": "nutrition",
                "query": "저염식 레시피",
                "result": {
                    "answer": "저염식 레시피로는 무염 버터를 사용한 감자 샐러드를 추천합니다."
                }
            },
            {
                "agent": "research_paper",
                "query": "저염식 논문",
                "result": {
                    "answer": "2023년 'Journal of Renal Nutrition' 연구에 따르면 저염식이 효과적입니다."
                }
            }
        ]

        aggregated = await response_aggregator.aggregate(agent_results)

        # 각 에이전트의 핵심 정보 포함 여부 확인
        assert "무염 버터" in aggregated
        assert "감자 샐러드" in aggregated
        assert "Journal of Renal Nutrition" in aggregated
        assert "2023년" in aggregated

    async def test_no_duplication(self, response_aggregator):
        """중복 정보가 제거되는지 검증"""
        agent_results = [
            {
                "agent": "nutrition",
                "result": {"answer": "저염식은 나트륨 2000mg 이하입니다. 저염식은 중요합니다."}
            },
            {
                "agent": "research_paper",
                "result": {"answer": "연구에 따르면 저염식은 혈압 조절에 효과적입니다."}
            }
        ]

        aggregated = await response_aggregator.aggregate(agent_results)

        # "저염식"이 과도하게 반복되지 않는지 확인
        count = aggregated.count("저염식")
        assert count <= 5  # 합리적인 반복 횟수

    async def test_minimum_length(self, response_aggregator):
        """통합 응답이 최소 길이를 충족하는지 검증"""
        agent_results = [
            {"agent": "nutrition", "result": {"answer": "A" * 200}},
            {"agent": "research_paper", "result": {"answer": "B" * 200}}
        ]

        aggregated = await response_aggregator.aggregate(agent_results)

        # 최소 200자 (각 에이전트당 100자)
        assert len(aggregated) >= 200
```

---

## 7. 구현 우선순위

### Phase 1: 필수 (즉시 적용)
1. ✅ **Structured Logging**: 디버깅 및 모니터링 필수
2. ✅ **오류 번역 계층**: 일관된 예외 처리
3. ✅ **응답 통합 검증**: 품질 보장

### Phase 2: 권장 (단기)
4. ✅ **asyncio.gather 문서화**: 개발자 이해도 향상
5. ✅ **테스트 자동화**: 의도 분류 및 응답 통합 품질 검증

### Phase 3: 선택 (중기)
6. ⬜ **OpenTelemetry 통합**: 분산 추적 (복잡도 증가, 대규모 서비스 시 필수)
7. ⬜ **TaskGroup 마이그레이션**: Python 3.11+ 업그레이드 시

---

**작성일**: 2025-11-23
**작성자**: Claude Code
**검토 반영**: Expert Review 2025-11-23
