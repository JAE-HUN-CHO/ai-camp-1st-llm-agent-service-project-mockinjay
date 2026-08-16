"""Frozen REST v1 contract for the active Health Records slice."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo import ReturnDocument
import pytest

from app.api import user_health_records
from app.api.dependencies import get_actor_context
from app.bootstrap import container as container_module
from app.bootstrap.container import build_health_records_container
from app.core.actor import ActorContext


FIXTURE = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "health-records-v1-contract.json").read_text(
        encoding="utf-8"
    )
)
RECORD_ID = "507f1f77bcf86cd799439011"


class _Cursor:
    def __init__(self, documents: list[dict[str, object]]) -> None:
        self._documents = documents

    def sort(self, field: str, direction: int) -> _Cursor:
        reverse = direction == -1
        self._documents.sort(key=lambda document: str(document[field]), reverse=reverse)
        return self

    def __aiter__(self) -> _Cursor:
        self._index = 0
        return self

    async def __anext__(self) -> dict[str, object]:
        if self._index >= len(self._documents):
            raise StopAsyncIteration
        document = self._documents[self._index]
        self._index += 1
        return deepcopy(document)


class _Result:
    def __init__(self, *, inserted_id: ObjectId | None = None, deleted_count: int = 0) -> None:
        self.inserted_id = inserted_id
        self.deleted_count = deleted_count


class _Collection:
    def __init__(self) -> None:
        self.documents: dict[str, dict[str, object]] = {
            RECORD_ID: {
                "_id": ObjectId(RECORD_ID),
                "user_id": "actor-1",
                "date": "2026-08-16",
                "hospital": "Synthetic Clinic",
                "creatinine": 1.2,
                "gfr": 62.0,
            }
        }
        self.mutation_queries: list[dict[str, object]] = []

    def find(self, query: dict[str, object]) -> _Cursor:
        return _Cursor(
            [
                document
                for document in self.documents.values()
                if document.get("user_id") == query.get("user_id")
            ]
        )

    async def insert_one(self, document: dict[str, object]) -> _Result:
        object_id = ObjectId("507f1f77bcf86cd799439012")
        self.documents[str(object_id)] = {"_id": object_id, **deepcopy(document)}
        return _Result(inserted_id=object_id)

    async def find_one(self, query: dict[str, object]) -> dict[str, object] | None:
        document = self.documents.get(str(query["_id"]))
        if document and document.get("user_id") == query.get("user_id"):
            return deepcopy(document)
        return None

    async def update_one(
        self, query: dict[str, object], update: dict[str, dict[str, object]]
    ) -> _Result:
        self.mutation_queries.append(deepcopy(query))
        document = self.documents[str(query["_id"])]
        document.update(deepcopy(update["$set"]))
        return _Result()

    async def find_one_and_update(
        self,
        query: dict[str, object],
        update: dict[str, dict[str, object]],
        *,
        return_document,
    ) -> dict[str, object] | None:
        document = await self.find_one(query)
        if document is None:
            return None
        previous = deepcopy(document)
        self.mutation_queries.append(deepcopy(query))
        self.documents[str(query["_id"])].update(deepcopy(update["$set"]))
        if return_document is ReturnDocument.BEFORE:
            return previous
        return deepcopy(self.documents[str(query["_id"])])

    async def delete_one(self, query: dict[str, object]) -> _Result:
        self.mutation_queries.append(deepcopy(query))
        document = self.documents.get(str(query["_id"]))
        if document is None or document.get("user_id") != query.get("user_id"):
            return _Result(deleted_count=0)
        del self.documents[str(query["_id"])]
        return _Result(deleted_count=1)


def _client(
    monkeypatch,
    collection: _Collection,
    actor_id: str = "actor-1",
    implementation: str = "legacy",
) -> TestClient:
    app = FastAPI()
    app.include_router(user_health_records.router)
    app.dependency_overrides[get_actor_context] = lambda: ActorContext(user_id=actor_id)
    monkeypatch.setattr(container_module, "get_health_records_collection", lambda: collection)
    app.state.health_records_container = build_health_records_container(
        environment={"HEALTH_RECORDS_IMPLEMENTATION": implementation}
    )
    return TestClient(app)


def _assert_record_response(response, route_key: str) -> None:
    assert response.status_code == FIXTURE["routes"][route_key]["status"]
    assert response.headers["content-type"].startswith(FIXTURE["content_type"])
    assert sorted(response.json()) == FIXTURE["record_keys"]


@pytest.mark.parametrize("implementation", ["legacy", "hex"])
def test_frozen_health_records_v1_crud_contract(monkeypatch, implementation: str) -> None:
    collection = _Collection()
    client = _client(monkeypatch, collection, implementation=implementation)

    listed = client.get(FIXTURE["route_prefix"] + FIXTURE["routes"]["list"]["path"])
    assert listed.status_code == FIXTURE["routes"]["list"]["status"]
    assert len(listed.json()) == 1
    assert sorted(listed.json()[0]) == FIXTURE["record_keys"]

    created = client.post(
        FIXTURE["route_prefix"] + FIXTURE["routes"]["create"]["path"],
        json={
            "date": "2026-08-17",
            "hospital": "Synthetic Clinic",
            "creatinine": 1.1,
            "gfr": 64.0,
        },
    )
    _assert_record_response(created, "create")

    updated = client.put(
        FIXTURE["route_prefix"] + FIXTURE["routes"]["update"]["path"].replace("{record_id}", RECORD_ID),
        json={"memo": None, "gfr": 63.0}
    )
    _assert_record_response(updated, "update")
    assert updated.json()["memo"] is None
    assert updated.json()["gfr"] == 63.0
    assert updated.json()["date"] == "2026-08-16"

    deleted = client.delete(FIXTURE["route_prefix"] + FIXTURE["routes"]["delete"]["path"].replace("{record_id}", RECORD_ID))
    assert deleted.status_code == FIXTURE["routes"]["delete"]["status"]
    assert deleted.json() == FIXTURE["delete_payload"]


@pytest.mark.parametrize("implementation", ["legacy", "hex"])
def test_frozen_health_records_v1_error_and_owner_contract(
    monkeypatch, implementation: str
) -> None:
    collection = _Collection()
    owner_client = _client(monkeypatch, collection, implementation=implementation)

    invalid = owner_client.put("/api/health-records/not-an-id", json={"memo": None})
    assert invalid.status_code == FIXTURE["errors"]["invalid_or_unowned_id"]["status"]
    assert invalid.json()["detail"] == FIXTURE["errors"]["invalid_or_unowned_id"]["detail"]

    empty = owner_client.put(f"/api/health-records/{RECORD_ID}", json={})
    assert empty.status_code == FIXTURE["errors"]["empty_update"]["status"]
    assert empty.json()["detail"] == FIXTURE["errors"]["empty_update"]["detail"]

    other_client = _client(
        monkeypatch, collection, actor_id="actor-2", implementation=implementation
    )
    denied = other_client.put(
        f"/api/health-records/{RECORD_ID}", json={"memo": "must-not-write"}
    )
    assert denied.status_code == FIXTURE["errors"]["invalid_or_unowned_id"]["status"]
    assert collection.mutation_queries == []
    assert "memo" not in collection.documents[RECORD_ID]
