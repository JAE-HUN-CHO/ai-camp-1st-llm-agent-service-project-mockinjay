"""Explicit local MongoDB integration for the Phase 3A Health Records adapter."""

from __future__ import annotations

import os
from urllib.parse import urlsplit
import uuid

from motor.motor_asyncio import AsyncIOMotorClient
import pytest

from app.adapters.mongodb.health_record_repository import MongoHealthRecordRepository
from app.config import settings
from app.features.health.domain import HealthRecordDraft, HealthRecordPatch


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_health_records_round_trip_is_owner_scoped_and_schema_preserving() -> None:
    if not os.getenv("MONGODB_URI"):
        pytest.skip("MONGODB_URI is required for the live Mongo integration smoke")
    uri = settings.mongodb_uri
    parsed = urlsplit(uri)
    if parsed.scheme != "mongodb" or parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        pytest.fail("Health Records integration requires loopback MongoDB")

    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000)
    collection = client[settings.db_name].health_records
    suffix = uuid.uuid4().hex
    owner_id = f"phase3a-owner-{suffix}"
    other_owner = f"phase3a-other-{suffix}"
    repository = MongoHealthRecordRepository(lambda: collection)
    try:
        created = await repository.create(
            owner_id,
            HealthRecordDraft(
                date="2099-01-02",
                hospital="Synthetic Verification Clinic",
                creatinine=1.23,
                gfr=61.0,
            ),
        )
        stored = await collection.find_one({"user_id": owner_id})
        assert stored is not None
        assert set(stored) == {
            "_id",
            "user_id",
            "date",
            "hospital",
            "creatinine",
            "gfr",
            "potassium",
            "phosphorus",
            "hemoglobin",
            "albumin",
            "pth",
            "hco3",
            "memo",
            "created_at",
        }

        assert await repository.get(created.record_id, other_owner) is None
        assert (
            await repository.update(
                created.record_id,
                other_owner,
                HealthRecordPatch({"memo": None}),
            )
            is None
        )
        assert await repository.delete(created.record_id, other_owner) is False

        updated = await repository.update(
            created.record_id,
            owner_id,
            HealthRecordPatch({"memo": None}),
        )
        assert updated is not None and updated.memo is None
        assert await repository.delete(created.record_id, owner_id) is True
        assert await repository.delete(created.record_id, owner_id) is False
    finally:
        await collection.delete_many({"user_id": {"$in": [owner_id, other_owner]}})
        client.close()
