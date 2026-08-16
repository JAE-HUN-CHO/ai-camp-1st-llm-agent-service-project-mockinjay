"""Application tests for the Phase 3A Health Records slice."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.core.actor import ActorContext
from app.features.health.application import (
    CreateHealthRecord,
    DeleteHealthRecord,
    ListHealthRecords,
    UpdateHealthRecord,
)
from app.features.health.domain import (
    HealthRecord,
    HealthRecordAccessDenied,
    HealthRecordDraft,
    HealthRecordNotFound,
    HealthRecordPatch,
)


class _FakeRepository:
    def __init__(self) -> None:
        self.records = {
            "record-1": HealthRecord(
                record_id="record-1",
                owner_id="owner-1",
                date="2026-08-16",
                hospital="Synthetic Clinic",
                creatinine=1.2,
                gfr=62.0,
                memo="initial",
            )
        }
        self.calls: list[tuple[str, str]] = []
        self.write_attempts: list[tuple[str, str]] = []
        self.writes: list[tuple[str, str]] = []

    @property
    def unauthorized_writes(self) -> int:
        return sum(request_owner != record_owner for request_owner, record_owner in self.writes)

    @property
    def unauthorized_write_attempts(self) -> int:
        return sum(
            request_owner != record_owner
            for request_owner, record_owner in self.write_attempts
        )

    async def list_for_owner(self, owner_id: str) -> list[HealthRecord]:
        self.calls.append(("list", owner_id))
        return [record for record in self.records.values() if record.owner_id == owner_id]

    async def create(self, owner_id: str, draft: HealthRecordDraft) -> HealthRecord:
        self.calls.append(("create", owner_id))
        record = HealthRecord(record_id="record-2", owner_id=owner_id, **draft.as_fields())
        self.write_attempts.append((owner_id, record.owner_id))
        self.writes.append((owner_id, record.owner_id))
        self.records[record.record_id] = record
        return record

    async def get(self, record_id: str, owner_id: str) -> HealthRecord | None:
        self.calls.append(("get", owner_id))
        record = self.records.get(record_id)
        return record if record and record.owner_id == owner_id else None

    async def update(
        self, record_id: str, owner_id: str, patch: HealthRecordPatch
    ) -> HealthRecord | None:
        self.calls.append(("update", owner_id))
        original = self.records.get(record_id)
        if original is not None:
            self.write_attempts.append((owner_id, original.owner_id))
        record = await self.get(record_id, owner_id)
        if record is None:
            return None
        updated = replace(record, **patch.as_fields())
        self.writes.append((owner_id, record.owner_id))
        self.records[record_id] = updated
        return updated

    async def delete(self, record_id: str, owner_id: str) -> bool:
        self.calls.append(("delete", owner_id))
        record = self.records.get(record_id)
        if record is not None:
            self.write_attempts.append((owner_id, record.owner_id))
        if record is None or record.owner_id != owner_id:
            return False
        self.writes.append((owner_id, record.owner_id))
        del self.records[record_id]
        return True


@pytest.mark.asyncio
async def test_health_record_crud_is_owner_scoped_and_preserves_null_unset() -> None:
    repository = _FakeRepository()
    actor = ActorContext(user_id="owner-1")

    listed = await ListHealthRecords(repository).execute(actor)
    created = await CreateHealthRecord(repository).execute(
        actor,
        HealthRecordDraft(
            date="2026-08-17",
            hospital="Synthetic Clinic",
            creatinine=1.1,
            gfr=64.0,
        ),
    )
    updated = await UpdateHealthRecord(repository).execute(
        actor,
        "record-1",
        HealthRecordPatch({"memo": None}),
    )
    deleted = await DeleteHealthRecord(repository).execute(actor, created.record_id)

    assert [record.record_id for record in listed] == ["record-1"]
    assert created.owner_id == "owner-1"
    assert updated.memo is None
    assert updated.date == "2026-08-16"
    assert deleted is True
    assert all(owner_id == "owner-1" for _, owner_id in repository.calls)


@pytest.mark.asyncio
async def test_missing_actor_fails_before_repository_access() -> None:
    repository = _FakeRepository()

    with pytest.raises(HealthRecordAccessDenied):
        await ListHealthRecords(repository).execute(ActorContext(user_id=""))

    assert repository.calls == []


@pytest.mark.asyncio
async def test_cross_user_update_and_retry_delete_fail_closed() -> None:
    repository = _FakeRepository()
    other_actor = ActorContext(user_id="owner-2")

    with pytest.raises(HealthRecordNotFound):
        await UpdateHealthRecord(repository).execute(
            other_actor,
            "record-1",
            HealthRecordPatch({"memo": "unauthorized-change"}),
        )
    with pytest.raises(HealthRecordNotFound):
        await DeleteHealthRecord(repository).execute(other_actor, "record-1")

    assert repository.records["record-1"].memo == "initial"
    assert repository.unauthorized_write_attempts == 2
    assert repository.unauthorized_writes == 0
