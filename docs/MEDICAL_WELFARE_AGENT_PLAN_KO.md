# 의료복지 에이전트 구현 계획

## 개요
독립적인 `MedicalWelfareAgent` 클래스 생성:
- **공유 Parlant 서버** 사용 (healthcare_v2_en.py, 포트 8800)
- **복지 전용 Parlant 에이전트** 생성 (저니 없음)
- **MongoDB welfare_programs** 컬렉션 사용 (기존 13개 프로그램)
- **프론트엔드 컴포넌트 선택**으로 Research 또는 Welfare 에이전트로 라우팅
- `ResearchPaperAgent`와 동일한 패턴을 따르지만 더 단순함 (저니 복잡성 없음)

---

## 구현 단계

### 1. 서버에 복지 전용 Parlant 에이전트 생성 (예상: 2-3시간)

**파일**: `backend/Agent/research_paper/server/healthcare_v2_en.py`

**변경 사항**:
- 두 번째 에이전트 생성: `WelfareGuide` (CareGuide_v2와 분리)
- 복지 전용 도구 구성: `search_welfare_programs`
- 복지 전용 가이드라인 설정 (의료 진단 금지, 복지 집중)
- 단순 프롬프트-응답 패턴 사용 (저니 오케스트레이션 없음)
- 3가지 사용자 프로필 모두 지원 (researcher, patient, general)

**CareGuide_v2와의 주요 차이점**:
- 복지/혜택에 집중한 더 단순한 시스템 프롬프트
- 1개 도구만 등록 (`search_welfare_programs`)
- 저니 없음 - 직접 Q&A 패턴
- 구조화된 복지 프로그램 데이터 반환

---

### 2. MedicalWelfareAgent 클래스 구현 (예상: 3-4시간)

**파일**: `backend/Agent/medical_welfare/agent.py`

**구현 내용**:
```python
class MedicalWelfareAgent(BaseAgent):
    - ResearchPaperAgent의 Parlant 클라이언트 싱글톤 패턴 재사용
    - 동일한 서버에 연결 (localhost:8800)
    - WelfareGuide 에이전트 ID 사용 (CareGuide_v2 아님)
    - 복지 쿼리를 위한 process() 메서드 구현
    - session_id별 세션 관리 처리
    - 복지 프로그램이 포함된 구조화된 응답 반환
```

**따를 패턴**: `ResearchPaperAgent`에서 복사하되:
- 일반 `_agent_id` 대신 `_welfare_agent_id` 사용
- 더 단순한 응답 파싱 (preamble 처리 불필요)
- 복지 프로그램 포맷팅에 집중

---

### 3. 프론트엔드 라우팅을 위한 Agent Manager 업데이트 (예상: 1시간)

**파일**: `backend/Agent/agent_manager.py`

**변경 사항**:
- `MedicalWelfareAgent`를 새 에이전트 타입으로 등록
- 라우팅 로직 추가: 복지 관련 쿼리 확인
- 프론트엔드가 요청에서 agent_type 지정 가능
- 동일 세션 내 에이전트 전환 지원

**라우팅 전략**:
```python
if agent_type == "medical_welfare" or is_welfare_query(query):
    agent = MedicalWelfareAgent()
else:
    agent = ResearchPaperAgent()
```

---

### 4. 복지 프롬프트 및 가이드라인 생성 (예상: 1-2시간)

**파일**: `backend/Agent/medical_welfare/prompts.py`

**내용**:
- 복지 에이전트를 위한 시스템 프롬프트
- 사용자 프로필별 프롬프트 (researcher, patient, general)
- 응답 포맷팅 템플릿
- 정부 프로그램에 대한 면책 조항 텍스트

**Parlant 가이드라인** (healthcare_v2_en.py 내):
- 복지 전용 가이드라인 (의료 질문 차단)
- 공감 및 지원 가이드라인
- 신청 안내 가이드라인
- 정부 출처 인용 가이드라인

---

### 5. API 엔드포인트 업데이트 (예상: 1시간)

**파일**: `backend/app/api/welfare.py`

**변경 사항**:
- POST `/api/welfare/chat` 엔드포인트 추가
- 수신: query, session_id, profile, language
- MedicalWelfareAgent로 라우팅
- 반환: 복지 프로그램, 답변, 메타데이터

**응답 형식**:
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

### 6. 프론트엔드 통합 포인트 (예상: 정보 제공만)

**프론트엔드 팀을 위한 사항**:
- 에이전트 선택 컴포넌트 추가 (Research vs Welfare 탭/버튼)
- 채팅 요청에 `agent_type` 파라미터 설정
- 복지 프로그램을 구조화된 카드 형식으로 표시
- 신청 단계 및 연락처 정보 눈에 띄게 표시

---

### 7. 평가 데이터셋으로 테스트 (예상: 2-3시간)

**테스트 케이스**:
- CSV의 18개 복지 질문 실행 (CKD_General_025-030, CKD_Patient_026-030, CKD_Researcher_026-030)
- 3가지 사용자 프로필 모두 테스트 (researcher, patient, general)
- 올바른 프로그램 검색 확인
- 응답 품질 및 정확도 확인
- 응답 시간 측정

**성공 기준**:
- 18개 질문 모두 관련 프로그램 반환
- 답변이 expected_answer 컨텍스트와 일치
- 응답 시간 < 10초
- 오류나 크래시 없음

---

## 파일 변경 요약

### 신규/수정 파일:
1. ✅ `backend/Agent/medical_welfare/agent.py` - 전체 구현
2. ✅ `backend/Agent/medical_welfare/prompts.py` - 복지 프롬프트 생성
3. ✅ `backend/Agent/medical_welfare/__init__.py` - MedicalWelfareAgent 내보내기
4. ✅ `backend/Agent/research_paper/server/healthcare_v2_en.py` - WelfareGuide 에이전트 추가
5. ✅ `backend/Agent/agent_manager.py` - 복지 에이전트 등록
6. ✅ `backend/app/api/welfare.py` - 채팅 엔드포인트 추가

### 기존 파일 (변경 불필요):
- `backend/app/db/welfare_manager.py` - 이미 WelfareManager 있음
- `backend/app/models/welfare.py` - 이미 데이터 모델 있음
- `data/welfare/welfare_programs_2025_verified.json` - 이미 13개 프로그램 있음

---

## 아키텍처 다이어그램

```
프론트엔드 컴포넌트 선택
    ↓
[Research 버튼] 또는 [Welfare 버튼]
    ↓
Agent Manager (agent_manager.py)
    ↓
    ├── ResearchPaperAgent → Parlant Server (port 8800) → CareGuide_v2 Agent
    │                                                         ↓
    │                                                    search_medical_qa 도구
    │                                                         ↓
    │                                                    5개 데이터 소스
    │
    └── MedicalWelfareAgent → Parlant Server (port 8800) → WelfareGuide Agent
                                                              ↓
                                                         search_welfare_programs 도구
                                                              ↓
                                                         MongoDB welfare_programs
```

---

## 주요 기술 결정 사항

1. **서버 공유**: 두 에이전트 모두 동일한 Parlant 서버 프로세스 사용 (효율적, 배포 간단)
2. **저니 없음**: WelfareGuide는 단순 Q&A 패턴 사용 (다단계 저니 오케스트레이션 없음)
3. **MongoDB만 사용**: 기존 13개 프로그램 사용 (나중에 확장 가능)
4. **프로필 지원**: 3가지 프로필 모두 지원 (연구자는 상세 인용, 일반인은 간소화)
5. **프론트엔드 라우팅**: 프론트엔드가 사용할 에이전트 제어 (명시적 사용자 선택)

---

## 타임라인 예상

- **1일차 (4-5시간)**:
  - healthcare_v2_en.py에 WelfareGuide 에이전트 생성
  - MedicalWelfareAgent 클래스 구현

- **2일차 (3-4시간)**:
  - 프롬프트 및 가이드라인 생성
  - agent_manager.py 업데이트
  - 복지 채팅 API 엔드포인트 생성

- **3일차 (2-3시간)**:
  - 18개 평가 질문으로 테스트
  - 버그 수정 및 개선
  - 문서화

**총**: 9-12시간의 개발 작업

---

## 성공 지표

1. ✅ MedicalWelfareAgent가 Parlant 서버에 성공적으로 연결
2. ✅ 18개 복지 질문 모두 관련 프로그램 반환
3. ✅ 응답 품질이 expected_answer와 일치하거나 초과
4. ✅ 쿼리당 응답 시간 < 10초
5. ✅ 3가지 사용자 프로필 모두 정상 작동
6. ✅ 프론트엔드가 Research와 Welfare 에이전트 간 전환 가능
7. ✅ 테스트 중 오류나 크래시 없음

---

## 향후 개선 사항 (MVP 이후)

1. **데이터 확장**: 20-30개 추가 복지 프로그램 추가
2. **시맨틱 검색**: 더 나은 매칭을 위해 Pinecone 벡터 검색 추가
3. **지역별 프로그램**: 시/도별 특화 프로그램 추가
4. **문서 생성**: 신청 체크리스트 자동 생성
5. **다국어 지원**: 영어 응답 지원
6. **평가 파이프라인**: BLEU/유사도 점수로 자동화된 테스트

---

## 평가 데이터셋 상세

### 총 복지 질문: 18개

**일반인/노비스 (General/Novice)** - 6개 질문:
- CKD_General_025: 투석 환자 복지 혜택
- CKD_General_026: 신장 장애인 등록 기준과 절차
- CKD_General_027: 장애 등록 시 혜택
- CKD_General_028: 정부 지원 신청 서류
- CKD_General_029: 이식 후 장애 혜택
- CKD_General_030: 가족 대리 신청

**질환자/경험자 (Patient/Experienced)** - 6개 질문:
- CKD_Patient_026: 산정특례 제도
- CKD_Patient_027: 복지카드 할인 혜택
- CKD_Patient_028: 지자체별 추가 지원
- CKD_Patient_029: 투석 환자 이동 지원
- CKD_Patient_030: 희귀질환 추가 지원

**연구자/전문가 (Researcher/Expert)** - 6개 질문:
- CKD_Researcher_026: 정부/질병청 계획
- CKD_Researcher_027: KONOS 신장이식 배분 원칙
- CKD_Researcher_028: 복막투석 재택관리 시범사업
- CKD_Researcher_029: 식약처 CKD 식단 가이드
- CKD_Researcher_030: 재생의료 R&D 정부 지원

### 다루는 주제:
1. 산정특례 (본인부담금 경감)
2. 장애등록 (장애인 등록 절차)
3. 복지혜택 (각종 복지 프로그램)
4. 정부지원 (재정 및 비재정 지원)
5. KONOS (장기이식 배분 시스템)
6. 식약처 가이드 (식단 및 식품 가이드라인)
7. 재생의료 R&D (재생의료 연구 지원금)
