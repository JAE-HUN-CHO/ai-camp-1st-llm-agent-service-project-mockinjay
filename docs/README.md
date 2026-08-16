# CareGuide

> 만성콩팥병(CKD) 환자를 위한 종합 케어 플랫폼

현재 구현과 문서가 충돌하면 [`agents/DOCUMENT_CONSISTENCY_MATRIX.md`](agents/DOCUMENT_CONSISTENCY_MATRIX.md)의
normative 문서와 Accepted ADR을 우선한다. 과거 설계·리포트는 삭제하지 않고 historical
참고자료로 보존한다.

## 프로젝트 개요

CareGuide는 만성콩팥병 환자에게 AI 챗봇 기반 의료정보, 영양 관리, 커뮤니티 기능을 제공하는 웹 플랫폼입니다.

## 기술 스택

### Backend
- Python 3.10+
- FastAPI
- MongoDB
- Ollama (`qwen3.6:27b-mlx`) with local MongoDB Atlas Local vector search

### Frontend
- React 19
- TypeScript
- Tailwind CSS
- Vite

## 프로젝트 구조

```
.
├── backend/          # Python 백엔드
│   ├── app/
│   │   ├── main.py
│   │   ├── api/      # API 라우터
│   │   ├── models/   # 데이터 모델
│   │   ├── services/ # 비즈니스 로직
│   │   └── db/       # DB 연결
│   └── requirements.txt
├── frontend/         # React 프론트엔드
│   ├── src/
│   └── package.json
└── data/            # 데이터 파일
```

## 실행 방법

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## 팀 구성

- **Yj**: Nutri Coach (영양 관리)
- **ch**: Community (커뮤니티)
- **jh**: Knowledge Search, Trends (지식 검색, 대시보드)
- **jk**: Sign up, My Page (회원가입, 마이페이지)

## 문서

- 현재 아키텍처 읽기 순서:
  [기준선](./agents/DOCUMENT_CONSISTENCY_MATRIX.md) →
  [도메인](./agents/domain.md)과 [Accepted ADR](./adr/README.md) →
  [현재 상태](./agents/ARCHITECTURE_CURRENT_STATE.md) →
  [갭 분석](./agents/ARCHITECTURE_GAP_ANALYSIS.md) →
  [소프트웨어 공학 근거 정렬](./agents/ARCHITECTURE_REFERENCE_ALIGNMENT.md) →
  [Accepted ADR-013](./adr/ADR-013-feature-first-hexagonal-modular-monolith.md)과
  [목표 설계](./agents/ARCHITECTURE_REFACTORING_DESIGN.md) →
  [실행 계획](./agents/ARCHITECTURE_REFACTORING_PLAN.md) →
  [실행 프롬프트](./agents/ARCHITECTURE_REFACTORING_EXECUTION_PROMPT.md) →
  [10개 관점 재검증](./agents/ARCHITECTURE_MULTI_AGENT_REVIEW.md)
- [기술 명세](./project-plans/tech-spec.md)
- [통합 가이드](./integration-guide.md)
- 개별 개발 계획: [jk](./project-plans/jk-plan.md), [jh](./project-plans/jh-plan.md), [Yj](./project-plans/Yj-plan.md), [ch](./project-plans/ch-plan.md)
