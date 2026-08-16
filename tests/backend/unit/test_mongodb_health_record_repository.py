"""Contract tests for the Phase 3A MongoDB Health Record adapter."""

from __future__ import annotations

from copy import deepcopy

import pytest
from bson import ObjectId
from pymongo import ReturnDocument

from app.adapters.mongodb.health_record_repository import MongoHealthRecordRepository
from app.features.health.domain import HealthRecordDraft, HealthRecordPatch


RECORD_ID = "507f1f77bcf86cd799439011"


class _Cursor:
    def __init__(self, documents: list[dict[str, object]]) -> None:
        self.documents = documents
        self.sort_call: tuple[str, int] | None = None

    def sort(self, field: str, direction: int) -> "_Cursor":
        self.sort_call = (field, direction)
        self.documents.sort(key=lambda item: str(item[field]), reverse=direction == -1)
        return self

    def __aiter__(self) -> "_Cursor":
        self.index = 0
        return self

    async def __anext__(self) -> dict[str, object]:
        if self.index >= len(self.documents):
            raise StopAsyncIteration
        value = deepcopy(self.documents[self.index])
        self.index += 1
        return value


class _Collection:
    def __init__(self) -> None:
        self.documents = {
            RECORD_ID: {
                "_id": ObjectId(RECORD_ID),
                "user_id": "owner-1",
                "date": "2026-08-16",
                "hospital": "Synthetic Clinic",
                "creatinine": 1.2,
                "gfr": 62.0,
                "memo": "existing",
            }
        }
        self.queries: list[tuple[str, dict[str, object]]] = []
        self.update_payloads: list[dict[str, object]] = []
        self.last_cursor: _Cursor | None = None

    def find(self, query: dict[str, object]) -> _Cursor:
        self.queries.append(("find", deepcopy(query)))
        self.last_cursor = _Cursor(
            [
                document
                for document in self.documents.values()
                if document["user_id"] == query.get("user_id")
            ]
        )
        return self.last_cursor

    async def insert_one(self, document: dict[str, object]):
        self.queries.append(("insert", {"user_id": document["user_id"]}))
        object_id = ObjectId("507f1f77bcf86cd799439012")
        self.documents[str(object_id)] = {"_id": object_id, **deepcopy(document)}
        return type("InsertResult", (), {"inserted_id": object_id})()

    async def find_one(self, query: dict[str, object]):
        self.queries.append(("find_one", deepcopy(query)))
        document = self.documents.get(str(query["_id"]))
        if document and document["user_id"] == query.get("user_id"):
            return deepcopy(document)
        return None

    async def find_one_and_update(
        self,
        query: dict[str, object],
        update: dict[str, dict[str, object]],
        *,
        return_document,
    ):
        self.queries.append(("update", deepcopy(query)))
        self.update_payloads.append(deepcopy(update))
        document = self.documents.get(str(query["_id"]))
        if document is None or document["user_id"] != query.get("user_id"):
            return None
        previous = deepcopy(document)
        document.update(deepcopy(update["$set"]))
        if return_document is ReturnDocument.BEFORE:
            return previous
        return deepcopy(document)

    async def delete_one(self, query: dict[str, object]):
        self.queries.append(("delete", deepcopy(query)))
        document = self.documents.get(str(query["_id"]))
        if document is None or document["user_id"] != query.get("user_id"):
            return type("DeleteResult", (), {"deleted_count": 0})()
        del self.documents[str(query["_id"])]
        return type("DeleteResult", (), {"deleted_count": 1})()


def _draft() -> HealthRecordDraft:
    return HealthRecordDraft(
        date="2026-08-17",
        hospital="Synthetic Clinic",
        creatinine=1.1,
        gfr=64.0,
    )


@pytest.mark.asyncio
async def test_mongodb_health_record_repository_preserves_collection_schema() -> None:
    collection = _Collection()
    repository = MongoHealthRecordRepository(lambda: collection)

    created = await repository.create("owner-1", _draft())
    stored = collection.documents[created.record_id]

    assert set(stored) == {
        "_id",
        "user_id",
        "date",
        "hospital",
        "creatinine",
        "gfr",
        "potassium",
        "phosphorus",
        "hemoglobin",
        "albumin",
        "pth",
        "hco3",
        "memo",
        "created_at",
    }
    assert stored["user_id"] == "owner-1"
    assert created.owner_id == "owner-1"


@pytest.mark.asyncio
async def test_mongodb_health_record_repository_scopes_every_resource_query() -> None:
    collection = _Collection()
    repository = MongoHealthRecordRepository(lambda: collection)

    listed = await repository.list_for_owner("owner-1")
    loaded = await repository.get(RECORD_ID, "owner-1")
    updated = await repository.update(
        RECORD_ID, "owner-1", HealthRecordPatch({"memo": None})
    )
    deleted = await repository.delete(RECORD_ID, "owner-1")

    assert [record.record_id for record in listed] == [RECORD_ID]
    assert loaded is not None
    assert updated is not None and updated.memo is None
    assert deleted is True
    assert collection.update_payloads == [{"$set": {"memo": None}}]
    assert collection.last_cursor is not None
    assert collection.last_cursor.sort_call == ("date", -1)
    assert all(
        query.get("user_id") == "owner-1"
        for operation, query in collection.queries
        if operation in {"find", "find_one", "update", "delete"}
    )


@pytest.mark.asyncio
async def test_mongodb_health_record_repository_cross_user_and_invalid_id_do_not_write() -> None:
    collection = _Collection()
    repository = MongoHealthRecordRepository(lambda: collection)

    wrong_owner = await repository.update(
        RECORD_ID, "owner-2", HealthRecordPatch({"memo": None})
    )
    invalid_update = await repository.update(
        "not-an-id", "owner-1", HealthRecordPatch({"memo": None})
    )
    invalid_delete = await repository.delete("not-an-id", "owner-1")

    assert wrong_owner is None
    assert invalid_update is None
    assert invalid_delete is False
    assert collection.documents[RECORD_ID]["memo"] == "existing"
    assert len([item for item in collection.queries if item[0] == "update"]) == 1
