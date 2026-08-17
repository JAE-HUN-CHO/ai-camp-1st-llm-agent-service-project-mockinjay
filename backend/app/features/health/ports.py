"""Consumer-owned persistence ports for the approved Health slices."""

from __future__ import annotations

from typing import Protocol

from app.features.health.domain import (
    HealthProfile,
    HealthProfilePatch,
    HealthRecord,
    HealthRecordDraft,
    HealthRecordPatch,
)


class HealthProfileRepository(Protocol):
    """Every profile operation is scoped by the trusted actor owner."""

    async def get_for_owner(self, owner_id: str) -> HealthProfile:
        """Load one health profile within the supplied owner boundary."""
        ...

    async def upsert_for_owner(
        self, owner_id: str, patch: HealthProfilePatch
    ) -> HealthProfile:
        """Persist one health profile within the supplied owner boundary."""
        ...


class HealthRecordRepository(Protocol):
    """Every resource operation requires the trusted owner identifier."""

    async def list_for_owner(self, owner_id: str) -> list[HealthRecord]: ...

    async def create(self, owner_id: str, draft: HealthRecordDraft) -> HealthRecord: ...

    async def get(self, record_id: str, owner_id: str) -> HealthRecord | None: ...

    async def update(
        self, record_id: str, owner_id: str, patch: HealthRecordPatch
    ) -> HealthRecord | None: ...

    async def delete(self, record_id: str, owner_id: str) -> bool: ...
