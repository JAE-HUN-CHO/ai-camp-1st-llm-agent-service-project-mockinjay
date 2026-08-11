# Medical Welfare Agent Implementation Plan

## Overview
Create a standalone `MedicalWelfareAgent` class that:
- Uses the **shared Parlant server** (healthcare_v2_en.py on port 8800)
- Creates a **separate welfare-focused Parlant agent** (no journeys)
- Uses **MongoDB welfare_programs** collection (13 existing programs)
- Allows **frontend component selection** to route queries to either Research or Welfare agent
- Follows the same pattern as `ResearchPaperAgent` but simpler (no journey complexity)

---

## Implementation Steps

### 1. Create Welfare-Specific Parlant Agent in Server (Estimated: 2-3 hours)

**File**: `backend/Agent/research_paper/server/healthcare_v2_en.py`

**Changes**:
- Add a second agent creation: `WelfareGuide` (separate from `CareGuide_v2`)
- Configure with welfare-only tools: `search_welfare_programs`
- Set up welfare-specific guidelines (no medical diagnosis, welfare focus)
- Use simple prompt-response pattern (no journey orchestration)
- Support all 3 user profiles (researcher, patient, general)

**Key differences from CareGuide_v2**:
- Simpler system prompt focused on welfare/benefits
- Only 1 tool registered (`search_welfare_programs`)
- No journeys - direct Q&A pattern
- Returns structured welfare program data

---

### 2. Implement MedicalWelfareAgent Class (Estimated: 3-4 hours)

**File**: `backend/Agent/medical_welfare/agent.py`

**Implementation**:
```python
class MedicalWelfareAgent(BaseAgent):
    - Reuse ResearchPaperAgent's Parlant client singleton pattern
    - Connect to same server (localhost:8800)
    - Use WelfareGuide agent ID (not CareGuide_v2)
    - Implement process() method for welfare queries
    - Handle session management per session_id
    - Return structured response with welfare programs
```

**Pattern to follow**: Copy from `ResearchPaperAgent` but:
- Use `_welfare_agent_id` instead of generic `_agent_id`
- Simpler response parsing (no preamble handling needed)
- Focus on welfare program formatting

---

### 3. Update Agent Manager for Frontend Routing (Estimated: 1 hour)

**File**: `backend/Agent/agent_manager.py`

**Changes**:
- Register `MedicalWelfareAgent` as new agent type
- Add routing logic: check if query is welfare-related
- Allow frontend to specify agent_type in request
- Support agent switching within same session

**Routing Strategy**:
```python
if agent_type == "medical_welfare" or is_welfare_query(query):
    agent = MedicalWelfareAgent()
else:
    agent = ResearchPaperAgent()
```

---

### 4. Create Welfare Prompts and Guidelines (Estimated: 1-2 hours)

**File**: `backend/Agent/medical_welfare/prompts.py`

**Content**:
- System prompt for welfare agent
- User profile-specific prompts (researcher, patient, general)
- Response formatting templates
- Disclaimer text for government programs

**Parlant Guidelines** (in healthcare_v2_en.py):
- Welfare-only guideline (block medical questions)
- Empathy and support guideline
- Application guidance guideline
- Government source citation guideline

---

### 5. Update API Endpoints (Estimated: 1 hour)

**File**: `backend/app/api/welfare.py`

**Changes**:
- Add POST `/api/welfare/chat` endpoint
- Accept: query, session_id, profile, language
- Route to MedicalWelfareAgent
- Return: welfare programs, answer, metadata

**Response Format**:
```json
{
  "answer": "복지 프로그램 설명...",
  "programs": [
    {
      "title": "만성신부전증 산정특례",
      "category": "sangjung_special",
      "benefits": {...},
      "application": {...}
    }
  ],
  "tokens_used": 1500,
  "agent_type": "medical_welfare"
}
```

---

### 6. Frontend Integration Points (Estimated: Info only)

**For frontend team**:
- Add agent selector component (Research vs Welfare tabs/buttons)
- Set `agent_type` parameter in chat requests
- Display welfare programs in structured card format
- Show application steps and contact info prominently

---

### 7. Testing with Evaluation Dataset (Estimated: 2-3 hours)

**Test Cases**:
- Run 18 welfare questions from CSV (CKD_General_025-030, CKD_Patient_026-030, CKD_Researcher_026-030)
- Test all 3 user profiles (researcher, patient, general)
- Verify correct program retrieval
- Check response quality and accuracy
- Measure response time

**Success Criteria**:
- All 18 questions return relevant programs
- Answers match expected_answer context
- Response time < 10 seconds
- No errors or crashes

---

## File Changes Summary

### New/Modified Files:
1. ✅ `backend/Agent/medical_welfare/agent.py` - Complete implementation
2. ✅ `backend/Agent/medical_welfare/prompts.py` - Create welfare prompts
3. ✅ `backend/Agent/medical_welfare/__init__.py` - Export MedicalWelfareAgent
4. ✅ `backend/Agent/research_paper/server/healthcare_v2_en.py` - Add WelfareGuide agent
5. ✅ `backend/Agent/agent_manager.py` - Register welfare agent
6. ✅ `backend/app/api/welfare.py` - Add chat endpoint

### Existing Files (No changes needed):
- `backend/app/db/welfare_manager.py` - Already has WelfareManager
- `backend/app/models/welfare.py` - Already has data models
- `data/welfare/welfare_programs_2025_verified.json` - Already has 13 programs

---

## Architecture Diagram

```
Frontend Component Selection
    ↓
[Research Button] or [Welfare Button]
    ↓
Agent Manager (agent_manager.py)
    ↓
    ├── ResearchPaperAgent → Parlant Server (port 8800) → CareGuide_v2 Agent
    │                                                         ↓
    │                                                    search_medical_qa tool
    │                                                         ↓
    │                                                    5 data sources
    │
    └── MedicalWelfareAgent → Parlant Server (port 8800) → WelfareGuide Agent
                                                              ↓
                                                         search_welfare_programs tool
                                                              ↓
                                                         MongoDB welfare_programs
```

---

## Key Technical Decisions

1. **Shared Server**: Both agents use same Parlant server process (efficient, simpler deployment)
2. **No Journeys**: WelfareGuide uses simple Q&A pattern (no multi-step journey orchestration)
3. **MongoDB Only**: Use existing 13 programs (can expand later)
4. **Profile Support**: All 3 profiles supported (researcher gets detailed citations, general gets simplified)
5. **Frontend Routing**: Frontend controls which agent to use (explicit user choice)

---

## Timeline Estimate

- **Day 1 (4-5 hours)**:
  - Create WelfareGuide agent in healthcare_v2_en.py
  - Implement MedicalWelfareAgent class

- **Day 2 (3-4 hours)**:
  - Create prompts and guidelines
  - Update agent_manager.py
  - Create welfare chat API endpoint

- **Day 3 (2-3 hours)**:
  - Testing with 18 evaluation questions
  - Bug fixes and refinements
  - Documentation

**Total**: 9-12 hours of development work

---

## Success Metrics

1. ✅ MedicalWelfareAgent successfully connects to Parlant server
2. ✅ All 18 welfare questions return relevant programs
3. ✅ Response quality matches or exceeds expected_answer
4. ✅ Response time < 10 seconds per query
5. ✅ All 3 user profiles work correctly
6. ✅ Frontend can switch between Research and Welfare agents
7. ✅ No errors or crashes during testing

---

## Future Enhancements (Post-MVP)

1. **Data Expansion**: Add 20-30 more welfare programs
2. **Semantic Search**: Add Pinecone vector search for better matching
3. **Regional Programs**: Add city/province-specific programs
4. **Document Generation**: Auto-generate application checklists
5. **Multi-language**: Support English responses
6. **Evaluation Pipeline**: Automated testing with BLEU/similarity scores

---

## Evaluation Dataset Details

### Total Welfare Questions: 18

**일반인/노비스 (General/Novice)** - 6 questions:
- CKD_General_025: 투석 환자 복지 혜택
- CKD_General_026: 신장 장애인 등록 기준과 절차
- CKD_General_027: 장애 등록 시 혜택
- CKD_General_028: 정부 지원 신청 서류
- CKD_General_029: 이식 후 장애 혜택
- CKD_General_030: 가족 대리 신청

**질환자/경험자 (Patient/Experienced)** - 6 questions:
- CKD_Patient_026: 산정특례 제도
- CKD_Patient_027: 복지카드 할인 혜택
- CKD_Patient_028: 지자체별 추가 지원
- CKD_Patient_029: 투석 환자 이동 지원
- CKD_Patient_030: 희귀질환 추가 지원

**연구자/전문가 (Researcher/Expert)** - 6 questions:
- CKD_Researcher_026: 정부/질병청 계획
- CKD_Researcher_027: KONOS 신장이식 배분 원칙
- CKD_Researcher_028: 복막투석 재택관리 시범사업
- CKD_Researcher_029: 식약처 CKD 식단 가이드
- CKD_Researcher_030: 재생의료 R&D 정부 지원

### Topics Covered:
1. 산정특례 (Sangjung special exemption)
2. 장애등록 (Disability registration)
3. 복지혜택 (Welfare benefits)
4. 정부지원 (Government support)
5. KONOS (Organ transplant system)
6. 식약처 가이드 (MFDS guidelines)
7. 재생의료 R&D (Regenerative medicine R&D)
