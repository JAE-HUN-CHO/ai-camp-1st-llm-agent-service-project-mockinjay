#!/usr/bin/env python3
"""Read-only local MongoDB schema and duplicate audit for Phase 3B."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys
from urllib.parse import urlsplit

from motor.motor_asyncio import AsyncIOMotorClient


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import settings
from smoke_common import utc_now, write_json


ALLOWED_FIELDS = {
    "_id",
    "userId",
    "conditions",
    "allergies",
    "dietaryRestrictions",
    "age",
    "gender",
    "updatedAt",
}
EXPECTED_INDEXES = {
    "_id_": {"keys": [["_id", 1]], "unique": True},
    "idx_health_profiles_userId": {"keys": [["userId", 1]], "unique": True},
}


def _require_loopback(uri: str) -> str:
    parsed = urlsplit(uri)
    if parsed.scheme != "mongodb" or parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise ValueError("Health Profile schema audit requires loopback MongoDB")
    return str(parsed.hostname)


async def audit(output: Path) -> None:
    host = _require_loopback(settings.mongodb_uri)
    client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
    try:
        database = client[settings.db_name]
        collection = database.health_profiles
        await client.admin.command("ping")
        document_count = await collection.count_documents({})
        verification_user_ids = [
            str(document["_id"])
            async for document in database.users.find(
                {"username": {"$regex": "^phase3b-(?:owner|other)-"}},
                {"_id": 1},
            )
        ]
        verification_user_count = len(verification_user_ids)
        verification_document_count = await collection.count_documents(
            {"userId": {"$in": verification_user_ids}}
        )
        invalid_owner_document_count = await collection.count_documents(
            {"$nor": [{"userId": {"$type": "string"}}]}
        )

        observed_fields = []
        async for document in collection.aggregate(
            [
                {"$project": {"fields": {"$objectToArray": "$$ROOT"}}},
                {"$unwind": "$fields"},
                {"$group": {"_id": "$fields.k"}},
                {"$sort": {"_id": 1}},
            ]
        ):
            observed_fields.append(str(document["_id"]))

        duplicate_group_count = 0
        async for result_document in collection.aggregate(
            [
                {"$match": {"userId": {"$exists": True}}},
                {"$group": {"_id": "$userId", "count": {"$sum": 1}}},
                {"$match": {"count": {"$gt": 1}}},
                {"$count": "groups"},
            ]
        ):
            duplicate_group_count = int(result_document.get("groups", 0))

        indexes: dict[str, dict[str, object]] = {}
        async for index in collection.list_indexes():
            name = str(index.get("name"))
            indexes[name] = {
                "keys": [list(item) for item in index.get("key", {}).items()],
                "unique": bool(index.get("unique", name == "_id_")),
            }

        unexpected_fields = sorted(set(observed_fields) - ALLOWED_FIELDS)
        field_audit_applicable = document_count > 0
        field_audit_passed = not field_audit_applicable or not unexpected_fields
        schema_drift_count = int(
            not field_audit_passed or bool(invalid_owner_document_count)
        )
        index_drift_count = int(indexes != EXPECTED_INDEXES)
        result = (
            "pass"
            if verification_user_count == 0
            and verification_document_count == 0
            and duplicate_group_count == 0
            and schema_drift_count == 0
            and index_drift_count == 0
            else "fail"
        )
        write_json(
            output,
            {
                "schema_version": 1,
                "result": result,
                "mongodb": {"host": host, "loopback_only": True},
                "collection": "health_profiles",
                "document_count": document_count,
                "field_audit_applicable": field_audit_applicable,
                "field_audit_passed": field_audit_passed,
                "verification_user_count": verification_user_count,
                "verification_document_count": verification_document_count,
                "duplicate_user_id_group_count": duplicate_group_count,
                "invalid_owner_document_count": invalid_owner_document_count,
                "observed_field_names": observed_fields,
                "allowed_field_names": sorted(ALLOWED_FIELDS),
                "unexpected_field_names": unexpected_fields,
                "indexes": indexes,
                "schema_drift_count": schema_drift_count,
                "index_drift_count": index_drift_count,
                "schema_migration_count": 0,
                "index_migration_count": 0,
                "cleanup_operation_count": 0,
                "finished_at": utc_now(),
            },
        )
        if result != "pass":
            raise RuntimeError("Health Profile schema, duplicate, or cleanup audit failed")
    finally:
        client.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(audit(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
