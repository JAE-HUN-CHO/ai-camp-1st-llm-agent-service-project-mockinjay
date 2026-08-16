#!/usr/bin/env python3
"""Read-only local MongoDB schema audit for the Phase 3A collection."""

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


EXPECTED_CREATE_FIELDS = {
    "_id",
    "albumin",
    "created_at",
    "creatinine",
    "date",
    "gfr",
    "hco3",
    "hemoglobin",
    "hospital",
    "memo",
    "phosphorus",
    "potassium",
    "pth",
    "user_id",
}
BASELINE_INDEXES = [
    {"name": "_id_", "keys": [["_id", 1]], "unique": True},
]


def evaluate_schema_audit(
    *,
    document_count: int,
    verification_document_count: int,
    observed_field_names: list[str],
    indexes: list[dict[str, object]],
) -> dict[str, object]:
    """Compare only observable schema state and the frozen baseline index snapshot."""
    schema_observed = document_count > 0
    schema_migration_count = int(
        schema_observed and set(observed_field_names) != EXPECTED_CREATE_FIELDS
    )
    index_migration_count = int(indexes != BASELINE_INDEXES)
    result = (
        "pass"
        if verification_document_count == 0
        and schema_migration_count == 0
        and index_migration_count == 0
        else "fail"
    )
    return {
        "result": result,
        "schema_observed": schema_observed,
        "schema_migration_count": schema_migration_count,
        "index_migration_count": index_migration_count,
    }


async def audit(output: Path) -> None:
    parsed = urlsplit(settings.mongodb_uri)
    if parsed.scheme != "mongodb" or parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise ValueError("Health Records schema audit requires loopback MongoDB")

    client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
    try:
        database = client[settings.db_name]
        collection = database.health_records
        await client.admin.command("ping")
        document_count = await collection.count_documents({})
        verification_document_count = await collection.count_documents(
            {"user_id": {"$regex": "^phase3a-(?:owner|other)-"}}
        )
        field_names = []
        async for document in collection.aggregate(
            [
                {"$project": {"fields": {"$objectToArray": "$$ROOT"}}},
                {"$unwind": "$fields"},
                {"$group": {"_id": "$fields.k"}},
                {"$sort": {"_id": 1}},
            ]
        ):
            field_names.append(str(document["_id"]))
        indexes = []
        async for index in collection.list_indexes():
            indexes.append(
                {
                    "name": index.get("name"),
                    "keys": [list(item) for item in index.get("key", {}).items()],
                    "unique": bool(index.get("unique", index.get("name") == "_id_")),
                }
            )
        indexes.sort(key=lambda item: str(item["name"]))
        evaluation = evaluate_schema_audit(
            document_count=document_count,
            verification_document_count=verification_document_count,
            observed_field_names=field_names,
            indexes=indexes,
        )
        write_json(
            output,
            {
                "schema_version": 1,
                **evaluation,
                "mongodb": {"host": parsed.hostname, "loopback_only": True},
                "collection": "health_records",
                "document_count": document_count,
                "verification_document_count": verification_document_count,
                "observed_field_names": field_names,
                "frozen_create_field_names": sorted(EXPECTED_CREATE_FIELDS),
                "indexes": indexes,
                "cleanup_operation_count": 0,
                "finished_at": utc_now(),
            },
        )
        if evaluation["result"] != "pass":
            raise RuntimeError("Health Records schema or cleanup audit failed")
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
