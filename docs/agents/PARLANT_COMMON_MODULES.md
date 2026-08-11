# Parlant Common Tools - Phase 2 완료! 🎉

## ✅ 생성된 공통 모듈

### 1. **emergency_tools.py**

응급 상황 감지 도구

```python
@p.tool
async def check_emergency_keywords(context, text):
    # 응급 키워드 감지
    # chest pain, breathing difficulty, severe bleeding 등
    # → 911/119 안내 반환
```

**감지 카테고리**:

- 흉통 (chest pain)
- 호흡곤란 (breathing difficulty)
- 심한 출혈 (severe bleeding)
- 의식 소실 (unconscious)
- 경련 (seizure)
- 뇌졸중 (stroke)
- 극심한 두통 (severe headache)
- 알레르기 반응 (allergic reaction)

### 2. **kidney_tools.py**

CKD 관련 정보 도구

#### `get_kidney_stage_info()`

- **GFR 값** 또는 **CKD 단계**로 조회
- 단계별 상세 정보:
  - 설명, 증상, 관리 방법
  - 식이 요법, 모니터링 주기

```python
@p.tool
async def get_kidney_stage_info(context, gfr=None, stage=None):
    # Stage 1-5 정보 제공
    # 예: gfr=45 → Stage 3 정보 자동 판단
```

#### `get_symptom_info()`

- 신장 질환 관련 증상 정보
- 증상별 원인, 관리 방법, 의사 상담 시점

```python
@p.tool
async def get_symptom_info(context, symptoms):
    # "fatigue, edema" → 각 증상 정보 반환
    # 응급 증상 자동 감지
```

### 3. **utils.py**

공통 유틸리티 함수

```python
def get_profile(context: ToolContext) -> str:
    # researcher / patient / general 판단

def convert_objectid_to_str(data):
    # MongoDB ObjectId → string 변환 (재귀적)

def get_default_profile() -> str:
    # 환경 변수에서 기본 프로필 읽기
```

---

## 📁 폴더 구조

```
backend/Agent/parlant_common/
├── __init__.py           # 패키지 초기화
├── emergency_tools.py    # 응급 상황 감지
├── kidney_tools.py       # CKD 정보 도구
└── utils.py              # 공통 유틸리티
```

---

## 🔧 사용 방법

### Research Paper Server에서 사용

```python
# backend/Agent/research_paper/server/research_server.py
from ...parlant_common import (
    check_emergency_keywords,
    get_kidney_stage_info,
    get_symptom_info,
    get_profile
)

# Parlant 서버에 도구 등록
@p.tool
async def check_emergency(context: ToolContext, text: str):
    return await check_emergency_keywords(context, text)

@p.tool
async def get_ckd_stage_info(context: ToolContext, gfr: float = None, stage: int = None):
    return await get_kidney_stage_info(context, gfr, stage)
```

### Medical Welfare Server에서 사용

```python
# backend/Agent/medical_welfare/server/welfare_server.py
from ...parlant_common import (
    check_emergency_keywords,
    get_symptom_info,
    convert_objectid_to_str
)

# 동일한 도구를 재사용
@p.tool
async def check_emergency(context: ToolContext, text: str):
    return await check_emergency_keywords(context, text)
```

---

## 🎯 장점

### 1. **코드 재사용**

- 공통 로직을 한 곳에서 관리
- 중복 제거

### 2. **일관성**

- 모든 Parlant 서버가 동일한 로직 사용
- 응급 상황 대응 통일

### 3. **유지보수성**

- 한 곳만 수정하면 모든 서버에 반영
- 버그 수정 효율적

### 4. **확장성**

- 새 공통 도구 추가 용이
- 새 Parlant 서버 생성 시 즉시 사용 가능

---

## 📊 다음 단계

- ✅ **Phase 2: 공통 모듈 추출** ⬅️ 방금 완료!
- ⬜ **Phase 3: Research Paper 서버 분리**
- ⬜ **Phase 4: Medical Welfare 서버 생성**
- ⬜ **Phase 5: RemoteAgent 어댑터 업데이트**

계속 진행하시겠습니까?
