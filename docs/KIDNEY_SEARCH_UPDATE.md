# Kidney 데이터 검색 시스템 업데이트

## 📋 변경 사항 요약

CareGuide 검색 시스템을 **일반 의료 데이터**에서 **신장(Kidney) 전용 데이터**로 전환했습니다.

---

## 🔄 주요 변경 사항

### 1. MongoDB Collections 변경

**이전 (Before):**
- `qa_data` - 일반 QA 데이터
- `papers` - 일반 논문 데이터
- `medical_data` - 일반 의료 데이터

**이후 (After):**
- `qa_kidney` - 신장 관련 QA 데이터 (3,993개)
- `papers_kidney` - 신장 관련 논문 데이터 (1,597개)
- `medical_kidney` - 신장 관련 의료 데이터 (7,512개)

### 2. Pinecone Vector Index 변경

**이전 (Before):**
- Index: `medical-embeddings`
- Namespaces: `qa`, `papers`, `medical`

**이후 (After):**
- Index: `kidney-medical-embeddings`
- Namespaces: `qa_kidney`, `papers_kidney`, `medical_kidney`

### 3. 수정된 파일 목록

#### [parlant/database/mongodb_manager.py](parlant/database/mongodb_manager.py)
- 모든 컬렉션 이름을 kidney 버전으로 변경
- 인덱스 생성 로직 업데이트
- DOI 필드 경로 수정 (`metadata.doi` → `doi`)
- 검색 메서드 모두 kidney 컬렉션 사용

#### [parlant/database/vector_manager.py](parlant/database/vector_manager.py)
- 기본 인덱스 이름을 `kidney-medical-embeddings`로 변경
- 생성자 기본값 업데이트

#### [parlant/search/hybrid_search.py](parlant/search/hybrid_search.py)
- QA 검색 namespace: `qa` → `qa_kidney`
- 논문 검색 namespace: `papers` → `papers_kidney`
- 의료 검색 namespace: `medical` → `medical_kidney`

#### [parlant/healthcare_v2_en.py](parlant/healthcare_v2_en.py)
- **수정 불필요** ✅
- `HybridSearchEngine`을 사용하므로 자동으로 kidney 데이터 검색

#### [client/app.py](client/app.py)
- **수정 불필요** ✅
- `healthcare_v2_en.py`의 tool을 호출하므로 자동 반영

---

## 🗄️ 데이터 현황

### MongoDB Collections (Local)
```
qa_kidney        : 3,993개  (중복 제거된 unique 질문)
papers_kidney    : 1,597개  (DOI 기반 unique 논문)
medical_kidney   : 7,512개  (의료 특허/데이터)
────────────────────────────
총합             : 13,102개
```

### Pinecone Index (kidney-medical-embeddings)
```
Namespace        Vector Count   Status
─────────────────────────────────────────
qa_kidney        3,993개        ✅ 완료
papers_kidney    1,597개        ✅ 완료
medical_kidney   7,512개        ✅ 완료
─────────────────────────────────────────
총합             13,102개
```

---

## 🚀 배포 시 체크리스트

### 1. 환경 변수 확인
```bash
# .env 파일 확인
MONGODB_URI=mongodb://localhost:27017
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text-v2-moe
PUBMED_EMAIL=<your-email>
```

### 2. MongoDB 인덱스 생성 확인
```bash
# MongoDB 쉘에서 확인
use careguide

# Text 검색 인덱스 확인
db.qa_kidney.getIndexes()
db.papers_kidney.getIndexes()
db.medical_kidney.getIndexes()

# 예상 인덱스:
# - qa_kidney_text_search (question, answer)
# - paper_kidney_text_search (title, abstract)
# - doi_kidney_unique (doi - unique)
# - medical_kidney_text_search (text, keyword)
```

### 3. Pinecone 인덱스 확인
```python
from pinecone import Pinecone
import os

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("kidney-medical-embeddings")

# Namespace별 벡터 수 확인
for ns in ["qa_kidney", "papers_kidney", "medical_kidney"]:
    stats = index.describe_index_stats()
    print(f"{ns}: {stats['namespaces'][ns]['vector_count']} vectors")
```

### 4. 검색 테스트
```bash
# HybridSearchEngine 테스트
cd parlant/search
python hybrid_search.py

# MongoDB Manager 테스트
cd parlant/database
python mongodb_manager.py
```

### 5. 서버 재시작
```bash
# CareGuide 서버 재시작
python parlant/healthcare_v2_en.py

# Flask 클라이언트 재시작
python client/app.py
```

---

## 🔍 검색 동작 방식

### Hybrid Search 알고리즘
1. **Keyword Search** (MongoDB Text Search) - 40% 가중치
   - Full-text indexing을 통한 빠른 키워드 매칭

2. **Semantic Search** (Pinecone Vector) - 60% 가중치
   - Sentence-Transformers (all-MiniLM-L6-v2) 임베딩
   - Cosine similarity 기반 의미론적 유사도

3. **Result Merging**
   - ID 기반 중복 제거
   - 가중 점수 조합: `final_score = keyword_score * 0.4 + semantic_score * 0.6`
   - 상위 N개 반환

---

## 📊 성능 영향 분석

### 데이터 크기 비교
- **이전**: 2,224,451개 → **이후**: 13,102개 (99.4% 감소)
- **검색 속도**: 대폭 향상 예상
- **정확도**: Kidney 전용 데이터로 더욱 정확한 결과

### 메모리 사용량
- MongoDB: 큰 변화 없음 (인덱스는 효율적으로 관리됨)
- Pinecone: 13,102 vectors × 384 dimensions = ~5MB (매우 경량)

---

## 🐛 문제 해결

### 1. "Index not found" 에러
```bash
# Pinecone 인덱스 재생성
python preprocess/setup_kidney_database.py --skip-mongodb
```

### 2. MongoDB 검색 결과 없음
```bash
# Text 인덱스 재생성
mongo careguide --eval "
  db.qa_kidney.dropIndexes();
  db.papers_kidney.dropIndexes();
  db.medical_kidney.dropIndexes();
"

# 서버 재시작 (자동으로 인덱스 재생성됨)
python parlant/healthcare_v2_en.py
```

### 3. Pinecone 검색 결과 없음
```bash
# 임베딩 재생성
python preprocess/embed_kidney_data.py
```

---

## 🔐 보안 고려사항

1. **API Key 보호**
   - `.env` 파일은 절대 Git에 커밋하지 않음
   - `.gitignore`에 `.env` 포함 확인

2. **MongoDB 접근 제어**
   - Production에서는 인증 활성화
   - Read-only 사용자 생성 권장

3. **Pinecone API 사용량**
   - Free tier: 100K requests/month
   - 사용량 모니터링 필요

---

## 📚 추가 참고 자료

- [Pinecone Documentation](https://docs.pinecone.io/)
- [MongoDB Text Search](https://docs.mongodb.com/manual/text-search/)
- [Sentence Transformers](https://www.sbert.net/)
- [PubMed API](https://www.ncbi.nlm.nih.gov/books/NBK25500/)

---

## ✅ 업데이트 완료 확인

- [x] MongoDB collections 변경 완료
- [x] Pinecone index 변경 완료
- [x] HybridSearchEngine namespace 변경 완료
- [x] healthcare_v2_en.py 호환성 확인
- [x] client/app.py 호환성 확인
- [x] 데이터 로딩 완료 (13,102개)
- [x] 임베딩 생성 완료 (13,102개)
- [x] 테스트 스크립트 검증

---

**작업 완료 시각**: 2025-11-11
**담당자**: AI Assistant
**버전**: v2.0 (Kidney Specialized)
