"""MongoDB adapter for the Phase 3A Health Record repository port."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument

from app.features.health.domain import (
    MUTABLE_HEALTH_RECORD_FIELDS,
    HealthRecord,
    HealthRecordDraft,
    HealthRecordPatch,
    HealthRecordPersistenceError,
)


logger = logging.getLogger(__name__)


class MongoHealthRecordRepository:
    """Persist owner-scoped records without changing ``health_records`` schema."""

    def __init__(self, collection_factory: Callable[[], Any]) -> None:
        self._collection_factory = collection_factory

    @property
    def _collection(self) -> Any:
        return self._collection_factory()

    async def list_for_owner(self, owner_id: str) -> list[HealthRecord]:
        try:
            cursor = self._collection.find({"user_id": owner_id}).sort("date", -1)
            return [self._to_domain(document) async for document in cursor]
        except Exception as exc:
            self._raise_persistence_error(exc)

    async def create(
        self, owner_id: str, draft: HealthRecordDraft
    ) -> HealthRecord:
        document = {
            "user_id": owner_id,
            **draft.as_fields(),
            "created_at": datetime.now(UTC),
        }
        try:
            result = await self._collection.insert_one(document)
            return HealthRecord(
                record_id=str(result.inserted_id),
                owner_id=owner_id,
                **draft.as_fields(),
            )
        except Exception as exc:
            self._raise_persistence_error(exc)

    async def get(self, record_id: str, owner_id: str) -> HealthRecord | None:
        object_id = self._parse_id(record_id)
        if object_id is None:
            return None
        try:
            document = await self._collection.find_one(
                {"_id": object_id, "user_id": owner_id}
            )
            return self._to_domain(document) if document else None
        except Exception as exc:
            self._raise_persistence_error(exc)

    async def update(
        self,
        record_id: str,
        owner_id: str,
        patch: HealthRecordPatch,
    ) -> HealthRecord | None:
        object_id = self._parse_id(record_id)
        if object_id is None or patch.is_empty:
            return None
        try:
            document = await self._collection.find_one_and_update(
                {"_id": object_id, "user_id": owner_id},
                {"$set": patch.as_fields()},
                return_document=ReturnDocument.AFTER,
            )
            return self._to_domain(document) if document else None
        except Exception as exc:
            self._raise_persistence_error(exc)

    async def delete(self, record_id: str, owner_id: str) -> bool:
        object_id = self._parse_id(record_id)
        if object_id is None:
            return False
        try:
            result = await self._collection.delete_one(
                {"_id": object_id, "user_id": owner_id}
            )
            return result.deleted_count == 1
        except Exception as exc:
            self._raise_persistence_error(exc)

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

    @staticmethod
    def _raise_persistence_error(exc: Exception) -> None:
        logger.warning("Health Record persistence failed")
        raise HealthRecordPersistenceError("health record persistence failed") from exc
