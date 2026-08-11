# ADR-002: Parlant SDK Orchestration

- **Status**: Proposed
- **Date**: 2026-05-23
- **Related**: `docs/converted/Parlant_Guide.md`, `docs/converted/KidneyWise_TechSpec.md`, `backend/Agent/agent_manager.py`

## Context

CareGuide는 4개 Parlant Agent로 구성된다:

1. **Medical_Welfare** — 의학 정보 + 복지 정보(산정특례·지원금)
2. **Nutrition** — 식단 분석, NutriCoach 위험도, 이미지 OCR
3. **Research_Paper** — PubMed RAG, 논문 비교, 트렌드
4. **Quiz** — RAG 기반 학습 퀴즈 생성·채점

쟁점:
- Parlant Journey(다이얼로그 트리)를 **JSON import**로 정의할지, **코드(파이썬)** 로 정의할지
- 4개 Agent를 **단일 Parlant 인스턴스 + Agent ID 분기**로 운영할지, **별도 인스턴스**로 분리할지
- 의도분류기를 Parlant 내부 분류기에 위임할지, **자체 분류기 후 Agent 라우팅**으로 갈지
- Confidence Score 임계값(<0.7)을 어디서 enforce할지

## Decision

1. **Parlant Journey는 코드(Python)로 정의**한다.
   - JSON 임포트 대비: 버전 관리 용이, 타입 체크 가능, 동적 컨텍스트 주입 쉬움.
2. **단일 Parlant 인스턴스 + Agent ID 분기** 패턴을 채택.
   - `agent_manager.py`가 의도분류 결과 → Agent ID 매핑.
   - Parlant 서버 1개(port 8800)로 운영 단순화.
3. **자체 의도분류기 → Agent 라우팅 패턴** 채택.
   - 10개 카테고리(MEDICAL_INFO/DIET_INFO/RESEARCH/...) 분류기를 backend에서 직접 운영 (정확도 ≥90% — REQ-056).
   - 분류 결과로 Agent 선택 → Parlant 호출.
4. **Confidence Score < 0.7 enforce는 응답 후처리 단계**에서 수행.
   - Agent 응답 후 `confidence_score` 추출 → 임계값 미만이면 "전문의 상담을 권장합니다" 메시지 자동 첨부.
5. **응급 키워드 감지는 의도분류 직전 pre-filter**로 운영.
   - 흉통/호흡곤란/의식저하/경련 → Agent 호출 우회 → 즉시 119 안내.

## Rationale

- **단일 인스턴스**: 4 인스턴스 운영은 메모리·세션 관리 오버헤드. CareGuide 규모(MVP)에선 단일이 합리적.
- **자체 분류기**: 의도분류 정확도를 평가·개선(`eval/router_eval.py`)하려면 자체 코드 구간이 필요.
- **응답 후처리에서 Confidence enforce**: Parlant Journey 내부에서 분기하면 Agent별 중복 정의 필요. 한 곳에서 enforce가 DRY.
- **응급 키워드 pre-filter**: False Negative를 0건으로 만들려면 LLM 호출 전에 차단해야 안전. LLM 응답에 의존 불가.

## Consequences

**Positive**
- 의도분류·안전 정책을 코드로 명시적으로 enforce → 회귀 테스트 가능
- Agent 추가 시 manager에 매핑만 추가하면 됨

**Negative**
- Parlant Journey 정의가 Python 코드와 결합 → Parlant Studio UI로 편집 불가
- 자체 분류기 운영 비용

**Follow-up tasks**
1. `agent_manager.py`에서 응급 pre-filter 함수 분리·테스트 추가
2. Confidence Score 후처리 미들웨어 작성
3. `eval/router_eval.py` CI에 통합
