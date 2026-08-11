# Medical Welfare Parlant Server - Phase 4 완료! 🎉

## ✅ 생성된 파일

### 1. **medical_welfare_server.py**

Medical Welfare Agent 전용 독립 Parlant 서버

**도구**:

- ✅ `search_welfare_programs()`: 복지 프로그램 검색
  - 카테고리 필터 (medical_support, social_welfare, etc.)
  - 질병 필터
  - CKD 단계별 필터
- ✅ `search_hospitals()`: 병원/약국/투석센터 검색
  - 병원 유형 (hospital, pharmacy, dialysis_center)
  - 지역 필터
  - 투석 가능 여부
  - 위치 기반 검색 (lat/long)
- ✅ `check_emergency()`: 응급 상황 감지 (공통 도구)
- ✅ `get_ckd_stage_info()`: CKD 단계 정보 (공통 도구)
- ✅ `get_symptoms_info()`: 증상 정보 (공통 도구)

### 2. **medical_welfare_guidelines.py**

Guidelines 및 Journey 정의

---

## 🔧 주요 특징

### 1. **독립성**

```python
# Port 8801에서 독립 실행
p.run_server(host="127.0.0.1", port=8801)
```

### 2. **Welfare & Hospital 전용**

```python
# WelfareManager 사용
await WELFARE_MANAGER.search_programs(
    query=query,
    category=category,
    disease=disease,
    ckd_stage=ckd_stage
)

# HospitalManager 사용
await HOSPITAL_MANAGER.search_hospitals(
    query=query,
    hospital_type=hospital_type,
    region=region,
    has_dialysis=has_dialysis
)
```

### 3. **공통 도구 재사용**

```python
from Agent.parlant_common import (
    check_emergency_keywords,
    get_kidney_stage_info,
    get_symptom_info
)
```

### 4. **Profile 지원**

- researcher: 최대 10개 결과
- patient: 최대 5개 결과
- general: 최대 3개 결과

---

## 📁 폴더 구조

```
backend/Agent/
├── parlant_common/                    # 공통 도구
│   ├── emergency_tools.py
│   ├── kidney_tools.py
│   └── utils.py
│
├── research_paper/
│   └── server/
│       ├── research_paper_server.py   # Port 8800
│       └── research_paper_guidelines.py
│
└── medical_welfare/
    └── server/
        ├── medical_welfare_server.py   # Port 8801 ✨
        └── medical_welfare_guidelines.py ✨
```

---

## 🚀 실행 방법

### Medical Welfare 서버

```bash
cd backend/Agent/medical_welfare/server
python medical_welfare_server.py
```

### 두 서버 동시 실행

```bash
# Terminal 1: Research Paper
cd backend/Agent/research_paper/server
python research_paper_server.py  # Port 8800

# Terminal 2: Medical Welfare
cd backend/Agent/medical_welfare/server
python medical_welfare_server.py  # Port 8801
```

---

## 🎯 검색 예제

### 복지 프로그램 검색

```python
await search_welfare_programs(
    query="투석 지원",
    category="dialysis_support",
    ckd_stage=5
)
```

**응답**:

```json
{
  "programs": [
    {
      "name": "만성신부전 투석환자 의료비 지원",
      "category": "dialysis_support",
      "eligibility": "혈액투석 또는 복막투석 환자",
      "benefits": "월 최대 30만원 지원",
      "application": "주민센터 방문 신청"
    }
  ]
}
```

### 병원 검색

```python
await search_hospitals(
    query="야간 투석 가능한 병원",
    region="서울",
    has_dialysis=True,
    night_dialysis=True
)
```

**응답**:

```json
{
  "hospitals": [
    {
      "name": "서울대학교병원",
      "type": "hospital",
      "has_dialysis": true,
      "night_dialysis": true,
      "phone": "02-2072-2114"
    }
  ]
}
```

---

## 🌟 장점

### 1. **완전 독립**

- Research Paper 서버와 분리
- 각자 독립적으로 스케일링 가능

### 2. **전문화**

- Welfare/Hospital 검색에 최적화
- 불필요한 도구 제거 (PubMed, Papers)

### 3. **공통 도구 공유**

- Emergency 감지
- CKD 정보
- 증상 정보

### 4. **유지보수성**

- Medical Welfare 관련 코드만 관리
- 명확한 책임 분리

---

## 📊 서버 비교

| 서버                | Port | 도구                                                 | 용도               |
| ------------------- | ---- | ---------------------------------------------------- | ------------------ |
| **Research Paper**  | 8800 | search_medical_qa, CKD info, symptoms                | 논문/연구 검색     |
| **Medical Welfare** | 8801 | search_welfare, search_hospitals, CKD info, symptoms | 복지/병원 검색     |
| **공통 도구**       | -    | emergency, CKD info, symptoms                        | 모든 서버에서 공유 |

---

## 📊 다음 단계

- ✅ Phase 2: 공통 모듈 추출
- ✅ Phase 3: Research Paper 서버 분리
- ✅ Phase 4: Medical Welfare 서버 생성 ⬅️ 방금 완료!
- ⬜ Phase 5: RemoteAgent 어댑터 업데이트
- ⬜ Phase 7: Router 시스템

계속 진행하시겠습니까? (RemoteAgent 어댑터 업데이트)
