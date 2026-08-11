"""
MongoDB 데이터 적재 스크립트 - 신장(Kidney) 관련 데이터

필터링된 JSONL 파일들을 MongoDB의 새로운 컬렉션에 적재합니다:
- papers_kidney.jsonl → careguide.papers_kidney
- medical_kidney.jsonl → careguide.medical_kidney
- qa_kidney.jsonl → careguide.qa_kidney
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
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


async def load_kidney_data_to_mongodb():
    """필터링된 신장 데이터를 MongoDB에 적재"""

    print("=" * 80)
    print("📊 신장(Kidney) 데이터 MongoDB 적재 시작")
    print("=" * 80)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # MongoDB Manager 초기화
    mongodb_uri = os.getenv(
        "MONGODB_URI",
        "mongodb://careguide:careguide_local@localhost:27017/?authSource=admin",
    )
    manager = MongoDBManager(mongodb_uri, db_name="careguide")

    try:
        # 연결 확인
        print("🔌 MongoDB 연결 확인 중...")
        await manager.connect()
        print("✅ MongoDB 연결 성공\n")

        # 데이터 파일 경로 설정
        data_dir = project_root / "data" / "preprocess" / "kidney_filtered"

        files_to_load = [
            {
                "file": data_dir / "papers_kidney.jsonl",
                "collection": "papers_kidney",
                "description": "연구 논문"
            },
            {
                "file": data_dir / "medical_kidney.jsonl",
                "collection": "medical_kidney",
                "description": "의료 문서"
            },
            {
                "file": data_dir / "qa_kidney.jsonl",
                "collection": "qa_kidney",
                "description": "QA 데이터"
            }
        ]

        total_loaded = 0

        # 각 파일 적재
        for file_info in files_to_load:
            file_path = file_info["file"]
            collection_name = file_info["collection"]
            description = file_info["description"]

            print(f"📁 [{description}] 적재 중...")
            print(f"   파일: {file_path.name}")
            print(f"   컬렉션: {collection_name}")

            if not file_path.exists():
                print(f"   ⚠️  경고: 파일이 존재하지 않습니다 - {file_path}")
                print()
                continue

            # 파일 크기 확인
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"   파일 크기: {file_size_mb:.2f} MB")

            start_time = datetime.now()

            try:
                # JSONL 파일 읽기
                import json
                from hashlib import md5
                from pymongo import UpdateOne

                data = []
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        data.append(json.loads(line))

                print(f"   📖 {len(data):,}개 문서 읽기 완료")

                # 컬렉션 접근
                collection = manager.db[collection_name]

                # 컬렉션 타입에 따라 적절한 upsert 로직 사용
                if "papers" in collection_name:
                    # Papers: DOI 기반 upsert
                    inserted = 0
                    skipped = 0
                    for paper in data:
                        doi = paper.get("metadata", {}).get("doi")
                        if doi and doi.strip():
                            try:
                                result = await collection.update_one(
                                    {"metadata.doi": doi},
                                    {"$set": paper},
                                    upsert=True
                                )
                                if result.upserted_id:
                                    inserted += 1
                            except Exception:
                                skipped += 1
                        else:
                            skipped += 1
                    loaded_count = inserted
                    if skipped > 0:
                        print(f"   ℹ️  {skipped:,}개 문서 스킵 (DOI 없음 또는 중복)")

                elif "medical" in collection_name:
                    # Medical: 텍스트 해시 기반 upsert
                    operations = []
                    for med in data:
                        text_hash = md5(med.get("text", "").encode()).hexdigest()
                        med["text_hash"] = text_hash
                        operations.append(
                            UpdateOne(
                                {"text_hash": text_hash},
                                {"$set": med},
                                upsert=True
                            )
                        )

                    if operations:
                        result = await collection.bulk_write(operations)
                        loaded_count = result.upserted_count
                        if result.modified_count > 0:
                            print(f"   ℹ️  {result.modified_count:,}개 문서 업데이트 (중복)")
                    else:
                        loaded_count = 0

                elif "qa" in collection_name:
                    # QA: 질문 해시 기반 upsert
                    operations = []
                    for qa in data:
                        q_hash = md5(qa.get("question", "").encode()).hexdigest()
                        qa["question_hash"] = q_hash
                        operations.append(
                            UpdateOne(
                                {"question_hash": q_hash},
                                {"$set": qa},
                                upsert=True
                            )
                        )

                    if operations:
                        result = await collection.bulk_write(operations)
                        loaded_count = result.upserted_count
                        if result.modified_count > 0:
                            print(f"   ℹ️  {result.modified_count:,}개 문서 업데이트 (중복)")
                    else:
                        loaded_count = 0

                else:
                    # 일반 삽입
                    result = await collection.insert_many(data, ordered=False)
                    loaded_count = len(result.inserted_ids)

                elapsed = (datetime.now() - start_time).total_seconds()
                total_loaded += loaded_count

                print(f"   ✅ 성공: {loaded_count:,}개 문서 적재")
                print(f"   ⏱️  소요 시간: {elapsed:.2f}초")

            except Exception as e:
                print(f"   ❌ 실패: {e}")
                import traceback
                traceback.print_exc()

            print()

        # 최종 통계 출력
        print("=" * 80)
        print("📈 적재 완료 통계")
        print("=" * 80)

        for file_info in files_to_load:
            collection_name = file_info["collection"]
            description = file_info["description"]

            count = await manager.db[collection_name].count_documents({})
            print(f"✓ {description} ({collection_name}): {count:,}개 문서")

        print(f"\n총 적재된 문서: {total_loaded:,}개")
        print(f"완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 연결 종료
        await manager.close()
        print("\n🔌 MongoDB 연결 종료")


if __name__ == "__main__":
    asyncio.run(load_kidney_data_to_mongodb())
