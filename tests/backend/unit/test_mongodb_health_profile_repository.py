"""MongoDB adapter tests for the existing health_profiles schema."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from pymongo import ReturnDocument

from app.adapters.mongodb.health_profile_repository import MongoHealthProfileRepository
from app.features.health.domain import HealthProfilePatch, HealthProfilePersistenceError


class _Collection:
    def __init__(self) -> None:
        self.documents: dict[str, dict[str, object]] = {}
        self.find_queries: list[dict[str, object]] = []
        self.update_calls: list[
            tuple[dict[str, object], dict[str, dict[str, object]], bool, Any]
        ] = []
        self.error: Exception | None = None
        self.force_missing = False

    async def find_one(self, query: dict[str, object]) -> dict[str, object] | None:
        if self.error:
            raise self.error
        self.find_queries.append(deepcopy(query))
        if self.force_missing:
            return None
        document = self.documents.get(str(query["userId"]))
        return deepcopy(document) if document else None

    async def find_one_and_update(
        self,
        query: dict[str, object],
        update: dict[str, dict[str, object]],
        *,
        upsert: bool,
        return_document: Any,
    ) -> dict[str, object] | None:
        if self.error:
            raise self.error
        self.update_calls.append(
            (deepcopy(query), deepcopy(update), upsert, return_document)
        )
        owner_id = str(query["userId"])
        document = self.documents.setdefault(owner_id, {"userId": owner_id})
        document.update(deepcopy(update["$set"]))
        return None if self.force_missing else deepcopy(document)


@pytest.mark.asyncio
async def test_missing_profile_returns_owner_scoped_frozen_default() -> None:
    collection = _Collection()
    repository = MongoHealthProfileRepository(lambda: collection)

    profile = await repository.get_for_owner("actor-a")

    assert profile.owner_id == "actor-a"
    assert profile.conditions == ()
    assert profile.updated_at is None
    assert collection.find_queries == [{"userId": "actor-a"}]
    assert collection.update_calls == []


@pytest.mark.asyncio
async def test_upsert_preserves_schema_and_ignores_null_fields() -> None:
    collection = _Collection()
    collection.documents["actor-a"] = {
        "userId": "actor-a",
        "conditions": ["synthetic-condition"],
        "age": 44,
    }
    repository = MongoHealthProfileRepository(lambda: collection)

    profile = await repository.upsert_for_owner(
        "actor-a",
        HealthProfilePatch(
            {"conditions": None, "dietary_restrictions": ["synthetic-restriction"]}
        ),
    )

    query, update, upsert, return_document = collection.update_calls[0]
    assert query == {"userId": "actor-a"}
    assert upsert is True
    assert return_document == ReturnDocument.AFTER
    assert set(update["$set"]) == {"userId", "updatedAt", "dietaryRestrictions"}
    assert profile.conditions == ("synthetic-condition",)
    assert profile.dietary_restrictions == ("synthetic-restriction",)
    assert profile.age == 44


@pytest.mark.asyncio
async def test_adapter_wraps_database_failure_without_health_values() -> None:
    collection = _Collection()
    collection.error = RuntimeError("synthetic database failure")
    repository = MongoHealthProfileRepository(lambda: collection)

    with pytest.raises(HealthProfilePersistenceError, match="persistence failed"):
        await repository.get_for_owner("actor-a")


@pytest.mark.asyncio
async def test_atomic_upsert_missing_result_is_explicit_after_one_scoped_write() -> None:
    collection = _Collection()
    collection.force_missing = True
    repository = MongoHealthProfileRepository(lambda: collection)

    with pytest.raises(HealthProfilePersistenceError, match="persistence failed"):
        await repository.upsert_for_owner("actor-a", HealthProfilePatch({"age": 44}))

    assert len(collection.update_calls) == 1
    assert collection.update_calls[0][0] == {"userId": "actor-a"}
    assert collection.find_queries == []
