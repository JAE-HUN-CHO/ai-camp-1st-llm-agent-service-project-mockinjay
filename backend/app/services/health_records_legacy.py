"""Compatibility facade for the frozen Health Records REST v1 behavior."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from app.core.actor import ActorContext
from app.features.health.domain import (
    MUTABLE_HEALTH_RECORD_FIELDS,
    HealthRecord,
    HealthRecordAccessDenied,
    HealthRecordDraft,
    HealthRecordEmptyUpdate,
    HealthRecordNotFound,
    HealthRecordPatch,
)


def _owner_id(actor: ActorContext) -> str:
    if not actor.user_id:
        raise HealthRecordAccessDenied("authenticated actor is required")
    return actor.user_id


class LegacyHealthRecordsFacade:
    """Keep the pre-Phase-3A implementation available for restart rollback."""

    def __init__(self, collection_factory: Callable[[], Any]) -> None:
        self._collection_factory = collection_factory

    @property
    def _collection(self) -> Any:
        return self._collection_factory()

    async def list(self, actor: ActorContext) -> list[HealthRecord]:
        owner_id = _owner_id(actor)
        cursor = self._collection.find({"user_id": owner_id}).sort("date", -1)
        return [self._to_domain(document) async for document in cursor]

    async def create(
        self, actor: ActorContext, draft: HealthRecordDraft
    ) -> HealthRecord:
        owner_id = _owner_id(actor)
        document = {
            "user_id": owner_id,
            **draft.as_fields(),
            "created_at": datetime.now(UTC),
        }
        result = await self._collection.insert_one(document)
        return HealthRecord(
            record_id=str(result.inserted_id),
            owner_id=owner_id,
            **draft.as_fields(),
        )

    async def update(
        self,
        actor: ActorContext,
        record_id: str,
        patch: HealthRecordPatch,
    ) -> HealthRecord:
        owner_id = _owner_id(actor)
        object_id = self._parse_id(record_id)
        if object_id is None:
            raise HealthRecordNotFound("health record not found")

        query = {"_id": object_id, "user_id": owner_id}
        existing = await self._collection.find_one(query)
        if not existing:
            raise HealthRecordNotFound("health record not found")
        if patch.is_empty:
            raise HealthRecordEmptyUpdate("health record patch is empty")

        await self._collection.update_one(query, {"$set": patch.as_fields()})
        updated = await self._collection.find_one(query)
        if not updated:
            raise HealthRecordNotFound("health record not found")
        return self._to_domain(updated)

    async def delete(self, actor: ActorContext, record_id: str) -> bool:
        owner_id = _owner_id(actor)
        object_id = self._parse_id(record_id)
        if object_id is None:
            raise HealthRecordNotFound("health record not found")
        result = await self._collection.delete_one(
            {"_id": object_id, "user_id": owner_id}
        )
        if result.deleted_count == 0:
            raise HealthRecordNotFound("health record not found")
        return True

    @staticmethod
    def _parse_id(record_id: str) -> ObjectId | None:
        try:
            return ObjectId(record_id)
        except (InvalidId, TypeError, ValueError):
            return None

    @staticmethod
    def _to_domain(document: Mapping[str, Any]) -> HealthRecord:
        fields = {field: document.get(field) for field in MUTABLE_HEALTH_RECORD_FIELDS}
        return HealthRecord(
            record_id=str(document["_id"]),
            owner_id=str(document["user_id"]),
            **fields,
        )
