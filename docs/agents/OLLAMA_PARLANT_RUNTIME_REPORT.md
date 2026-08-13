# Ollama-only Parlant 런타임 보고서

**업데이트:** 2026-08-13

## 현재 계약

- Parlant 연구 서버: `RESEARCH_PORT` (기본 `8800`)
- Parlant 복지 서버: `WELFARE_PORT` (기본 `8801`)
- 생성: `OLLAMA_MODEL` (기본 `qwen3.6:27b-mlx`)
- 임베딩: `OLLAMA_EMBEDDING_MODEL` (기본 `nomic-embed-text-v2-moe`, 1536차원 필수)
- 대체 임베딩 모델도 MongoDB 벡터 저장 및 cosine 검색 호환을 위해 1536차원을 유지해야 합니다.
- Ollama endpoint: `http://localhost:11434`
- 세션·고객 저장소: Parlant local store
- 유료 API 키: 필요 없음

두 독립 Parlant 서버는 `parlant_nlp_adapter.py`의
`ParlantHealthcareNLPService`를 주입받습니다. 어댑터는 Parlant 3.3.x의
tracer와 optional hints 계약을 구현하고, 로컬 모델이 Markdown code fence나
후행 설명을 반환해도 첫 JSON 값을 추출해 schema 검증합니다. 스트리밍은
지원하지 않으며 호출 시 `NotImplementedError`를 명시적으로 반환합니다.

## 검증 결과

- `ruff` 변경 파일 검사: 통과
- adapter 회귀 테스트: JSON object/array, code fence, 후행 설명, 무응답,
  streaming 미지원 동작을 검증
- Parlant 초기화 중 `POST http://localhost:11434/api/chat` 실제 호출 확인
- 임베딩 모델 초기화 및 local store 생성 확인
- 전체 Parlant 인덱싱은 로컬 모델 성능에 따라 수 분 이상 걸릴 수 있으므로
  서버 HTTP smoke는 인덱싱 완료 후 별도로 실행해야 합니다.

## 실행

```bash
OLLAMA_MODEL=qwen3.6:27b-mlx \
OLLAMA_EMBEDDING_MODEL=nomic-embed-text-v2-moe \
.venv/bin/python backend/Agent/research_paper/server/healthcare_v2_en.py
```

복지 서버는 동일한 환경 변수에 `WELFARE_PORT=8801`을 추가해 실행합니다.
