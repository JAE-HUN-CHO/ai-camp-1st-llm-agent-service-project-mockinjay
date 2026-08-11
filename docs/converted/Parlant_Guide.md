<!-- Slide number: 1 -->

Parlant 프레임워크 완전 가이드
제어 가능한 AI 에이전트 구축을 위한 솔루션
2025년 10월 30일

<!-- Slide number: 2 -->
목차
  핵심 개념
  Parlant 소개
1
2
  아키텍처 구조
  주요 컴포넌트
3
4
  실전 예제
  SDK 사용법
5
6
  다음 단계
7

<!-- Slide number: 3 -->
AI 에이전트 개발의 문제점과 해결 방식
    기존 AI 에이전트의 문제점
    Parlant의 해결 방식

![Picture 3](Picture3.jpg)

![Picture 15](Picture15.jpg)
    시스템 프롬프트 무시
    가이드라인 기반의 행동 제어

![Picture 17](Picture17.jpg)

![Picture 5](Picture5.jpg)
    중요한 순간의 환각 응답
    명확한 여정(Journey) 정의

![Picture 19](Picture19.jpg)

![Picture 7](Picture7.jpg)
    엣지 케이스 처리의 일관성 부족
    외부 시스템과의 안정적인 통합

![Picture 21](Picture21.jpg)

![Picture 9](Picture9.jpg)
    예측 불가능한 대화 흐름
    예측 가능한 대화 흐름

![Picture 23](Picture23.jpg)

![Picture 11](Picture11.jpg)
 # Parlant 방식: 준수 보장 ✅
 await agent.create_guideline(
 condition="고객이 환불을 문의할 때",
 action="주문 상태를 먼저 확인하여 자격 여부를 판단",
 tools=[check_order_status],
 )
 # 전통적인 방식: 기대에 맡기기 🤞
 system_prompt = "당신은 도움이 되는 어시스턴트입니다. 다음 47가지 규칙을 따르세요..."

<!-- Slide number: 4 -->
Parlant의 주요 특징 및 장점

규정 준수
대화 관리
엔터프라이즈급

![Picture 3](Picture3.jpg)

![Picture 7](Picture7.jpg)

![Picture 11](Picture11.jpg)
 세션, 이벤트, 컨텍스트 변수 등 풍부한 대화 관리 기능 제공
 SLA, 안정성, 보안을 고려한 대규모 설계로 실제 비즈니스 환경에 최적화
 엄격한 가이드라인으로 에이전트 행동을 제어하고 일관된 응답 보장

유연한 통합
헥사고날 아키텍처
빠른 배포

![Picture 15](Picture15.jpg)

![Picture 19](Picture19.jpg)

![Picture 23](Picture23.jpg)
 OpenAI, Anthropic 등 20개 이상의 LLM 제공자 지원으로 다양한 환경에서 활용 가능
 단 몇 분 만에 프로덕션 환경에 AI 에이전트 배포 가능
 깔끔한 계층 분리로 확장과 테스트 용이하며 유지보수 편리

<!-- Slide number: 5 -->
Parlant가 적합한 사용 사례

금융 서비스 고객 상담
의료 예약 및 상담 시스템

![Picture 4](Picture4.jpg)

![Picture 9](Picture9.jpg)
 규제 준수가 중요한 금융 상담 업무에 적합하며, 정확한 정보 제공과 일관된 응답 보장
 정확한 예약 관리와 환자 정보 보호가 필요한 의료 분야에서 안정적인 서비스 제공

법률 자문 챗봇
여행 예약 에이전트

![Picture 14](Picture14.jpg)

![Picture 19](Picture19.jpg)
 법률 용어와 절차에 대한 정확한 정보 제공이 필요한 법률 분야에서 신뢰성 있는 응답
 복잡한 예약 절차와 다양한 옵션 관리가 필요한 여행 산업에서 효율적인 자동화

전자상거래 고객 지원

![Picture 24](Picture24.jpg)
 주문 처리, 반품, 교환 등 복잡한 고객 지원 업무를 자동화하여 운영 효율성 향상

<!-- Slide number: 6 -->
핵심 개념 - Agent와 Session

Agent (에이전트)
Session (세션)

![Picture 19](Picture19.jpg)

![Picture 4](Picture4.jpg)
 AI 에이전트의 기본 단위로, 특정 역할과 목적을 가진 인공지능 비서
 고객과 에이전트 간의 대화를 나타내며, 여러 이벤트로 구성

 session = await server.create_session(
 agent_id=agent.id,
 customer_id=customer.id,
 )
    name: 에이전트의 이름

![Picture 8](Picture8.jpg)
    description: 에이전트의 역할과 목적

![Picture 10](Picture10.jpg)
    max_engine_iterations: 최대 반복 처리 횟수

![Picture 12](Picture12.jpg)
이벤트 유형
    composition_mode: 응답 생성 방식

![Picture 14](Picture14.jpg)

CUSTOM
MESSAGE
TOOL
STATUS

![Picture 35](Picture35.jpg)

![Picture 29](Picture29.jpg)

![Picture 26](Picture26.jpg)

![Picture 32](Picture32.jpg)
 agent = await server.create_agent(
 name="고객 상담 에이전트",
 description="고객의 질문에 친절하게 답변하는 상담 에이전트",
 max_engine_iterations=10,
 composition_mode=CompositionMode.FLUID,
 )
    CUSTOMER: 고객 메시지

![Picture 38](Picture38.jpg)
    AI_AGENT: AI 에이전트 응답

![Picture 40](Picture40.jpg)
    HUMAN_AGENT: 사람 상담원 개입

![Picture 42](Picture42.jpg)

<!-- Slide number: 7 -->

 # 여정 생성
 journey = await agent.create_journey(
 title="예약하기",
 description="고객이 예약을 진행하는 여정",
 )

 # 상태 정의
 date_selection = journey.initial_state.chat(
 action="고객에게 원하는 날짜를 물어봅니다."
 )

 time_selection = date_selection.chat(
 action="선택된 날짜에 사용 가능한 시간을 안내합니다."
 )

 confirmation = time_selection.chat(
 action="예약 내용을 확인하고 최종 확정합니다."
 )

 # 전환 정의
 date_selection.transition_to(
 time_selection,
 condition="고객이 날짜를 선택했을 때"
 )

 # 조건 분기 예시
 fork = availability_check.fork(
 action="예약 가능 여부에 따라 분기합니다."
 )

 available_path = fork.chat(
 action="예약 가능하다고 안내합니다."
 )

 unavailable_path = fork.chat(
 action="예약 불가하다고 안내합니다."
 )

 # 조건부 전환
 fork.transition_to(
 available_path,
 condition="재고가 있을 때"
 )
 fork.transition_to(
 unavailable_path,
 condition="재고가 없을 때"
 )
핵심 개념 - Journey

Journey (여정)

![Picture 3](Picture3.jpg)
 대화의 흐름을 정의하는 상태 머신으로, 예측 가능한 대화 경로 제공

Chat 상태

![Picture 8](Picture8.jpg)
에이전트가 사용자와 대화하는 상태

Tool 상태

![Picture 13](Picture13.jpg)
외부 도구를 실행하는 상태

Fork 상태

![Picture 18](Picture18.jpg)
조건에 따라 여러 경로로 분기하는 상태

상태 전환 예시

→
→
날짜 선택
시간 선택
예약 확인
고객이 날짜 선택
사용 가능 시간 확인
최종 확정

Parlant 프레임워크 완전 가이드

<!-- Slide number: 8 -->
핵심 개념 - Guideline

 # 기본 가이드라인 생성
 guideline = await agent.create_guideline(
 condition="고객이 불만을 제기할 때",
 action="정중하게 사과하고 상급자 연결을 제안합니다.",
 )

 # 도구와 함께 사용
 pricing_guideline = await agent.create_guideline(
 condition="고객이 가격을 문의할 때",
 action="get_pricing 도구를 사용하여 최신 가격을 확인하고 안내합니다.",
 )
 await pricing_guideline.attach_tool("get_pricing")

 # 우선순위 설정
 urgent_guideline = await agent.create_guideline(
 condition="긴급 상황이 발생했을 때",
 action="즉시 담당자에게 연결합니다.",
 )

 normal_guideline = await agent.create_guideline(
 condition="일반적인 문의가 있을 때",
 action="표준 절차에 따라 응답합니다.",
 )

 # 긴급 가이드라인이 일반 가이드라인보다 우선
 await urgent_guideline.prioritize_over(normal_guideline)

 # 후속 가이드라인은 초기 가이드라인에 종속
 followup_guideline = await agent.create_guideline(
 condition="초기 응답 후 추가 정보가 필요할 때",
 action="추가 정보를 요청합니다.",
 )

 await followup_guideline.depend_on(initial_guideline)

 # 특정 가이드라인이 일반 가이드라인을 함의
 await specific_guideline.entail(general_guideline)

Guideline (가이드라인)

![Picture 3](Picture3.jpg)
 조건부 행동 규칙으로, 특정 상황에서 에이전트가 어떻게 행동해야 하는지 정의

우선순위 (Priority)

![Picture 8](Picture8.jpg)
특정 가이드라인이 다른 가이드라인보다 우선 적용

종속성 (Dependency)

![Picture 13](Picture13.jpg)
한 가이드라인이 다른 가이드라인에 의존

함의 (Entailment)

![Picture 18](Picture18.jpg)
특정 가이드라인이 일반 가이드라인을 포함

<!-- Slide number: 9 -->
핵심 개념 - Tool과 Context Variable

Context Variable (컨텍스트 변수)
Tool (도구)

![Picture 3](Picture3.jpg)

![Picture 18](Picture18.jpg)
 외부 시스템과 연동하는 함수로, 에이전트가 실제 데이터에 접근하고 작업을 수행
 세션 간 유지되는 동적 컨텍스트로, 고객별 정보나 상태 저장에 활용

 @p.tool 데코레이터로 정의
 고객별 값 설정 및 조회

![Picture 22](Picture22.jpg)

![Picture 7](Picture7.jpg)

 attach_tool()로 에이전트에 연결
 대화 기록과 상태 유지

![Picture 25](Picture25.jpg)

![Picture 10](Picture10.jpg)

 ToolContext로 세션 정보 접근
 개인화된 응답 생성

![Picture 28](Picture28.jpg)

![Picture 13](Picture13.jpg)
 # 도구 정의
 @p.tool
 async def check_availability(
 date: str,
 context: ToolContext,
 ) -> ToolResult:
 """주어진 날짜의 예약 가능 여부를 확인합니다."""
 # 외부 API 호출 등
 available_slots = await api.get_available_slots(date)

 return ToolResult(
 data={"slots": available_slots},
 metadata={"checked_date": date},
 )

 # 에이전트에 도구 연결
 await agent.attach_tool("check_availability")

 # 변수 생성
 variable = await agent.create_variable(
 name="customer_tier",
 description="고객의 멤버십 등급",
 )

 # 고객별 값 설정
 await variable.set_value_for_customer(
 customer_id=customer.id,
 value="VIP",
 )

 # 값 조회
 tier = await variable.get_value_for_customer(
 customer_id=customer.id
 )

 # 도구에서 값 조회
 @p.tool
 async def checkout(context: ToolContext) -> ToolResult:
 cart = await context.get_variable("shopping_cart")
 # 결제 처리
 return ToolResult(data={"order_id": "12345"})

Parlant 프레임워크 완전 가이드

<!-- Slide number: 10 -->
핵심 개념 - Glossary

도메인별 용어 예시
Glossary (용어집)

![Picture 18](Picture18.jpg)

![Picture 3](Picture3.jpg)
 도메인 특화 용어를 정의하여 에이전트가 전문 용어를 이해하고 일관된 응답 생성

    금융 용어

![Picture 22](Picture22.jpg)
 용어 이름과 상세 설명 정의

![Picture 7](Picture7.jpg)
 APR (연이율): 연간 이자율을 나타내는 표준화된 지표
    동의어: 연이자율, 연간 이율

![Picture 25](Picture25.jpg)
 동의어 등록으로 다양한 표현 인식

![Picture 10](Picture10.jpg)

![Picture 13](Picture13.jpg)
    의료 용어
 도메인 지식을 에이전트에 내재화

![Picture 28](Picture28.jpg)
 초진: 환자가 병원에 처음 방문하여 의사의 진료를 받는 것

 # 용어 생성
 term = await agent.create_term(
 name="간편결제",
 description="신용카드를 등록하여 클릭 한 번으로 결제하는 방식",
 synonyms=["원클릭결제", "자동결제"],
 )

 # 여러 용어 정의
 await agent.create_term(
 name="배송정책",
 description="주문 후 3-5 영업일 내 배송, 무료배송 기준 30,000원 이상",
 )

 await agent.create_term(
 name="반품정책",
 description="구매일로부터 30일 이내 반품 가능, 미개봉 제품만 가능",
 )
    동의어: 첫 진료, 초기 진단

![Picture 31](Picture31.jpg)

<!-- Slide number: 11 -->

아키텍처 구조 - 헥사고날 아키텍처 개요

헥사고날 아키텍처

![Picture 3](Picture3.jpg)

SDK Layer

![Picture 21](Picture21.jpg)
 Parlant는 헥사고날 아키텍처 패턴을 따라 외부 의존성과 분리된 유연한 구조 제공
사용자 진입점, Python API, 데코레이터

API Layer

 명확한 계층 분리로 유지보수 용이

![Picture 26](Picture26.jpg)

![Picture 7](Picture7.jpg)
REST API, FastAPI, 엔드포인트, 미들웨어

 포트-어댑터 패턴으로 외부 시스템과 느슨한 결합

![Picture 10](Picture10.jpg)
Application Layer

![Picture 31](Picture31.jpg)
비즈니스 로직, 엔진, 오케스트레이션

 의존성 역전으로 테스트와 확장성 향상

![Picture 13](Picture13.jpg)

Core Layer

![Picture 36](Picture36.jpg)

 독립적인 개발과 배포 가능
도메인 모델, Port 인터페이스

![Picture 16](Picture16.jpg)

Adapters Layer

![Picture 41](Picture41.jpg)
NLP 서비스, DB, 벡터 DB, 텔레메트리

<!-- Slide number: 12 -->

아키텍처 구조 - 계층별 역할

Core Layer
Adapters Layer

![Picture 4](Picture4.jpg)

![Picture 27](Picture27.jpg)
 순수 비즈니스 로직으로 외부 의존성 없이 도메인 모델 정의
 외부 시스템과의 통합을 담당하는 구현체 계층

NLP 서비스 (20+ 제공자)
벡터 DB
데이터베이스
Agent
Session
Guideline
Journey

![Picture 31](Picture31.jpg)

![Picture 37](Picture37.jpg)

![Picture 34](Picture34.jpg)

![Picture 11](Picture11.jpg)

![Picture 8](Picture8.jpg)

![Picture 17](Picture17.jpg)

![Picture 14](Picture14.jpg)

텔레메트리
로깅
Port 인터페이스
Tool

![Picture 40](Picture40.jpg)

![Picture 43](Picture43.jpg)

![Picture 20](Picture20.jpg)

![Picture 23](Picture23.jpg)

Application Layer
API Layer

![Picture 64](Picture64.jpg)

![Picture 47](Picture47.jpg)
 엔진과 비즈니스 로직을 오케스트레이션하는 계층
 REST API를 통해 외부 시스템과 통신하는 계층

상태 관리
에이전트 실행 엔진
가이드라인 매칭
여정 실행
속도 제한
엔드포인트
인증
CORS
FastAPI

![Picture 60](Picture60.jpg)

![Picture 51](Picture51.jpg)

![Picture 8](Picture8.jpg)

![Picture 74](Picture74.jpg)

![Picture 57](Picture57.jpg)

![Picture 68](Picture68.jpg)

![Picture 54](Picture54.jpg)

![Picture 71](Picture71.jpg)

![Picture 77](Picture77.jpg)

![Picture 80](Picture80.jpg)

SDK Layer

![Picture 84](Picture84.jpg)
 사용자 친화적인 Python API로 프레임워크 기능에 접근

컨텍스트 매니저
간편한 통합
@p.tool 데코레이터
async/await 인터페이스
Python API

![Picture 97](Picture97.jpg)

![Picture 100](Picture100.jpg)

![Picture 91](Picture91.jpg)

![Picture 94](Picture94.jpg)

![Picture 88](Picture88.jpg)
]

<!-- Slide number: 13 -->

주요 컴포넌트 - Session Events와 Composition Modes

Session Events
Composition Modes

![Picture 3](Picture3.jpg)

![Picture 40](Picture40.jpg)
 모든 상호작용을 이벤트로 기록하여 대화 흐름 추적
 에이전트의 응답 생성 방식을 제어하여 일관성 보장

    EventSource (이벤트 출처)

![Picture 8](Picture8.jpg)

FLUID
COMPOSITED

![Picture 52](Picture52.jpg)

![Picture 45](Picture45.jpg)

CUSTOMER
AI_AGENT
HUMAN_AGENT

![Picture 13](Picture13.jpg)

![Picture 16](Picture16.jpg)

![Picture 10](Picture10.jpg)
 LLM이 자유롭게 응답 생성
 준비된 응답의 톤과 스타일을 모방

CUSTOMER_UI
SYSTEM

![Picture 19](Picture19.jpg)

![Picture 22](Picture22.jpg)
    창의적인 대화나 개방형 질문에 적합
    브랜드 목소리 유지가 필요한 고객 서비스

![Picture 49](Picture49.jpg)

![Picture 56](Picture56.jpg)

    EventKind (이벤트 종류)

![Picture 26](Picture26.jpg)

STRICT

![Picture 59](Picture59.jpg)

MESSAGE
TOOL
STATUS
CUSTOM

![Picture 31](Picture31.jpg)

![Picture 37](Picture37.jpg)

![Picture 28](Picture28.jpg)

![Picture 34](Picture34.jpg)
 준비된 응답만 사용 (규정 준수 극대화)
    법률 자문이나 금융 규제가 중요한 분야

![Picture 63](Picture63.jpg)

<!-- Slide number: 14 -->

주요 컴포넌트 - Journey State Types와 Tool Context

Journey State Types
Tool Context

![Picture 28](Picture28.jpg)

![Picture 3](Picture3.jpg)
 여정의 상태 유형으로 대화 흐름을 정의하고 제어
 도구 실행 시 제공되는 컨텍스트로 세션 정보 접근 및 제어

Chat 상태

세션 정보 접근

![Picture 8](Picture8.jpg)

![Picture 33](Picture33.jpg)
 에이전트가 사용자와 대화하는 상태
 에이전트 ID, 세션 ID, 고객 ID 등 핵심 정보에 접근

 greeting = journey.initial_state.chat(
 action="고객에게 인사합니다."
 )

 agent_id = context.agent_id
 session_id = context.session_id
 customer_id = context.customer_id

Tool 상태

로깅

![Picture 15](Picture15.jpg)

![Picture 40](Picture40.jpg)
 외부 도구 실행 상태
 도구 실행 과정을 기록하고 추적

 availability_check = date_request.tool(
 tool_name="check_availability",
 action="예약 가능 여부를 확인합니다."
 )

 context.logger.info("도구 실행 중")
 context.logger.debug("파라미터: {}".format(params))

Fork 상태

이벤트 전송

![Picture 22](Picture22.jpg)

 조건에 따라 여러 경로로 분기

![Picture 47](Picture47.jpg)
 처리 상태를 실시간으로 전달

 fork = availability_check.fork(
 action="예약 가능 여부에 따라 분기합니다."
 )

 fork.transition_to(available_path, "재고가 있을 때")
 fork.transition_to(unavailable_path, "재고가 없을 때")

 await context.emit_status("처리 중...")
 await context.emit_status("완료")

<!-- Slide number: 15 -->
주요 컴포넌트 - Relationships

엔티티 간 관계 정의

![Picture 3](Picture3.jpg)
 엔티티 간 관계를 정의하여 복잡한 상호작용과 의존성 표현

ENTAILMENT
PRIORITY
DEPENDENCY

![Picture 15](Picture15.jpg)

![Picture 8](Picture8.jpg)

![Picture 22](Picture22.jpg)
 함의: A가 있으면 B도 적용
 우선순위: A가 B보다 우선
 종속성: A는 B에 의존

 # 긴급 가이드라인이 일반 가이드라인보다 우선
 await urgent_guideline.prioritize_over(general_guideline)
 # 후속 가이드라인은 초기 가이드라인에 종속
 await followup_guideline.depend_on(initial_guideline)
 # 특정 가이드라인이 일반 가이드라인을 함의
 await specific_guideline.entail(general_guideline)

실제 활용
DISAMBIGUATION
REEVALUATION

![Picture 43](Picture43.jpg)

![Picture 36](Picture36.jpg)

![Picture 29](Picture29.jpg)
 복잡한 비즈니스 로직을 체계적으로 표현
 명확화: A와 B가 겹칠 때
 재평가: A 후 B 재평가

 # 유사한 가이드라인 간 충돌 해결
 await refund_policy.disambiguate(exchange_policy)
 # 다중 관계 설정 예시
 await vip_policy.prioritize_over(standard_policy)
 await vip_policy.entail(premium_benefits)
 await vip_policy.depend_on(customer_verification)
 # 특정 조건 발생 후 다른 가이드라인 재평가
 await special_condition.reevaluate(standard_response)

<!-- Slide number: 16 -->
SDK 사용법 - 기본 설정과 NLP 서비스 설정

기본 설정
NLP 서비스 설정

![Picture 3](Picture3.jpg)

![Picture 29](Picture29.jpg)
 Parlant 프레임워크의 기본 구성 요소 설정 방법
 20개 이상의 LLM 제공자를 지원하는 유연한 설정

서버 생성
OpenAI

1

![Picture 34](Picture34.jpg)
호스트, 포트, NLP 서비스, 세션 저장소 등 설정
가장 널리 사용되는 LLM 서비스

에이전트 생성
Anthropic

2

![Picture 41](Picture41.jpg)
이름, 설명, 최대 반복 횟수, 구성 모드 설정
Claude 모델을 통한 고성능 응답

고객 및 세션 생성

3
Azure OpenAI

고객 정보와 에이전트-고객 간 대화 세션 설정

![Picture 48](Picture48.jpg)
엔터프라이즈 환경에 최적화된 서비스

메시지 전송

4

Ollama (로컬)
세션을 통해 메시지를 전송하고 응답 수신

![Picture 55](Picture55.jpg)
온프레미스 환경에서의 로컬 실행
 # 기본 설정 예시
 async with p.Server(
 host="0.0.0.0",
 port=8800,
 nlp_service=NLPServices.openai(api_key="your-key"),
 session_store="transient",
 ) as server:
 agent = await server.create_agent(
 name="샘플 에이전트",
 description="고객을 돕는 친절한 에이전트"
 )

<!-- Slide number: 17 -->

SDK 사용법 - 도구 정의, 여정 만들기, 가이드라인 만들기, 컨텍스트 사용 (1)

도구 정의
여정 만들기

![Picture 4](Picture4.jpg)

![Picture 11](Picture11.jpg)
 @tool 데코레이터로 외부 시스템과 연동
 상태 체인 구성과 전환 설정으로 대화 흐름 정의
 # 여정 생성
 journey = await agent.create_journey(
 title="호텔 예약",
 description="고객이 호텔을 예약하는 과정"
 )

 # 상태 체인 구성
 search = journey.initial_state.chat(
 action="지역과 날짜를 물어봅니다."
 )

 results = search.tool(
 tool_name="search_hotels",
 action="조건에 맞는 호텔 검색"
 )

 # 전환 설정
 search.transition_to(results,
 condition="고객이 검색 조건 제공"
 )

 # 도구 정의
 @p.tool
 async def get_weather(
 city: str,
 context: ToolContext,
 ) -> ToolResult:
 """도시의 현재 날씨 조회"""
 weather_data = await fetch_weather_api(city)

 return ToolResult(
 data={
 "city": city,
 "temperature": weather_data["temp"],
 },
	 )

 # 에이전트에 도구 연결
 await agent.attach_tool("get_weather")

<!-- Slide number: 18 -->
SDK 사용법 - 도구 정의, 여정 만들기, 가이드라인 만들기, 컨텍스트 사용 (2)

가이드라인 만들기
컨텍스트 변수 사용

![Picture 18](Picture18.jpg)

![Picture 25](Picture25.jpg)
 조건부 행동 규칙과 관계 설정
 세션 간 유지되는 동적 컨텍스트 관리
 # 변수 생성
 cart_variable = await agent.create_variable(
 name="shopping_cart",
 description="고객의 장바구니 내용"
 )

 # 값 설정
 await cart_variable.set_value_for_customer(
 customer_id=customer.id,
 value={
 "items": ["item1", "item2"],
 "total": 50000
 },
 )

 # 도구에서 값 조회
 @p.tool
 async def checkout(context: ToolContext):
 cart = await context.get_variable("shopping_cart")
 # 결제 처리
 return ToolResult(data={"order_id": "12345"})

 # 기본 가이드라인
 greeting = await agent.create_guideline(
 condition="대화가 시작될 때",
 action="밝고 친절하게 인사"
 )

 # 도구와 함께 사용
 pricing_guideline = await agent.create_guideline(
 condition="고객이 가격 문의",
 action="get_pricing 도구 사용"
 )
 await pricing_guideline.attach_tool("get_pricing")

 # 관계 설정
 await vip_guideline.prioritize_over(pricing_guideline)
 # 변수 생성
 cart_variable = await agent.create_variable(
 name="shopping_cart",
 description="고객의 장바구니 내용"
 )

 # 값 설정
 await cart_variable.set_value_for_customer(
 customer_id=customer.id,
 value={
 "items": ["item1", "item2"],
 "total": 50000
 },
 )

 # 도구에서 값 조회
 @p.tool
 async def checkout(context: ToolContext):
 cart = await context.get_variable("shopping_cart")
 # 결제 처리
 return ToolResult(data={"order_id": "12345"})

<!-- Slide number: 19 -->

실전 예제 - 간단한 FAQ 봇과 예약 시스템

예약 시스템
FAQ 봇

![Picture 17](Picture17.jpg)

![Picture 4](Picture4.jpg)
 자주 묻는 질문에 일관된 답변을 제공하는 챗봇
 레스토랑 예약 프로세스를 자동화하는 시스템
 도구 정의로 외부 시스템 연동

![Picture 20](Picture20.jpg)
 에이전트 생성과 기본 설정

![Picture 7](Picture7.jpg)
 여정 생성으로 예약 흐름 정의
 용어 정의로 도메인 지식 내재화

![Picture 22](Picture22.jpg)

![Picture 9](Picture9.jpg)
 조건 분기로 예약 가능 여부 처리
 가이드라인 설정으로 응답 패턴 제어

![Picture 24](Picture24.jpg)

![Picture 11](Picture11.jpg)
 # 도구 정의
 @p.tool
 async def check_availability(
 date: str, time: str,
 context: ToolContext
 ) -> ToolResult:
 available = await db.check_slot(date, time)
 return ToolResult(data={"available": available})

 # 여정 생성
 journey = await agent.create_journey(
 title="레스토랑 예약"
 )

 # 상태 체인 구성
 date_request = greeting.chat(
 action="원하시는 날짜와 시간을 물어봅니다."
 )

 # 조건 분기
 fork = availability_check.fork(
 action="예약 가능 여부에 따라 분기합니다."
 )

 # 에이전트 생성
 agent = await server.create_agent(
 name="FAQ 봇",
 description="자주 묻는 질문에 답변하는 봇"
 )

 # 용어 정의
 await agent.create_term(
 name="배송정책",
 description="주문 후 3-5 영업일 내 배송"
 )

 # 가이드라인 설정
 await agent.create_guideline(
 condition="고객이 배송에 대해 문의할 때",
 action="배송정책을 상세히 설명합니다."
 )

<!-- Slide number: 20 -->

실전 예제 - 멀티 티어 고객 지원

등급별 맞춤 지원
구현 방법

![Picture 3](Picture3.jpg)

![Picture 22](Picture22.jpg)
 고객 등급에 따른 개인화된 응대 시스템
 컨텍스트 변수와 가이드라인 우선순위 활용

 # 컨텍스트 변수로 고객 등급 관리
 tier_variable = await agent.create_variable(
 name="customer_tier",
 description="고객의 멤버십 등급"
 )

 # 등급별 가이드라인 생성
 vip_guideline = await agent.create_guideline(
 condition="VIP 고객이 문의할 때",
 action="최우선으로 응대하고 전담 매니저를 배정합니다.",
 )

 premium_guideline = await agent.create_guideline(
 condition="PREMIUM 고객이 문의할 때",
 action="빠른 응대와 할인 혜택을 안내합니다.",
 )

 basic_guideline = await agent.create_guideline(
 condition="BASIC 고객이 문의할 때",
 action="표준 절차에 따라 응대합니다.",
 )

 # 우선순위 설정
 await vip_guideline.prioritize_over(premium_guideline)
 await premium_guideline.prioritize_over(basic_guideline)

 # 도구로 고객 등급 확인
 @p.tool
 async def get_customer_tier(context: ToolContext) -> ToolResult:
 tier = await context.get_variable("customer_tier")
 if not tier:
 tier = "BASIC"  # 기본값
 return ToolResult(data={"tier": tier})

 await agent.attach_tool("get_customer_tier")

VIP 고객

![Picture 8](Picture8.jpg)
 최우선 응대와 전담 매니저 배정

PREMIUM 고객

![Picture 13](Picture13.jpg)
 빠른 응대와 할인 혜택 안내

BASIC 고객

![Picture 18](Picture18.jpg)
 표준 절차에 따른 응대

<!-- Slide number: 21 -->

다음 단계 및 추가 리소스

학습 경로
추가 리소스

![Picture 3](Picture3.jpg)

![Picture 27](Picture27.jpg)
 Parlant 프레임워크를 체계적으로 학습하는 방법
 Parlant 프레임워크 관련 유용한 자료

튜토리얼 실행
공식 문서

1

![Picture 32](Picture32.jpg)
 tutorial.py 파일을 실행하여 단계별 학습
 상세한 API 참조와 가이드
 https://parlant.io

예제 코드 참고

2
GitHub 저장소

 examples/ 폴더의 실전 예제 확인

![Picture 37](Picture37.jpg)
 소스 코드와 예제 프로젝트
 https://github.com/emcie-co/parlant

API 문서 확인

3

 FastAPI docs 참고 (http://localhost:8800/docs)
이슈 및 질문

![Picture 42](Picture42.jpg)
 커뮤니티 지원과 문제 해결
 GitHub Issues

테스트 코드 학습

4
 tests/ 폴더의 테스트 코드로 패턴 학습

블로그 게시물

![Picture 47](Picture47.jpg)
 심층적인 기술 설명과 비교 분석
 Parlant vs LangGraph, DSPy
