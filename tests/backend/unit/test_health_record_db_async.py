"""Regression tests for the Motor boundary in health-record endpoints."""

from datetime import datetime

import pytest
from fastapi import HTTPException

from app.api import user_health_records
from app.bootstrap import container as container_module
from app.bootstrap.container import HealthRecordsContainer, build_health_records_container
from app.core.actor import ActorContext
from app.models.user_health_record import HealthRecordCreate, HealthRecordUpdate


class _AsyncInsertResult:
    inserted_id = "507f1f77bcf86cd799439011"


class _AsyncDeleteResult:
    deleted_count = 1


class _FakeHealthRecords:
    def __init__(self) -> None:
        self.mutation_queries = []
        self.documents = {
            "507f1f77bcf86cd799439011": {
                "_id": "507f1f77bcf86cd799439011",
                "user_id": "user-1",
                "date": "2026-08-12",
                "hospital": "Local Clinic",
                "creatinine": 1.2,
                "gfr": 62.0,
                "created_at": datetime.utcnow(),
            }
        }

    async def insert_one(self, document):
        self.documents[_AsyncInsertResult.inserted_id] = {
            "_id": _AsyncInsertResult.inserted_id,
            **document,
        }
        return _AsyncInsertResult()

    async def find_one(self, query):
        document = self.documents.get(str(query["_id"]))
        if document and query.get("user_id") == document.get("user_id"):
            return document
        return None

    async def update_one(self, query, update):
        self.mutation_queries.append(query)
        document = self.documents[str(query["_id"])]
        assert query["user_id"] == document["user_id"]
        document.update(update["$set"])

    async def delete_one(self, query):
        self.mutation_queries.append(query)
        document = self.documents.get(str(query["_id"]))
        if not document or query.get("user_id") != document.get("user_id"):
            return type("Result", (), {"deleted_count": 0})()
        self.documents.pop(str(query["_id"]), None)
        return _AsyncDeleteResult()


def _legacy_container(
    monkeypatch, collection: _FakeHealthRecords
) -> HealthRecordsContainer:
    monkeypatch.setattr(container_module, "get_health_records_collection", lambda: collection)
    return build_health_records_container(environment={})


@pytest.mark.asyncio
async def test_create_health_record_awaits_motor_insert(monkeypatch) -> None:
    collection = _FakeHealthRecords()
    container = _legacy_container(monkeypatch, collection)

    response = await user_health_records.create_health_record(
        HealthRecordCreate(
            date="2026-08-12",
            hospital="Local Clinic",
            creatinine=1.2,
            gfr=62.0,
        ),
        actor=ActorContext(user_id="user-1"),
        container=container,
    )

    assert response["id"] == _AsyncInsertResult.inserted_id
    assert collection.documents[_AsyncInsertResult.inserted_id]["user_id"] == "user-1"


@pytest.mark.asyncio
async def test_update_and_delete_health_record_await_motor_operations(monkeypatch) -> None:
    collection = _FakeHealthRecords()
    container = _legacy_container(monkeypatch, collection)
    record_id = "507f1f77bcf86cd799439011"

    updated = await user_health_records.update_health_record(
        record_id,
        HealthRecordUpdate(memo=None),
        actor=ActorContext(user_id="user-1"),
        container=container,
    )
    deleted = await user_health_records.delete_health_record(
        record_id, actor=ActorContext(user_id="user-1"), container=container
    )

    assert updated["memo"] is None
    assert deleted["success"] is True
    assert record_id not in collection.documents
    assert all(query["user_id"] == "user-1" for query in collection.mutation_queries)


@pytest.mark.asyncio
async def test_cross_user_health_update_has_zero_mutations(monkeypatch) -> None:
    collection = _FakeHealthRecords()
    container = _legacy_container(monkeypatch, collection)

    with pytest.raises(HTTPException) as exc:
        await user_health_records.update_health_record(
            "507f1f77bcf86cd799439011",
            HealthRecordUpdate(memo="unauthorized"),
            actor=ActorContext(user_id="user-2"),
            container=container,
        )

    assert getattr(exc.value, "status_code", None) == 404
    assert collection.mutation_queries == []
    assert collection.documents["507f1f77bcf86cd799439011"].get("memo") is None
