# Parlant 통합 가이드
## Tools & Journey 7 Implementation

**문서**: 03_WELFARE_PARLANT_INTEGRATION.md
**작성일**: 2025-11-19
**선행 문서**: 02_WELFARE_BACKEND_IMPLEMENTATION.md
**다음 문서**: 04_WELFARE_API_REFERENCE.md
**예상 시간**: 4시간

---

## 📋 목차

1. [Parlant 통합 개요](#1-parlant-통합-개요)
2. [search_welfare_programs Tool](#2-search_welfare_programs-tool)
3. [search_hospitals Tool](#3-search_hospitals-tool)
4. [Journey 7 구현](#4-journey-7-구현)
5. [main() 함수 업데이트](#5-main-함수-업데이트)
6. [테스트](#6-테스트)

---

## 1. Parlant 통합 개요

### 1.1 통합 위치

**파일**: `backend/Agent/research_paper/server/healthcare_v2_en.py`
**현재 상태**: 1,860줄, 2 Journeys, 4 Tools
**추가 예정**: 2 Tools, 1 Journey

### 1.2 기존 구조 이해

**현재 Tools** (4개):
```python
@p.tool
async def search_medical_qa(...)       # Line 326-530

@p.tool
async def get_kidney_stage_info(...)   # Line 716-775

@p.tool
async def get_symptom_info(...)        # Line 777-809

@p.tool
async def check_emergency_keywords(...) # Line 1010-1060
```

**현재 Journeys** (2개):
```python
async def create_medical_info_journey(agent) -> p.Journey:  # Line 1373-1503

async def create_research_paper_journey(agent) -> p.Journey:  # Line 1506-1759
```

**추가할 위치**:
- **Tools**: Line 1060 이후 (check_emergency_keywords 아래)
- **Journey**: Line 1760 이후 (create_research_paper_journey 아래)

---

## 2. search_welfare_programs Tool

### 2.1 Tool 위치 및 코드

**파일**: `backend/Agent/research_paper/server/healthcare_v2_en.py`
**라인**: 1060 이후 추가

```python
# ==================== Welfare Programs Tool ====================

# Global WelfareManager instance (SEARCH_ENGINE 패턴)
WELFARE_MANAGER: Optional[WelfareManager] = None

async def initialize_welfare_manager():
    """Initialize WelfareManager singleton

    SEARCH_ENGINE 초기화 패턴 적용 (Line 191-221)
    """
    global WELFARE_MANAGER
    if WELFARE_MANAGER is None:
        from app.db.welfare_manager import WelfareManager
        WELFARE_MANAGER = WelfareManager()
        await WELFARE_MANAGER.connect()
        logger.info("✅ WelfareManager initialized for Parlant Tool")


@p.tool
async def search_welfare_programs(
    context: ToolContext,
    query: str,
    category: Optional[str] = None,
    disease: Optional[str] = None,
    ckd_stage: Optional[int] = None
) -> ToolResult:
    """Search welfare programs for CKD patients

    이 도구는 만성콩팥병 환자를 위한 복지 프로그램을 검색합니다.
    산정특례, 장애인 복지, 의료비 지원, 신장이식 지원, 교통비 지원 등을 찾을 수 있습니다.

    **주요 카테고리**:
    - sangjung_special: 산정특례 제도 (본인부담금 감면)
    - disability: 장애인 복지 혜택
    - medical_aid: 저소득층 의료비 지원
    - transplant: 신장이식 지원
    - transport: 투석 환자 교통비 지원

    **사용 예시**:
    - search_welfare_programs(query="산정특례")
    - search_welfare_programs(query="의료비", category="medical_aid")
    - search_welfare_programs(query="지원", ckd_stage=4)

    Args:
        context: Tool execution context (automatic)
        query: 검색어 (e.g., "산정특례", "장애인 등록", "의료비 지원")
        category: 카테고리 필터 (optional)
        disease: 질병 필터 (e.g., "CKD", "ESRD", "dialysis") (optional)
        ckd_stage: CKD 단계 필터 1-5 (optional)

    Returns:
        ToolResult containing:
        - results: 검색된 프로그램 리스트
        - synthesis_prompt: LLM이 사용할 합성 프롬프트
        - metadata: 검색 메타데이터 (count, response_time)
    """
    start_time = time.time()

    try:
        # Initialize WelfareManager (singleton)
        await initialize_welfare_manager()

        # Get profile for result limiting (search_medical_qa 패턴, Line 368-371)
        profile = await get_profile(context)
        max_results = PROFILE_LIMITS[profile]["max_results"]

        logger.info(f"[WELFARE TOOL] Search started: query='{query}', profile='{profile}', max={max_results}")

        # Build filters (search_medical_qa 패턴, Line 402-411)
        filters = {}
        if category:
            filters["category"] = category
            logger.info(f"[WELFARE TOOL] Filter: category={category}")

        if disease:
            filters["target_disease"] = {"$in": [disease]}
            logger.info(f"[WELFARE TOOL] Filter: disease={disease}")

        if ckd_stage:
            filters["eligibility.ckd_stage"] = {"$in": [ckd_stage]}
            logger.info(f"[WELFARE TOOL] Filter: ckd_stage={ckd_stage}")

        # Execute search
        results = await WELFARE_MANAGER.search_by_text(
            query=query,
            limit=max_results,
            filters=filters if filters else None
        )

        logger.info(f"[WELFARE TOOL] Search completed: {len(results)} results in {time.time()-start_time:.3f}s")

        # Format results for LLM (search_medical_qa 패턴, Line 458-485)
        formatted_results = []
        for prog in results:
            formatted_results.append({
                "programId": prog.get("programId"),
                "title": prog.get("title"),
                "category": prog.get("category"),
                "description": prog.get("description"),
                "benefits": prog.get("benefits", {}),
                "application": prog.get("application", {}),
                "contact": prog.get("contact", {}),
                "keywords": prog.get("keywords", []),
                "score": prog.get("score", 0)
            })

        # Generate LLM synthesis prompt (llm_refine_results_v2 패턴, Line 242-318)
        synthesis_prompt = f"""You are CareGuide, an AI assistant helping CKD patients find welfare programs.

**User Query**: "{query}"
**User Profile**: {profile}
  - researcher: Provide detailed, academic-level information
  - patient: Provide practical, step-by-step guidance
  - general: Provide simple, easy-to-understand explanation

**Search Results**: {len(formatted_results)} welfare programs found

**Programs**:
{json.dumps(formatted_results, ensure_ascii=False, indent=2)}

**Your Task**:
Synthesize the above welfare program information into a comprehensive, helpful response.

**Required Content**:
1. **Brief Summary** (1-2 sentences):
   - Overview of available programs

2. **Program Details** (for each program):
   - 💳 Program name and category
   - 📋 Eligibility requirements (who can apply)
   - ✨ Benefits (copay reduction, financial support, etc.)
   - 📝 Application process (step-by-step)
   - 📄 Required documents (bulleted list)
   - 📍 Where to apply
   - ⏱️ Processing time
   - 📞 Contact information (phone number, website)

3. **Important Notes**:
   - Clarify that final eligibility is determined by authorities
   - Provide specific contact numbers for personalized guidance
   - Encourage users to contact programs directly

4. **Next Steps**:
   - Suggest related programs if applicable
   - Offer to find nearby hospitals/application centers

**Response Style**:
{'Academic and detailed with references' if profile == 'researcher' else 'Practical and supportive with examples' if profile == 'patient' else 'Simple and encouraging'}

**Language**: Use Korean (한국어) for all responses.

**Format**:
- Use markdown formatting
- Use emojis for visual clarity (💳, 📋, ✨, etc.)
- Bold important information
- Use bullet points and numbered lists

**Disclaimer**:
Always remind users that this is general information and they should contact the relevant authorities for personalized eligibility assessment.
"""

        elapsed = time.time() - start_time

        return ToolResult(
            data={
                "query": query,
                "category": category,
                "disease": disease,
                "ckd_stage": ckd_stage,
                "profile": profile,
                "results": formatted_results,
                "synthesis_prompt": synthesis_prompt,
                "metadata": {
                    "count": len(formatted_results),
                    "response_time": f"{elapsed:.3f}s",
                    "max_results": max_results,
                    "filters_applied": bool(filters)
                }
            }
        )

    except Exception as e:
        logger.error(f"[WELFARE TOOL] Error: {e}", exc_info=True)
        return ToolResult(
            data={
                "error": str(e),
                "query": query,
                "results": [],
                "synthesis_prompt": f"An error occurred while searching welfare programs: {e}"
            }
        )
```

### 2.2 Import 추가

**파일**: `backend/Agent/research_paper/server/healthcare_v2_en.py`
**라인**: 상단 import 섹션

```python
# 기존 imports
import parlant as p
from parlant import ServerContext, ToolContext, ToolResult
import json
import logging
# ... 기타 imports ...

# 추가 import (Line 20 근처)
from app.db.welfare_manager import WelfareManager  # 추가
from app.db.hospital_manager import HospitalManager  # 추가 (기존에 없다면)
```

---

## 3. search_hospitals Tool

### 3.1 Tool 코드

**파일**: `backend/Agent/research_paper/server/healthcare_v2_en.py`
**라인**: search_welfare_programs 아래

```python
# ==================== Hospital Search Tool ====================

# Global HospitalManager instance
HOSPITAL_MANAGER: Optional[HospitalManager] = None

async def initialize_hospital_manager():
    """Initialize HospitalManager singleton"""
    global HOSPITAL_MANAGER
    if HOSPITAL_MANAGER is None:
        from app.db.hospital_manager import HospitalManager
        HOSPITAL_MANAGER = HospitalManager()
        await HOSPITAL_MANAGER.connect()
        logger.info("✅ HospitalManager initialized for Parlant Tool")


@p.tool
async def search_hospitals(
    context: ToolContext,
    query: Optional[str] = None,
    region: Optional[str] = None,
    has_dialysis: Optional[bool] = None,
    night_dialysis: Optional[bool] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    max_distance_km: Optional[float] = 10.0
) -> ToolResult:
    """Search hospitals, pharmacies, and dialysis centers

    이 도구는 병원, 약국, 투석센터를 검색합니다.
    특히 복지 프로그램 신청이 가능한 병원이나 투석 가능한 병원을 찾을 수 있습니다.

    **104,836개** 병원/약국 데이터베이스에서 검색합니다.

    **검색 방법**:
    1. Text search: query parameter (e.g., "서울대병원")
    2. Regional search: region parameter (e.g., "서울", "부산")
    3. Nearby search: latitude + longitude (e.g., 37.5826, 127.0001)

    **사용 예시**:
    - search_hospitals(region="서울", has_dialysis=True)
    - search_hospitals(query="서울대병원")
    - search_hospitals(latitude=37.5826, longitude=127.0001, max_distance_km=5.0)

    Args:
        context: Tool execution context (automatic)
        query: 병원명 또는 검색어 (optional)
        region: 지역 (e.g., "서울", "부산", "대구") (optional)
        has_dialysis: 투석 가능 병원만 (optional)
        night_dialysis: 야간 투석 가능 병원만 (optional)
        latitude: 사용자 위도 (nearby search용) (optional)
        longitude: 사용자 경도 (nearby search용) (optional)
        max_distance_km: 최대 거리 (km) (default: 10.0)

    Returns:
        ToolResult containing:
        - results: 병원 리스트
        - synthesis_prompt: LLM이 사용할 프롬프트
        - metadata: 검색 메타데이터
    """
    start_time = time.time()

    try:
        # Initialize HospitalManager
        await initialize_hospital_manager()

        # Get profile for result limiting
        profile = await get_profile(context)
        max_results = PROFILE_LIMITS[profile]["max_results"] * 2  # 병원은 더 많이 표시

        logger.info(f"[HOSPITAL TOOL] Search started: query='{query}', region='{region}', dialysis={has_dialysis}")

        # Determine search method
        results = []

        if latitude is not None and longitude is not None:
            # Nearby search (geospatial)
            logger.info(f"[HOSPITAL TOOL] Using nearby search: lat={latitude}, lng={longitude}, distance={max_distance_km}km")
            results = await HOSPITAL_MANAGER.search_nearby(
                latitude=latitude,
                longitude=longitude,
                max_distance_km=max_distance_km,
                has_dialysis=has_dialysis,
                limit=max_results
            )

        elif region:
            # Regional search
            logger.info(f"[HOSPITAL TOOL] Using regional search: region={region}")
            results = await HOSPITAL_MANAGER.search_by_region(
                region=region,
                has_dialysis=has_dialysis,
                night_dialysis=night_dialysis,
                limit=max_results
            )

        elif query:
            # Text search
            logger.info(f"[HOSPITAL TOOL] Using text search: query={query}")
            filters = {}
            if has_dialysis:
                filters["has_dialysis_unit"] = True
            if night_dialysis:
                filters["night_dialysis"] = True

            results = await HOSPITAL_MANAGER.search_by_text(
                query=query,
                limit=max_results,
                filters=filters if filters else None
            )

        else:
            # Default: Get dialysis centers
            logger.info(f"[HOSPITAL TOOL] Using default: get dialysis centers")
            results = await HOSPITAL_MANAGER.get_dialysis_centers(
                region=region,
                night_only=night_dialysis or False,
                limit=max_results
            )

        logger.info(f"[HOSPITAL TOOL] Search completed: {len(results)} results")

        # Format results
        formatted_results = []
        for hospital in results:
            formatted_results.append({
                "name": hospital.get("name"),
                "address": hospital.get("address"),
                "phone": hospital.get("phone"),
                "region": hospital.get("region"),
                "type": hospital.get("type"),
                "has_dialysis": hospital.get("has_dialysis_unit", False),
                "dialysis_machines": hospital.get("dialysis_machines", 0),
                "night_dialysis": hospital.get("night_dialysis", False),
                "dialysis_days": hospital.get("dialysis_days", []),
                "naver_map": hospital.get("naver_map_url"),
                "kakao_map": hospital.get("kakao_map_url"),
                "distance": hospital.get("distance")  # For nearby search
            })

        # Generate LLM synthesis prompt
        synthesis_prompt = f"""You are CareGuide, helping users find hospitals and dialysis centers.

**Search Parameters**:
- Query: {query or 'N/A'}
- Region: {region or 'N/A'}
- Dialysis capability: {has_dialysis or 'N/A'}
- Night dialysis: {night_dialysis or 'N/A'}
- Location: {f'({latitude}, {longitude})' if latitude else 'N/A'}

**Hospitals Found**: {len(formatted_results)}

**Hospital Data**:
{json.dumps(formatted_results, ensure_ascii=False, indent=2)}

**Your Task**:
Synthesize hospital information into a helpful response.

**Required Content**:
1. **Summary**: Brief overview of hospitals found
2. **Hospital List**: For each hospital:
   - 🏥 Hospital name
   - 📍 Address
   - 📞 Phone number
   - 💉 Dialysis capability (if applicable)
     - Number of machines
     - Night dialysis availability
     - Available days
   - 🗺️ Map links (Naver/Kakao)
   - 📏 Distance (if nearby search)

3. **Recommendations**:
   - Best options based on user needs
   - Tips for visiting or contacting

4. **Additional Info**:
   - Hospital operating hours (if known)
   - Parking availability (if known)

**Language**: Use Korean (한국어).

**Format**:
- Use markdown
- Use emojis for clarity
- Bold hospital names
- Provide clickable map links
"""

        elapsed = time.time() - start_time

        return ToolResult(
            data={
                "query": query,
                "region": region,
                "has_dialysis": has_dialysis,
                "night_dialysis": night_dialysis,
                "results": formatted_results,
                "synthesis_prompt": synthesis_prompt,
                "metadata": {
                    "count": len(formatted_results),
                    "response_time": f"{elapsed:.3f}s",
                    "search_method": "nearby" if latitude else ("region" if region else ("text" if query else "default"))
                }
            }
        )

    except Exception as e:
        logger.error(f"[HOSPITAL TOOL] Error: {e}", exc_info=True)
        return ToolResult(
            data={
                "error": str(e),
                "results": [],
                "synthesis_prompt": f"An error occurred while searching hospitals: {e}"
            }
        )
```

---

## 4. Journey 7 구현

### 4.1 Journey 함수

**파일**: `backend/Agent/research_paper/server/healthcare_v2_en.py`
**라인**: 1760 이후 추가

```python
# ==================== Journey 7: Welfare Support Journey ====================

async def create_welfare_journey(agent: p.Agent) -> p.Journey:
    """복지 지원 Journey (Journey 1 패턴 100% 적용)

    Journey 1 (Medical Information Journey) 구조 참고:
    - Multi-step conversation flow
    - Tool execution (search_welfare_programs, search_hospitals)
    - State transitions with conditions
    - Fork-based user choices
    - Profile-aware responses
    - Journey-level guidelines

    **Steps**:
    0. Welcome and introduce welfare categories
    1. Execute welfare search (tool)
    2. Present results and offer follow-up
    3. (Optional) Find nearby hospitals (tool)
    4. End or loop back

    **Tools Used**:
    - search_welfare_programs: 복지 프로그램 검색
    - search_hospitals: 신청 가능 병원 검색

    **Profile Behavior**:
    - researcher: 10 results, detailed info
    - patient: 5 results, practical advice
    - general: 3 results, simple explanation
    """
    journey = await agent.create_journey(
        title="Welfare Support Journey",
        description="Guide for welfare programs, insurance support, and medical cost reduction for CKD patients",
        conditions=[
            "User asks about welfare programs (복지, 지원, 혜택)",
            "User wants to know about 산정특례 or copay reduction",
            "User needs information about disability registration (장애인 등록)",
            "User asks about medical cost support or insurance benefits (의료비, 본인부담금)",
            "User mentions 교통비 지원 or transport support",
            "User asks how to apply for benefits"
        ]
    )

    # ========================================
    # Step 0: Welcome & Category Introduction
    # ========================================
    t0 = await journey.initial_state.transition_to(
        chat_state="""안녕하세요! 복지 지원 상담에 오신 것을 환영합니다. 🎗️

만성콩팥병 환자를 위한 다양한 복지 혜택을 안내해드립니다:

**주요 복지 프로그램**:

1. 💳 **산정특례** - 본인부담금 90-95% 감면
   - CKD 3기 이상: 본인부담금 10%
   - 혈액투석: 본인부담금 5%
   - 복막투석: 본인부담금 5%

2. 🦽 **장애인 등록** - 장애인 복지 혜택
   - 투석 3개월 이상: 2급
   - 신장이식 후: 5급
   - 장애인연금, 의료비 지원, 주차 스티커 등

3. 💰 **의료비 지원** - 저소득층 의료비
   - 차상위 의료급여 (본인부담금 0-10%)
   - 재난적 의료비 지원 (최대 2,000만원)
   - 긴급 의료비 지원 (최대 300만원)

4. 🏥 **신장이식 지원** - 수술비 및 면역억제제
   - 수술비: 최대 3,000만원
   - 면역억제제: 월 최대 20만원 (평생)

5. 🚗 **교통비 지원** - 투석 환자 교통비
   - 월 15만원 지원 (지자체별 상이)

---

어떤 복지 혜택에 대해 궁금하신가요?
구체적으로 말씀해주시면 자세히 안내해드리겠습니다.

예시:
- "산정특례 신청 방법 알려주세요"
- "장애인 등록하려면 어떻게 하나요?"
- "의료비 지원 받을 수 있나요?"
- "신장이식 수술비 지원은?"
"""
    )

    # ========================================
    # Step 1: Execute Welfare Search (Tool)
    # ========================================
    t1 = await t0.target.transition_to(
        tool_state=search_welfare_programs,
        condition="User specifies welfare program interest or asks specific question about benefits"
    )

    # ========================================
    # Step 2: Present Results
    # ========================================
    t2 = await t1.target.transition_to(
        chat_state="""검색된 복지 프로그램 정보를 바탕으로 상세히 안내해드립니다.

{synthesis_prompt에서 생성된 LLM 응답이 여기에 표시됩니다}

---

**추가로 도움이 필요하신가요?**

다음 옵션 중 선택해주세요:
- 🔍 **다른 복지 프로그램 알아보기** (다른 카테고리나 키워드로 검색)
- 🏥 **근처 신청 가능한 병원 찾기** (산정특례 신청, 장애진단서 발급 등)
- ✅ **상담 종료** (충분한 정보를 얻으셨다면)

원하시는 옵션을 말씀해주세요."""
    )

    # ========================================
    # Step 3: Follow-up Options (Fork)
    # ========================================

    # Option A: Search more programs (loop back to Step 1)
    await t2.target.transition_to(
        state=t1.target,
        condition="User wants to know about other welfare programs or different category"
    )

    # Option B: Find nearby hospitals (new tool execution)
    t3_hospital = await t2.target.transition_to(
        tool_state=search_hospitals,
        condition="User wants to find nearby hospitals or application centers or dialysis centers"
    )

    # ========================================
    # Step 4: Present Hospital Results
    # ========================================
    t4 = await t3_hospital.target.transition_to(
        chat_state="""근처 병원 정보를 안내해드립니다.

{hospital search synthesis_prompt 응답이 여기에 표시됩니다}

---

**다음 단계**:
복지 프로그램 신청은 위 병원에서 가능합니다.
- 산정특례: 병원 원무과 방문
- 장애진단서: 신장내과 진료 예약
- 투석 상담: 투석실 연락

**추가 도움**:
- 다른 지역 병원 찾기
- 다른 복지 프로그램 알아보기
- 상담 종료"""
    )

    # Loop back options from hospital results
    await t4.target.transition_to(
        state=t1.target,
        condition="User wants to explore more welfare programs"
    )

    await t4.target.transition_to(
        state=t3_hospital.target,
        condition="User wants to search hospitals in different region"
    )

    # Option C: End journey
    await t2.target.transition_to(
        state=p.END_JOURNEY,
        condition="User is satisfied or wants to end the conversation or says goodbye"
    )

    await t4.target.transition_to(
        state=p.END_JOURNEY,
        condition="User is satisfied or wants to end"
    )

    # ========================================
    # Journey-level Guidelines
    # ========================================

    # Guideline 1: Eligibility disclaimer
    await journey.create_guideline(
        condition="User asks about specific eligibility requirements or whether they qualify",
        action="""Always remind the user that:

1. You are providing GENERAL guidelines based on typical requirements
2. FINAL ELIGIBILITY is determined by the relevant authorities (국민건강보험공단, 주민센터, KONOS, etc.)
3. Personal circumstances may affect eligibility
4. They should contact the program directly for personalized eligibility assessment

**Example Response Format**:
"일반적으로 [자격 요건]에 해당하는 경우 신청 가능합니다.
하지만 최종 자격 여부는 [담당 기관]에서 개별적으로 판단합니다.
정확한 상담을 위해 [전화번호]로 직접 문의하시는 것을 권장드립니다."

**Tone**: Helpful but cautious, avoiding definitive yes/no answers
"""
    )

    # Guideline 2: Empathetic support
    await journey.create_guideline(
        condition="User expresses financial difficulty, desperation, or emotional distress about medical costs",
        action="""Respond with empathy and comprehensive support:

1. **Acknowledge** their situation with compassion
   - "의료비 부담이 크시겠어요. 여러 지원 제도가 있으니 함께 알아보겠습니다."

2. **Emphasize** that multiple support programs are available
   - List all relevant programs (산정특례, 의료비 지원, 장애인 복지)

3. **Provide** the most relevant programs for their situation
   - Prioritize by impact (산정특례 90% reduction first)

4. **Encourage** them to apply and seek help
   - "포기하지 마시고 꼭 신청하세요"
   - "담당자와 상담하시면 도움받으실 수 있습니다"

5. **Emergency contact** if needed
   - 보건복지콜센터: 국번없이 129
   - 긴급 복지 지원: 주민센터

**Tone**: Warm, supportive, encouraging, non-judgmental
**Avoid**: Minimizing their concerns, making promises about approval
"""
    )

    # Guideline 3: Application process clarity
    await journey.create_guideline(
        condition="User asks about application process or required documents",
        action="""Provide CLEAR, STEP-BY-STEP application instructions:

1. **List steps** in numbered format
   - Step 1: [First action]
   - Step 2: [Second action]
   - ...

2. **Required documents**:
   - Use bullet points
   - Be specific (e.g., "의사 진단서 (희귀난치성질환 등록 신청용)")
   - Mention where to get each document if not obvious

3. **Where to apply**:
   - Provide exact location (e.g., "국민건강보험공단 지사 또는 병원 원무과")
   - Suggest calling ahead to confirm

4. **Processing time**:
   - Set realistic expectations
   - Mention follow-up options if delayed

5. **Contact for questions**:
   - Always provide phone number
   - Encourage calling for clarification

**Format**: Use numbered lists, bullet points, and emojis for visual clarity
"""
    )

    return journey
```

---

## 5. main() 함수 업데이트

### 5.1 Journey 등록

**파일**: `backend/Agent/research_paper/server/healthcare_v2_en.py`
**라인**: 1840 근처 (기존 Journey 생성 부분)

```python
async def main() -> None:
    """Main function to run Parlant server

    Updates:
    - Added Journey 7: Welfare Support Journey
    - Added welfare/hospital journey disambiguation
    - Updated tools list to include welfare and hospital search
    """

    # ... 기존 코드 (server 생성, agent 생성, guidelines 추가) ...

    # ========================================
    # Create Journeys
    # ========================================
    print("\n" + "="*80)
    print("Creating Journeys...")
    print("="*80)

    print("  🗺️ Creating Medical Information Journey...")
    medical_journey = await create_medical_info_journey(agent)
    print(f"     Journey ID: {medical_journey.id}")

    print("  🗺️ Creating Research Paper Journey...")
    research_journey = await create_research_paper_journey(agent)
    print(f"     Journey ID: {research_journey.id}")

    # 추가: Journey 7
    print("  🗺️ Creating Welfare Support Journey...")
    welfare_journey = await create_welfare_journey(agent)
    print(f"     Journey ID: {welfare_journey.id}")

    # ========================================
    # Journey Disambiguation
    # ========================================
    print("\n" + "="*80)
    print("Setting up Journey Disambiguation...")
    print("="*80)

    # Medical vs Research (기존)
    print("  🔀 Medical vs Research disambiguation...")
    paper_inquiry = await agent.create_observation(
        "User asks about research papers, scientific studies, or wants advanced paper analysis, "
        "but it's not clear whether they need basic information or in-depth research analysis"
    )
    await paper_inquiry.disambiguate([medical_journey, research_journey])

    # Medical vs Welfare (추가)
    print("  🔀 Medical vs Welfare disambiguation...")
    welfare_inquiry = await agent.create_observation(
        "User asks about medical costs, insurance benefits, copay reduction, financial support, or welfare programs, "
        "but it's not clear whether they need medical information or welfare program guidance"
    )
    await welfare_inquiry.disambiguate([medical_journey, welfare_journey])

    # Research vs Welfare (추가)
    print("  🔀 Research vs Welfare disambiguation...")
    research_welfare_inquiry = await agent.create_observation(
        "User asks about programs, support systems, or policies, "
        "but it's not clear whether they want research papers about programs or actual welfare benefit information"
    )
    await research_welfare_inquiry.disambiguate([research_journey, welfare_journey])

    # ========================================
    # Server Summary
    # ========================================
    print("\n" + "="*80)
    print("🎉 Parlant Server Started Successfully!")
    print("="*80)
    print(f"  🤖 Agent: {agent.name}")
    print(f"  📋 Guidelines: {len(await agent.list_guidelines())}")
    print(f"  🔧 Tools:")
    print(f"     - search_medical_qa")
    print(f"     - get_kidney_stage_info")
    print(f"     - get_symptom_info")
    print(f"     - check_emergency_keywords")
    print(f"     - search_welfare_programs")  # 추가
    print(f"     - search_hospitals")  # 추가
    print(f"  🗺️ Journeys: {len(await agent.list_journeys())}")
    print(f"     1. Medical Information Journey")
    print(f"     2. Research Paper Deep Dive Journey")
    print(f"     3. Welfare Support Journey")  # 추가
    print("="*80)

    # ... 나머지 코드 (server.run()) ...
```

---

## 6. 테스트

### 6.1 Parlant 서버 재시작

```bash
# 1. 기존 서버 종료 (Ctrl+C)

# 2. 재시작
cd backend
python Agent/research_paper/server/healthcare_v2_en.py

# Expected output:
# ================================================================================
# Creating Journeys...
# ================================================================================
#   🗺️ Creating Medical Information Journey...
#      Journey ID: jrn_abc123
#   🗺️ Creating Research Paper Journey...
#      Journey ID: jrn_def456
#   🗺️ Creating Welfare Support Journey...
#      Journey ID: jrn_ghi789
#
# ================================================================================
# Setting up Journey Disambiguation...
# ================================================================================
#   🔀 Medical vs Research disambiguation...
#   🔀 Medical vs Welfare disambiguation...
#   🔀 Research vs Welfare disambiguation...
#
# ================================================================================
# 🎉 Parlant Server Started Successfully!
# ================================================================================
#   🤖 Agent: CareGuide_v2
#   📋 Guidelines: 11
#   🔧 Tools:
#      - search_medical_qa
#      - get_kidney_stage_info
#      - get_symptom_info
#      - check_emergency_keywords
#      - search_welfare_programs
#      - search_hospitals
#   🗺️ Journeys: 3
#      1. Medical Information Journey
#      2. Research Paper Deep Dive Journey
#      3. Welfare Support Journey
# ================================================================================
```

### 6.2 수동 테스트 (프론트엔드)

**테스트 시나리오 1: 산정특례**

```
사용자: "산정특례 신청 방법 알려주세요"

예상 동작:
1. ✅ Journey 7 시작 (Welfare Support Journey)
2. ✅ Step 0: Welcome 메시지
3. ✅ Step 1: search_welfare_programs(query="산정특례") 실행
4. ✅ Tool 결과: V001, V003, V005
5. ✅ Step 2: LLM 합성 응답
   - 산정특례 제도 설명
   - 본인부담금 10%, 5%
   - 신청 방법 단계별
   - 필요 서류 목록
   - 연락처 1577-1000
6. ✅ Step 3 옵션 제시: "다른 프로그램?", "근처 병원?"

사용자: "근처 병원 찾아줘"

7. ✅ search_hospitals(region="서울", has_dialysis=True) 실행
8. ✅ Tool 결과: 서울대병원, 삼성서울병원 등
9. ✅ Step 4: 병원 목록 표시
   - 이름, 주소, 전화
   - 투석기 수, 야간 투석
   - 지도 링크

사용자: "고마워요"

10. ✅ Journey END
```

**테스트 시나리오 2: 장애인 복지**

```
사용자: "장애인 등록하려면 어떻게 하나요?"

예상 동작:
1. ✅ Journey 7 시작
2. ✅ search_welfare_programs(query="장애인 등록") 실행
3. ✅ 결과: disability_kidney 프로그램
4. ✅ LLM 응답:
   - 자격 요건 (투석 3개월 이상 → 2급)
   - 혜택 (장애인연금 월 20만원, 주차 스티커 등)
   - 신청 방법 (주민센터, 필요 서류)
   - 연락처 129
```

### 6.3 로그 확인

**Parlant 서버 로그**:
```
[INFO] [WELFARE TOOL] Search started: query='산정특례', profile='patient', max=5
[INFO] [WELFARE TOOL] Search completed: 3 results in 0.045s
[INFO] Journey transition: Step 0 → Step 1 (tool execution)
[INFO] Tool executed: search_welfare_programs
[INFO] Journey transition: Step 1 → Step 2 (present results)
```

**FastAPI 로그** (proxy):
```
[INFO] POST /api/chat/message - 200 OK
[INFO] SSE event sent: message
[INFO] SSE event sent: tool (search_welfare_programs)
[INFO] SSE event sent: status (completed)
```

---

## 🔧 트러블슈팅

### 문제 1: Tool이 실행되지 않음
**증상**: Journey는 시작되지만 Tool이 호출 안됨

**해결**:
```python
# 1. Tool이 등록되었는지 확인
tools = await agent.list_tools()
print([t.name for t in tools])
# Expected: ['search_medical_qa', 'search_welfare_programs', ...]

# 2. Journey condition 확인
# "User asks about welfare"가 너무 모호할 수 있음
# 더 구체적인 키워드 추가

# 3. State transition condition 확인
# tool_state=search_welfare_programs 앞의 condition이 맞는지
```

### 문제 2: Journey가 시작되지 않음
**증상**: 사용자 "산정특례" 입력 시 Medical Journey 시작

**해결**:
```python
# 1. Journey conditions 강화
conditions=[
    "User explicitly asks about welfare (복지, 지원, 혜택)",
    "User mentions 산정특례, 장애인, 의료비",
    # ...
]

# 2. Disambiguation 확인
# welfare_inquiry가 제대로 설정되었는지

# 3. Guideline 충돌 확인
# Safety guidelines가 welfare를 차단하지 않는지
```

### 문제 3: WelfareManager import 에러
**증상**:
```
ImportError: cannot import name 'WelfareManager' from 'app.db.welfare_manager'
```

**해결**:
```python
# 1. 파일 경로 확인
ls backend/app/db/welfare_manager.py

# 2. PYTHONPATH 확인
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"

# 3. Import 경로 확인
# healthcare_v2_en.py에서:
from app.db.welfare_manager import WelfareManager  # ✅ Correct
# from welfare_manager import WelfareManager  # ❌ Wrong
```

---

## ✅ Checklist

**Parlant 통합 완료 기준**:

### Tool 구현
- [ ] search_welfare_programs Tool 추가 (healthcare_v2_en.py:1060~)
- [ ] search_hospitals Tool 추가 (healthcare_v2_en.py:1100~)
- [ ] WelfareManager import 추가
- [ ] HospitalManager import 추가
- [ ] initialize_welfare_manager() 함수
- [ ] initialize_hospital_manager() 함수

### Journey 구현
- [ ] create_welfare_journey() 함수 추가 (healthcare_v2_en.py:1760~)
- [ ] Step 0: Welcome state
- [ ] Step 1: search_welfare_programs tool state
- [ ] Step 2: Present results state
- [ ] Step 3: search_hospitals tool state (fork)
- [ ] Step 4: Present hospital results
- [ ] Journey guidelines (3개)

### main() 업데이트
- [ ] Journey 7 생성 (welfare_journey = await create_welfare_journey(agent))
- [ ] Disambiguation 추가 (medical vs welfare)
- [ ] Disambiguation 추가 (research vs welfare)
- [ ] Tools 출력 업데이트 (6개 표시)
- [ ] Journeys 출력 업데이트 (3개 표시)

### 테스트
- [ ] Parlant 서버 재시작 성공
- [ ] Journey 3개 표시 확인
- [ ] Tools 6개 표시 확인
- [ ] "산정특례" 입력 → Journey 7 시작
- [ ] Tool 실행 → 결과 반환
- [ ] "근처 병원" → search_hospitals 실행

---

## 📚 다음 단계

1. ✅ Parlant 통합 완료
2. ✅ Journey 7 작동 확인
3. ➡️ **다음 문서**: `04_WELFARE_API_REFERENCE.md`
4. 구현: REST API 엔드포인트 (선택 사항)

---

**END OF PARLANT INTEGRATION**

Journey 7이 정상 작동하는지 확인했다면,
필요 시 REST API 문서로 이동하거나
테스트 가이드로 바로 이동할 수 있습니다.
