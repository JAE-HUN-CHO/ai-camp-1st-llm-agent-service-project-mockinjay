"""Explicit local MongoDB integration for the Phase 3B Health Profile adapter."""

from __future__ import annotations

import os
from urllib.parse import urlsplit
import uuid

from motor.motor_asyncio import AsyncIOMotorClient
import pytest

from app.adapters.mongodb.health_profile_repository import MongoHealthProfileRepository
from app.config import settings
from app.features.health.domain import HealthProfile, HealthProfilePatch


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_health_profile_round_trip_is_owner_scoped_and_schema_preserving() -> None:
    explicit_uri = os.getenv("MONGODB_URI")
    if not explicit_uri:
        pytest.skip("MONGODB_URI is required for the live Mongo integration smoke")
    uri = settings.mongodb_uri
    if uri != explicit_uri:
        pytest.fail("Health Profile integration URI must match the explicit MONGODB_URI")
    parsed = urlsplit(uri)
    if parsed.scheme != "mongodb" or parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        pytest.fail("Health Profile integration requires loopback MongoDB")

    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000)
    collection = client[settings.db_name].health_profiles
    suffix = uuid.uuid4().hex
    owner_id = f"phase3b-owner-{suffix}"
    other_owner = f"phase3b-other-{suffix}"
    repository = MongoHealthProfileRepository(lambda: collection)
    try:
        created = await repository.upsert_for_owner(
            owner_id,
            HealthProfilePatch(
                {
                    "conditions": ["synthetic-condition"],
                    "allergies": ["synthetic-allergy"],
                    "dietary_restrictions": ["synthetic-restriction"],
                    "age": 44,
                    "gender": "other",
                }
            ),
        )
        stored = await collection.find_one({"userId": owner_id})
        assert stored is not None
        assert set(stored) == {
            "_id",
            "userId",
            "conditions",
            "allergies",
            "dietaryRestrictions",
            "age",
            "gender",
            "updatedAt",
        }
        assert created.owner_id == owner_id

        other = await repository.get_for_owner(other_owner)
        assert other == HealthProfile.empty(other_owner)
        assert await collection.count_documents({"userId": other_owner}) == 0

        preserved = await repository.upsert_for_owner(
            owner_id, HealthProfilePatch({"conditions": None})
        )
        assert preserved.conditions == ("synthetic-condition",)
        assert preserved.age == 44
        assert preserved.updated_at is not None
        assert created.updated_at is not None
        assert preserved.updated_at >= created.updated_at
        assert await collection.count_documents({"userId": owner_id}) == 1
        stored_after = await collection.find_one({"userId": owner_id})
        assert stored_after is not None
        assert set(stored_after) == set(stored)
        assert stored_after["updatedAt"] == preserved.updated_at
    finally:
        await collection.delete_many({"userId": {"$in": [owner_id, other_owner]}})
        client.close()
