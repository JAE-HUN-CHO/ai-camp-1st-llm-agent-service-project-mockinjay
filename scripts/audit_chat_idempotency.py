#!/usr/bin/env python3
"""Read-only audit for additive, user-scoped Chat idempotency writes."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db.context_manager import ContextManager  # noqa: E402


async def audit() -> dict[str, object]:
    """
    클라이언트 메시지 ID 기반 대화 데이터의 멱등성 상태를 감사한다.
    
    Returns:
    	dict[str, object]: 중복 그룹, 스키마 버전, 결정적 ID 문서 수와 감사 결과를 포함한 보고서
    """
    manager = ContextManager()
    await manager.connect()
    try:
        existing = await manager.db.conversation_history.count_documents(
            {"client_message_id": {"$exists": True}}
        )
        pipeline = [
            {"$match": {"client_message_id": {"$exists": True}}},
            {
                "$group": {
                    "_id": {
                        "user_id": "$user_id",
                        "client_message_id": "$client_message_id",
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$match": {"count": {"$gt": 1}}},
            {"$count": "groups"},
        ]
        rows = await manager.db.conversation_history.aggregate(pipeline).to_list(
            length=1
        )
        schema_v2 = await manager.db.conversation_history.count_documents(
            {"client_message_id": {"$exists": True}, "_schema_version": 2}
        )
        deterministic_ids = await manager.db.conversation_history.count_documents(
            {"_id": {"$regex": r"^chat-v1:[0-9a-f]{64}$"}}
        )
        return {
            "result": "pass" if not rows else "fail",
            "strategy": "user_scoped_deterministic_mongodb_id_set_on_insert",
            "existing_client_message_id_documents": existing,
            "duplicate_user_message_id_groups": rows[0]["groups"] if rows else 0,
            "schema_version_2_documents": schema_v2,
            "deterministic_id_documents": deterministic_ids,
            "runtime_additive_schema_version": 2,
            "custom_unique_index_created": False,
            "backfill_performed": False,
            "audit_write_count": 0,
            "destructive_schema_or_index_mutations": 0,
        }
    finally:
        await manager.close()


def main() -> int:
    """
    감사 결과를 JSON으로 출력하고 중복 그룹 존재 여부에 따라 종료 코드를 반환합니다.
    
    Returns:
    	int: 중복 사용자 메시지 ID 그룹이 있으면 1, 그렇지 않으면 0
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = asyncio.run(audit())
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 1 if result["duplicate_user_message_id_groups"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
