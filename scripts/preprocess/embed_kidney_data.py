"""
Local Ollama/MongoDB 벡터 임베딩 스크립트 - 신장(Kidney) 관련 데이터

MongoDB 컬렉션에서 데이터를 읽어 로컬 Ollama 임베딩을 생성합니다.
- papers_kidney → kidney-medical-embeddings (namespace: papers_kidney)
- medical_kidney → kidney-medical-embeddings (namespace: medical_kidney)
- qa_kidney → kidney-medical-embeddings (namespace: qa_kidney)
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from parlant.database.mongodb_manager import MongoDBManager
from parlant.database.vector_manager import VectorDBManager
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


async def embed_kidney_data_to_local_vector():
    """신장 데이터의 Ollama 임베딩을 MongoDB vector adapter로 전달"""

    print("=" * 80)
    print("🔮 신장(Kidney) 데이터 Ollama 임베딩 시작")
    print("=" * 80)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    mongodb_uri = os.getenv(
        "MONGODB_URI",
        "mongodb://careguide:careguide_local@localhost:27017/?authSource=admin",
    )

    # Manager 초기화
    mongodb_manager = MongoDBManager(mongodb_uri, db_name="careguide")
    vector_manager = VectorDBManager(index_name="kidney-medical-embeddings")

    try:
        # MongoDB 연결
        print("🔌 MongoDB 연결 중...")
        await mongodb_manager.connect()
        print("✅ MongoDB 연결 성공\n")

        # MongoDB vector index setup is owned by the database adapter.
        print("🔮 MongoDB vector index 경로 확인 중...")
        print("   인덱스 이름: kidney-medical-embeddings")
        print(f"   임베딩 모델: {os.getenv('OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text-v2-moe')}")
        print("   메트릭: cosine")
        await vector_manager.create_index()
        print("✅ MongoDB vector adapter 경로 준비 완료\n")

        # 적재할 컬렉션 정의
        collections_to_embed = [
            {
                "collection": "papers_kidney",
                "namespace": "papers_kidney",
                "description": "연구 논문",
                "text_fields": ["title", "abstract"],
                "metadata_fields": ["source", "metadata"]
            },
            {
                "collection": "medical_kidney",
                "namespace": "medical_kidney",
                "description": "의료 문서",
                "text_fields": ["text"],
                "metadata_fields": ["keyword", "category", "source_dataset"]
            },
            {
                "collection": "qa_kidney",
                "namespace": "qa_kidney",
                "description": "QA 데이터",
                "text_fields": ["question", "answer"],
                "metadata_fields": ["source_dataset", "category"]
            }
        ]

        total_embedded = 0

        # 각 컬렉션 임베딩
        for coll_info in collections_to_embed:
            collection_name = coll_info["collection"]
            namespace = coll_info["namespace"]
            description = coll_info["description"]
            text_fields = coll_info["text_fields"]

            print(f"📊 [{description}] 임베딩 중...")
            print(f"   컬렉션: {collection_name}")
            print(f"   네임스페이스: {namespace}")

            # MongoDB에서 문서 개수 확인
            collection = mongodb_manager.db[collection_name]
            total_docs = await collection.count_documents({})
            print(f"   문서 수: {total_docs:,}개")

            if total_docs == 0:
                print("   ⚠️  경고: 컬렉션이 비어있습니다\n")
                continue

            start_time = datetime.now()

            # 배치 단위로 문서 읽기 및 임베딩
            batch_size = 100
            embedded_count = 0

            # 모든 문서를 메모리에 로드 (최적화 가능)
            print("   📥 문서 읽기 중...")
            cursor = collection.find({})
            docs = await cursor.to_list(length=total_docs)
            print(f"   ✅ {len(docs):,}개 문서 로드 완료")

            # 문서 포맷 변환
            formatted_docs = []
            for doc in docs:
                # _id를 문자열로 변환
                doc_id = str(doc.get("_id", ""))

                # 텍스트 필드 추출
                text_content = {}
                for field in text_fields:
                    if field in doc:
                        text_content[field] = doc[field]

                # 메타데이터 추가
                metadata = {"_id": doc_id}
                for field in coll_info.get("metadata_fields", []):
                    if field in doc:
                        metadata[field] = doc[field]

                formatted_doc = {
                    "id": doc_id,
                    **text_content,
                    "metadata": metadata
                }
                formatted_docs.append(formatted_doc)

            # 임베딩 생성 및 업로드
            print(f"   🔮 임베딩 생성 및 업로드 중... (배치 크기: {batch_size})")

            for i in range(0, len(formatted_docs), batch_size):
                batch = formatted_docs[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(formatted_docs) + batch_size - 1) // batch_size

                try:
                    await vector_manager.upsert_embeddings(
                        docs=batch,
                        namespace=namespace,
                        id_field="id",  # formatted_doc에서 "id" 필드 사용
                        text_fields=text_fields
                    )
                    embedded_count += len(batch)

                    # 진행 상황 출력
                    if batch_num % 10 == 0 or batch_num == total_batches:
                        progress = (embedded_count / len(formatted_docs)) * 100
                        print(f"   📊 진행: {embedded_count:,}/{len(formatted_docs):,} "
                              f"({progress:.1f}%) - 배치 {batch_num}/{total_batches}")

                except Exception as e:
                    print(f"   ⚠️  배치 {batch_num} 업로드 실패: {e}")
                    continue

            elapsed = (datetime.now() - start_time).total_seconds()
            total_embedded += embedded_count

            print(f"   ✅ 완료: {embedded_count:,}개 벡터 생성")
            print(f"   ⏱️  소요 시간: {elapsed:.2f}초")
            print(f"   ⚡ 처리 속도: {embedded_count / elapsed:.1f} 문서/초\n")

        # 최종 통계 출력
        print("=" * 80)
        print("📈 임베딩 완료 통계")
        print("=" * 80)
        print("인덱스: kidney-medical-embeddings")
        print(f"총 임베딩된 벡터: {total_embedded:,}개\n")

        # MongoDB vector adapter 통계 확인
        print("🔍 MongoDB vector adapter 통계 확인 중...")
        try:
            stats = await vector_manager.get_index_stats()
            if stats:
                print(f"   전체 벡터 수: {stats.get('total_vector_count', 'N/A'):,}")
                print("   네임스페이스 정보:")
                namespaces = stats.get("namespaces", {})
                for ns_name, ns_info in namespaces.items():
                    print(f"     - {ns_name}: {ns_info.get('vector_count', 0):,}개")
        except Exception as e:
            print(f"   ⚠️  통계 조회 실패: {e}")

        print(f"\n완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 연결 종료
        await mongodb_manager.close()
        print("\n🔌 연결 종료")


if __name__ == "__main__":
    asyncio.run(embed_kidney_data_to_local_vector())
