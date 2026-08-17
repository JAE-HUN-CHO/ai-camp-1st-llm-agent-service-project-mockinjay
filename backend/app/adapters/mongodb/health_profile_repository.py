"""MongoDB adapter for the existing owner-scoped health_profiles schema."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
import logging
from typing import Protocol

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


class _HealthProfileCollection(Protocol):
    async def find_one(
        self, query: Mapping[str, object]
    ) -> Mapping[str, object] | None:
        """Find one health-profile document by an owner-scoped query."""
        ...

    async def find_one_and_update(
        self,
        query: Mapping[str, object],
        update: Mapping[str, object],
        *,
        upsert: bool,
        return_document: object,
    ) -> Mapping[str, object] | None:
        """Atomically update and return one owner-scoped profile document."""
        ...


class _MissingUpsertResult(RuntimeError):
    pass


class MongoHealthProfileRepository:
    """Persist profiles without changing collection fields or indexes."""

    def __init__(
        self, collection_factory: Callable[[], _HealthProfileCollection]
    ) -> None:
        """Initialize the repository with a lazy MongoDB collection factory."""
        self._collection_factory = collection_factory

    @property
    def _collection(self) -> _HealthProfileCollection:
        """Resolve the current MongoDB health-profile collection."""
        return self._collection_factory()

    async def get_for_owner(self, owner_id: str) -> HealthProfile:
        """Load one profile without reading outside the supplied owner scope."""
        try:
            document = await self._collection.find_one({"userId": owner_id})
            return self._to_domain(document) if document else HealthProfile.empty(owner_id)
        except Exception as exc:  # noqa: BLE001 - translate Mongo driver failures
            self._raise_persistence_error(exc)

    async def upsert_for_owner(
        self, owner_id: str, patch: HealthProfilePatch
    ) -> HealthProfile:
        """Atomically persist and return a profile for the supplied owner."""
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
                self._raise_missing_upsert_result()
            return self._to_domain(document)
        except Exception as exc:  # noqa: BLE001 - translate Mongo driver failures
            self._raise_persistence_error(exc)

    @staticmethod
    def _raise_missing_upsert_result() -> None:
        """Raise the explicit failure used when an upsert returns no document."""
        raise _MissingUpsertResult

    @staticmethod
    def _to_domain(document: Mapping[str, object]) -> HealthProfile:
        """Convert one stored health-profile document to the domain model."""
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
        """Translate a MongoDB failure without exposing health values."""
        logger.warning("Health Profile persistence failed")
        raise HealthProfilePersistenceError from exc
