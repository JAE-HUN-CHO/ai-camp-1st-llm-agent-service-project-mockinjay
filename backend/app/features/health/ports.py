"""Consumer-owned persistence port for Phase 3A Health Records."""

from __future__ import annotations

from typing import Protocol

from app.features.health.domain import HealthRecord, HealthRecordDraft, HealthRecordPatch


class HealthRecordRepository(Protocol):
    """Every resource operation requires the trusted owner identifier."""

    async def list_for_owner(self, owner_id: str) -> list[HealthRecord]: ...

    async def create(self, owner_id: str, draft: HealthRecordDraft) -> HealthRecord: ...

    async def get(self, record_id: str, owner_id: str) -> HealthRecord | None: ...

    async def update(
        self, record_id: str, owner_id: str, patch: HealthRecordPatch
    ) -> HealthRecord | None: ...

    async def delete(self, record_id: str, owner_id: str) -> bool: ...
