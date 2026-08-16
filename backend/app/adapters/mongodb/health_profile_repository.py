"""MongoDB adapter for the existing owner-scoped health_profiles schema."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
import logging
from typing import Any

from pymongo import ReturnDocument

from app.features.health.domain import (
    HealthProfile,
    HealthProfilePatch,
    HealthProfilePersistenceError,
)


logger = logging.getLogger(__name__)

_MONGO_FIELD = {
    "conditions": "conditions",
    "allergies": "allergies",
    "dietary_restrictions": "dietaryRestrictions",
    "age": "age",
    "gender": "gender",
}


class MongoHealthProfileRepository:
    """Persist profiles without changing collection fields or indexes."""

    def __init__(self, collection_factory: Callable[[], Any]) -> None:
        self._collection_factory = collection_factory

    @property
    def _collection(self) -> Any:
        return self._collection_factory()

    async def get_for_owner(self, owner_id: str) -> HealthProfile:
        try:
            document = await self._collection.find_one({"userId": owner_id})
            return self._to_domain(document) if document else HealthProfile.empty(owner_id)
        except Exception as exc:
            self._raise_persistence_error(exc)

    async def upsert_for_owner(
        self, owner_id: str, patch: HealthProfilePatch
    ) -> HealthProfile:
        update = {
            "userId": owner_id,
            "updatedAt": datetime.now(UTC),
            **{
                _MONGO_FIELD[field]: value
                for field, value in patch.as_persisted_fields().items()
            },
        }
        try:
            document = await self._collection.find_one_and_update(
                {"userId": owner_id},
                {"$set": update},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            if document is None:
                raise RuntimeError("health profile upsert result was not found")
            return self._to_domain(document)
        except Exception as exc:
            self._raise_persistence_error(exc)

    @staticmethod
    def _to_domain(document: Mapping[str, Any]) -> HealthProfile:
        updated_at = document.get("updatedAt")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        return HealthProfile(
            owner_id=str(document["userId"]),
            conditions=tuple(document.get("conditions", [])),
            allergies=tuple(document.get("allergies", [])),
            dietary_restrictions=tuple(document.get("dietaryRestrictions", [])),
            age=document.get("age"),
            gender=document.get("gender"),
            updated_at=updated_at,
        )

    @staticmethod
    def _raise_persistence_error(exc: Exception) -> None:
        logger.warning("Health Profile persistence failed")
        raise HealthProfilePersistenceError("health profile persistence failed") from exc
