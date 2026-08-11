"""
신장(Kidney) 데이터베이스 통합 설정 스크립트

MongoDB와 로컬 Ollama 임베딩 경로를 검증하는 전체 프로세스를 실행합니다.

단계:
1. MongoDB에 필터링된 JSONL 파일 적재
2. Ollama 임베딩 생성 경로 확인

사용법:
    python setup_kidney_database.py

옵션:
    python setup_kidney_database.py --skip-mongodb    # MongoDB 적재 건너뛰기
    python setup_kidney_database.py --skip-vector   # 벡터 임베딩 건너뛰기
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import argparse

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


async def run_mongodb_loading():
    """MongoDB 데이터 적재 실행"""
    print("\n" + "=" * 80)
    print("🗄️  STEP 1: MongoDB 데이터 적재")
    print("=" * 80 + "\n")

    # load_kidney_data 모듈 임포트 및 실행
    from load_kidney_data import load_kidney_data_to_mongodb

    await load_kidney_data_to_mongodb()


async def run_local_vector_embedding():
    """Ollama 임베딩 실행"""
    print("\n" + "=" * 80)
    print("🔮 STEP 2: Ollama 벡터 임베딩")
    print("=" * 80 + "\n")

    # embed_kidney_data 모듈 임포트 및 실행
    from embed_kidney_data import embed_kidney_data_to_local_vector

    await embed_kidney_data_to_local_vector()


async def verify_setup():
    """설정 검증"""
    print("\n" + "=" * 80)
    print("✅ STEP 3: 설정 검증")
    print("=" * 80 + "\n")

    from parlant.database.mongodb_manager import MongoDBManager
    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")

    # MongoDB 검증
    print("🔍 MongoDB 데이터 검증 중...")
    mongodb_manager = MongoDBManager(mongodb_uri, db_name="careguide")

    try:
        await mongodb_manager.connect()

        collections = ["papers_kidney", "medical_kidney", "qa_kidney"]
        total_docs = 0

        for collection_name in collections:
            count = await mongodb_manager.db[collection_name].count_documents({})
            total_docs += count
            print(f"   ✓ {collection_name}: {count:,}개 문서")

        print(f"\n   총 문서 수: {total_docs:,}개")

        await mongodb_manager.close()

    except Exception as e:
        print(f"   ❌ MongoDB 검증 실패: {e}")

    print("\n🔍 Ollama/MongoDB vector 경로 확인")
    print(f"   Ollama 모델: {os.getenv('OLLAMA_MODEL', 'qwen3.6:27b-mlx')}")
    print(f"   임베딩 모델: {os.getenv('OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text-v2-moe')}")


async def main():
    """메인 실행 함수"""

    # 명령행 인자 파싱
    parser = argparse.ArgumentParser(
        description="신장(Kidney) 데이터를 MongoDB와 로컬 Ollama 임베딩 경로에 적재합니다."
    )
    parser.add_argument(
        "--skip-mongodb",
        action="store_true",
        help="MongoDB 적재 단계를 건너뜁니다"
    )
    parser.add_argument(
        "--skip-vector",
        action="store_true",
        help="벡터 임베딩 단계를 건너뜁니다"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="검증만 수행합니다 (적재하지 않음)"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("🚀 신장(Kidney) 데이터베이스 설정 시작")
    print("=" * 80)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 환경 변수 확인
    print("\n📋 환경 설정 확인:")
    mongodb_uri = os.getenv("MONGODB_URI")
    print(f"   MONGODB_URI: {'✅ 설정됨' if mongodb_uri else '❌ 미설정'}")

    if not mongodb_uri and not args.skip_mongodb:
        print("\n❌ 오류: MONGODB_URI가 설정되지 않았습니다.")
        print("   .env 파일에 MONGODB_URI를 추가하세요.")
        return

    start_time = datetime.now()

    try:
        # 검증만 수행하는 경우
        if args.verify_only:
            await verify_setup()
            return

        # Step 1: MongoDB 적재
        if not args.skip_mongodb:
            await run_mongodb_loading()
        else:
            print("\n⏭️  MongoDB 적재를 건너뜁니다 (--skip-mongodb)")

        # Step 2: Ollama 임베딩
        if not args.skip_vector:
            await run_local_vector_embedding()
        else:
            print("\n⏭️  벡터 임베딩을 건너뜁니다 (--skip-vector)")

        # Step 3: 검증
        await verify_setup()

        # 최종 요약
        elapsed = (datetime.now() - start_time).total_seconds()
        elapsed_minutes = int(elapsed // 60)
        elapsed_seconds = int(elapsed % 60)

        print("\n" + "=" * 80)
        print("🎉 데이터베이스 설정 완료!")
        print("=" * 80)
        print(f"총 소요 시간: {elapsed_minutes}분 {elapsed_seconds}초")
        print(f"완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n✅ 신장(Kidney) 데이터가 성공적으로 적재되었습니다.")
        print("\n다음 단계:")
        print("   1. 하이브리드 검색 테스트: python -m parlant.search.hybrid_search")
        print("   2. CareGuide 챗봇 실행: cd client && python app.py")

    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
