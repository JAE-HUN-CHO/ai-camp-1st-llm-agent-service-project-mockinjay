# 신장(Kidney) 데이터 적재 가이드

## 📋 개요

필터링된 신장 관련 데이터를 MongoDB와 Pinecone에 적재하는 스크립트 모음입니다.

### 데이터 규모
- **Papers (논문)**: 1,659개 (4.4 MB)
- **Medical (의료 문서)**: 7,512개 (168 MB)
- **QA (질문-답변)**: 112,322개 (158 MB)
- **총 문서 수**: 121,493개

---

## 🚀 빠른 시작

### 1. 환경 변수 설정

`.env` 파일에 다음 변수가 설정되어 있는지 확인하세요:

```bash
MONGODB_URI=mongodb://localhost:27017
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text-v2-moe
```

### 2. MongoDB 실행 (로컬 사용 시)

```bash
# MongoDB가 설치되어 있다면
mongod --dbpath /path/to/your/db

# 또는 Docker 사용
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### 3. 전체 프로세스 실행

```bash
cd preprocess
source ../.venv/bin/activate
python3 setup_kidney_database.py
```

**예상 소요 시간:**
- MongoDB 적재: 2-3분
- Pinecone 임베딩: 15-20분
- **총 소요 시간: ~20-25분**

---

## 📚 스크립트 설명

### `setup_kidney_database.py` (통합 실행)

MongoDB와 Pinecone 적재를 순차적으로 실행하는 메인 스크립트입니다.

**사용법:**
```bash
# 전체 프로세스 실행
python3 setup_kidney_database.py

# MongoDB만 실행
python3 setup_kidney_database.py --skip-pinecone

# Pinecone만 실행
python3 setup_kidney_database.py --skip-mongodb

# 검증만 수행
python3 setup_kidney_database.py --verify-only
```

### `load_kidney_data.py` (MongoDB 전용)

필터링된 JSONL 파일을 MongoDB에 적재합니다.

**적재 대상:**
- `papers_kidney.jsonl` → `careguide.papers_kidney`
- `medical_kidney.jsonl` → `careguide.medical_kidney`
- `qa_kidney.jsonl` → `careguide.qa_kidney`

**사용법:**
```bash
python3 load_kidney_data.py
```

### `embed_kidney_data.py` (Pinecone 전용)

MongoDB 컬렉션에서 데이터를 읽어 Pinecone에 벡터 임베딩을 생성/업로드합니다.

**Pinecone 설정:**
- **인덱스 이름**: `kidney-medical-embeddings`
- **차원**: 384 (sentence-transformers/all-MiniLM-L6-v2)
- **메트릭**: cosine
- **네임스페이스**: `papers_kidney`, `medical_kidney`, `qa_kidney`

**사용법:**
```bash
python3 embed_kidney_data.py
```

---

## 🗄️ 데이터베이스 구조

### MongoDB 컬렉션

#### `papers_kidney`
```json
{
  "_id": "ObjectId",
  "title": "Paper title",
  "abstract": "Paper abstract",
  "source": "pubmed",
  "metadata": {
    "doi": "10.1234/example",
    "journal": "Journal Name",
    "authors": ["Author 1", "Author 2"],
    "publication_date": "2023-01-01",
    "keywords": ["kidney", "disease"]
  },
  "_filtering_info": {
    "filter_date": "2025-11-11",
    "filter_keywords": ["kidney", "renal"]
  }
}
```

#### `medical_kidney`
```json
{
  "_id": "ObjectId",
  "id": "unique_id",
  "text": "Medical content",
  "keyword": "keyword",
  "category": "category_name",
  "source_dataset": "dataset_name",
  "source_file": "filename.jsonl",
  "_filtering_info": {...}
}
```

#### `qa_kidney`
```json
{
  "_id": "ObjectId",
  "id": "unique_id",
  "question": "Question text",
  "answer": "Answer text",
  "source_dataset": "dataset_name",
  "category": "category_name",
  "metadata": {...},
  "_filtering_info": {...}
}
```

### Pinecone 인덱스

**인덱스**: `kidney-medical-embeddings`

**네임스페이스별 벡터:**
- `papers_kidney`: 논문 임베딩 (title + abstract)
- `medical_kidney`: 의료 문서 임베딩 (text)
- `qa_kidney`: QA 임베딩 (question + answer)

---

## ✅ 검증

### MongoDB 검증

```bash
# MongoDB 쉘 접속
mongosh

# 데이터베이스 선택
use careguide

# 문서 수 확인
db.papers_kidney.countDocuments()
db.medical_kidney.countDocuments()
db.qa_kidney.countDocuments()

# 샘플 문서 확인
db.papers_kidney.findOne()
```

### Pinecone 검증

스크립트 실행 시 자동으로 통계가 출력됩니다:
```bash
python3 setup_kidney_database.py --verify-only
```

또는 Python에서 직접 확인:
```python
from parlant.database.vector_manager import VectorDBManager
import asyncio

async def check_pinecone():
    manager = VectorDBManager(
        api_key="your_key",
        index_name="kidney-medical-embeddings"
    )
    stats = await manager.get_index_stats()
    print(stats)

asyncio.run(check_pinecone())
```

---

## 🔍 검색 테스트

### 하이브리드 검색 (MongoDB + Pinecone)

```python
from parlant.search.hybrid_search import HybridSearchEngine
import asyncio

async def test_search():
    engine = HybridSearchEngine(
        mongodb_uri="mongodb://localhost:27017",
        pinecone_api_key="your_key",
        pinecone_index="kidney-medical-embeddings",
        db_name="careguide"
    )

    # 신장 질환 검색
    results = await engine.search(
        query="chronic kidney disease treatment",
        collections=["papers_kidney", "medical_kidney", "qa_kidney"],
        top_k=5
    )

    for result in results:
        print(f"Score: {result['score']:.4f}")
        print(f"Title: {result.get('title', result.get('text', '')[:100])}")
        print()

asyncio.run(test_search())
```

---

## 🛠️ 트러블슈팅

### MongoDB 연결 실패

```bash
# MongoDB가 실행 중인지 확인
ps aux | grep mongod

# 포트 확인
lsof -i :27017

# .env 파일 확인
cat ../.env | grep MONGODB_URI
```

### Pinecone API 키 오류

```bash
# API 키 확인
cat ../.env | grep PINECONE_API_KEY

# Pinecone 대시보드에서 키 확인
# https://app.pinecone.io/
```

### 메모리 부족 오류

임베딩 생성 시 메모리 부족이 발생하면 `embed_kidney_data.py`의 `batch_size`를 줄여보세요:

```python
# 기본값: 100
batch_size = 50  # 또는 25
```

### 중복 데이터

스크립트는 자동으로 중복을 처리합니다:
- **Papers**: DOI 기반 중복 제거
- **Medical/QA**: 해시 기반 중복 제거

재실행 시 기존 데이터는 유지되고 새 데이터만 추가됩니다.

---

## 📊 성능 최적화

### MongoDB 인덱스 생성

적재 후 검색 성능 향상을 위해 인덱스를 생성할 수 있습니다:

```javascript
// MongoDB 쉘에서 실행
use careguide

// 텍스트 검색 인덱스 (이미 자동 생성됨)
db.papers_kidney.createIndex({ title: "text", abstract: "text" })
db.medical_kidney.createIndex({ text: "text" })
db.qa_kidney.createIndex({ question: "text", answer: "text" })

// 키워드 검색 인덱스
db.medical_kidney.createIndex({ keyword: 1 })
db.qa_kidney.createIndex({ category: 1 })
```

### Pinecone 최적화

- **Pod Type**: p1 (기본) 또는 s1 (더 빠름, 더 비쌈)
- **Replicas**: 1개 (기본) 또는 더 많이 (고가용성)
- **Metric**: cosine (기본) - 의료 도메인에 적합

---

## 🔗 관련 파일

- 필터링 스크립트:
  - [`filter_papers_kidney.py`](filter_papers_kidney.py)
  - [`filter_medical_kidney.py`](filter_medical_kidney.py)
  - [`filter_qa_kidney.py`](filter_qa_kidney.py)

- 데이터 파일:
  - [`data/preprocess/kidney_filtered/papers_kidney.jsonl`](../data/preprocess/kidney_filtered/papers_kidney.jsonl)
  - [`data/preprocess/kidney_filtered/medical_kidney.jsonl`](../data/preprocess/kidney_filtered/medical_kidney.jsonl)
  - [`data/preprocess/kidney_filtered/qa_kidney.jsonl`](../data/preprocess/kidney_filtered/qa_kidney.jsonl)

- 데이터베이스 매니저:
  - [`parlant/database/mongodb_manager.py`](../parlant/database/mongodb_manager.py)
  - [`parlant/database/vector_manager.py`](../parlant/database/vector_manager.py)

- 검색 엔진:
  - [`parlant/search/hybrid_search.py`](../parlant/search/hybrid_search.py)

---

## 📝 다음 단계

데이터 적재가 완료되면:

1. **하이브리드 검색 테스트**
   ```bash
   python -m parlant.search.hybrid_search
   ```

2. **CareGuide 챗봇 실행**
   ```bash
   cd client
   python app.py
   ```

3. **Parlant 에이전트 설정**
   - 신장 질환 특화 가이드라인 적용
   - 커스텀 프롬프트 설정

---

## 💡 참고사항

- MongoDB와 Pinecone 모두 기존 데이터를 유지하면서 새 데이터를 추가합니다
- 재실행해도 안전하며, 중복은 자동으로 처리됩니다
- 스크립트는 진행 상황을 실시간으로 출력합니다
- 오류 발생 시 상세한 에러 메시지가 출력됩니다

---

**생성 일자**: 2025-11-11
**버전**: 1.0.0
**작성자**: Claude Code
