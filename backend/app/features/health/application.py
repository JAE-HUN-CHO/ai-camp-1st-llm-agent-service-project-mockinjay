"""Owner-scoped use cases for the approved Health vertical slices."""

from __future__ import annotations

from app.core.actor import ActorContext
from app.features.health.domain import (
    HealthProfile,
    HealthProfileAccessDenied,
    HealthProfilePatch,
    HealthRecord,
    HealthRecordAccessDenied,
    HealthRecordDraft,
    HealthRecordEmptyUpdate,
    HealthRecordNotFound,
    HealthRecordPatch,
)
from app.features.health.ports import HealthProfileRepository, HealthRecordRepository


def _profile_owner_id(actor: ActorContext) -> str:
    if not actor.user_id:
        raise HealthProfileAccessDenied("authenticated actor is required")
    return actor.user_id


class GetHealthProfile:
    def __init__(self, repository: HealthProfileRepository) -> None:
        self._repository = repository

    async def execute(self, actor: ActorContext) -> HealthProfile:
        return await self._repository.get_for_owner(_profile_owner_id(actor))


class UpdateHealthProfile:
    def __init__(self, repository: HealthProfileRepository) -> None:
        self._repository = repository

    async def execute(
        self, actor: ActorContext, patch: HealthProfilePatch
    ) -> HealthProfile:
        return await self._repository.upsert_for_owner(_profile_owner_id(actor), patch)


def _owner_id(actor: ActorContext) -> str:
    if not actor.user_id:
        raise HealthRecordAccessDenied("authenticated actor is required")
    return actor.user_id


class ListHealthRecords:
    def __init__(self, repository: HealthRecordRepository) -> None:
        self._repository = repository

    async def execute(self, actor: ActorContext) -> list[HealthRecord]:
        return await self._repository.list_for_owner(_owner_id(actor))


class CreateHealthRecord:
    def __init__(self, repository: HealthRecordRepository) -> None:
        self._repository = repository

    async def execute(
        self, actor: ActorContext, draft: HealthRecordDraft
    ) -> HealthRecord:
        return await self._repository.create(_owner_id(actor), draft)


class UpdateHealthRecord:
    def __init__(self, repository: HealthRecordRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        actor: ActorContext,
        record_id: str,
        patch: HealthRecordPatch,
    ) -> HealthRecord:
        owner_id = _owner_id(actor)
        existing = await self._repository.get(record_id, owner_id)
        if existing is None:
            raise HealthRecordNotFound("health record not found")
        if patch.is_empty:
            raise HealthRecordEmptyUpdate("health record patch is empty")
        record = await self._repository.update(record_id, owner_id, patch)
        if record is None:
            raise HealthRecordNotFound("health record not found")
        return record


class DeleteHealthRecord:
    def __init__(self, repository: HealthRecordRepository) -> None:
        self._repository = repository

    async def execute(self, actor: ActorContext, record_id: str) -> bool:
        deleted = await self._repository.delete(record_id, _owner_id(actor))
        if not deleted:
            raise HealthRecordNotFound("health record not found")
        return True
