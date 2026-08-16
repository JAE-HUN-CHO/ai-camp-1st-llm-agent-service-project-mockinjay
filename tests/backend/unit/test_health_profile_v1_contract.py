"""Frozen REST v1 behavior for the active MyPage Health Profile endpoints."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path

from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from pymongo import ReturnDocument

from app.api import mypage
from app.bootstrap import container as container_module
from app.bootstrap.container import build_health_profile_container
from app.services.auth import get_current_user


FIXTURE = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "health-profile-v1-contract.json").read_text(
        encoding="utf-8"
    )
)
RESPONSE_KEYS = set(FIXTURE["response_keys"])


class _Result:
    def __init__(self, *, matched_count: int, upserted_id: ObjectId | None) -> None:
        self.matched_count = matched_count
        self.upserted_id = upserted_id


class _Collection:
    def __init__(self) -> None:
        self.documents: dict[str, dict[str, object]] = {}
        self.mutation_queries: list[dict[str, object]] = []
        self.error: Exception | None = None

    async def find_one(self, query: dict[str, object]) -> dict[str, object] | None:
        if self.error:
            raise self.error
        document = self.documents.get(str(query["userId"]))
        return deepcopy(document) if document else None

    async def update_one(
        self,
        query: dict[str, object],
        update: dict[str, dict[str, object]],
        *,
        upsert: bool,
    ) -> _Result:
        if self.error:
            raise self.error
        assert upsert is True
        owner_id = str(query["userId"])
        self.mutation_queries.append(deepcopy(query))
        document = self.documents.get(owner_id)
        matched_count = int(document is not None)
        if document is None:
            document = {"_id": ObjectId(), "userId": owner_id}
            self.documents[owner_id] = document
        document.update(deepcopy(update["$set"]))
        return _Result(
            matched_count=matched_count,
            upserted_id=None if matched_count else document["_id"],
        )

    async def find_one_and_update(
        self,
        query: dict[str, object],
        update: dict[str, dict[str, object]],
        *,
        upsert: bool,
        return_document: object,
    ) -> dict[str, object] | None:
        await self.update_one(query, update, upsert=upsert)
        assert return_document == ReturnDocument.AFTER
        document = self.documents.get(str(query["userId"]))
        return deepcopy(document) if document else None


def _client(
    collection: _Collection,
    implementation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[TestClient, dict[str, dict[str, ObjectId]]]:
    app = FastAPI()
    app.include_router(mypage.router)
    actor = {"value": {"_id": ObjectId("507f1f77bcf86cd799439011")}}

    async def _current_user() -> dict[str, ObjectId]:
        return actor["value"]

    app.dependency_overrides[get_current_user] = _current_user
    monkeypatch.setattr(
        container_module, "get_health_profiles_collection", lambda: collection
    )
    container = build_health_profile_container(
        environment={"HEALTH_PROFILE_IMPLEMENTATION": implementation}
    )
    if container.legacy is not None:
        container.legacy._service._health_profiles_collection = collection
    app.state.health_profile_container = container
    return TestClient(app), actor


def _assert_json_response(response, expected_status: int = 200) -> dict[str, object]:
    assert response.status_code == expected_status
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert isinstance(payload, dict)
    return payload


@pytest.mark.parametrize("implementation", ["legacy", "hex"])
def test_get_returns_frozen_default_payload(
    implementation: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    collection = _Collection()
    client, actor = _client(collection, implementation, monkeypatch)
    owner_id = str(actor["value"]["_id"])

    payload = _assert_json_response(client.get(FIXTURE["paths"]["get"]["path"]))

    assert set(payload) == RESPONSE_KEYS
    assert payload == {"userId": owner_id, **FIXTURE["default_values"]}
    assert collection.mutation_queries == []


@pytest.mark.parametrize("implementation", ["legacy", "hex"])
def test_update_preserves_keys_alias_and_null_unset_semantics(
    implementation: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    collection = _Collection()
    client, actor = _client(collection, implementation, monkeypatch)
    path = FIXTURE["paths"]["update"]["path"]
    owner_id = str(actor["value"]["_id"])

    update_payload = {
        "conditions": ["synthetic-condition"],
        "allergies": ["synthetic-allergy"],
        "dietaryRestrictions": ["synthetic-restriction"],
        "age": 44,
        "gender": "other",
    }
    assert set(update_payload) == set(FIXTURE["update_fields"])
    created = _assert_json_response(client.put(path, json=update_payload))
    assert set(created) == RESPONSE_KEYS
    assert created["userId"] == owner_id
    assert created["conditions"] == created["healthConditions"]
    assert isinstance(created["updatedAt"], str)
    datetime.fromisoformat(created["updatedAt"])

    explicit_null = _assert_json_response(client.put(path, json={"conditions": None}))
    empty_update = _assert_json_response(client.put(path, json={}))

    for payload in (explicit_null, empty_update):
        assert payload["conditions"] == ["synthetic-condition"]
        assert payload["healthConditions"] == ["synthetic-condition"]
        assert payload["age"] == 44
        assert payload["gender"] == "other"


@pytest.mark.parametrize("implementation", ["legacy", "hex"])
def test_owner_binding_keeps_cross_user_profiles_separate(
    implementation: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    collection = _Collection()
    client, actor = _client(collection, implementation, monkeypatch)
    path = FIXTURE["paths"]["update"]["path"]
    owner_a = str(actor["value"]["_id"])

    _assert_json_response(client.put(path, json={"age": 41}))
    actor["value"] = {"_id": ObjectId("507f1f77bcf86cd799439012")}
    owner_b = str(actor["value"]["_id"])
    default_b = _assert_json_response(client.get(path))
    assert default_b == {"userId": owner_b, **FIXTURE["default_values"]}
    _assert_json_response(client.put(path, json={"age": 52}))

    actor["value"] = {"_id": ObjectId(owner_a)}
    profile_a = _assert_json_response(client.get(path))
    assert profile_a["age"] == 41
    assert collection.documents[owner_b]["age"] == 52
    assert collection.mutation_queries == [{"userId": owner_a}, {"userId": owner_b}]


@pytest.mark.parametrize("implementation", ["legacy", "hex"])
def test_validation_status_is_frozen(
    implementation: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    collection = _Collection()
    client, _ = _client(collection, implementation, monkeypatch)
    path = FIXTURE["paths"]["update"]["path"]

    validation = FIXTURE["validation"]
    assert (
        client.put(path, json={"age": validation["age_minimum"] - 1}).status_code
        == validation["age_below_minimum_status"]
    )
    assert (
        client.put(path, json={"age": validation["age_maximum"] + 1}).status_code
        == validation["age_above_maximum_status"]
    )
    assert collection.mutation_queries == []


@pytest.mark.parametrize("implementation", ["legacy", "hex"])
@pytest.mark.parametrize(
    ("method", "contract_name"),
    [("get", "get_persistence"), ("put", "update_persistence")],
)
def test_persistence_error_payload_is_frozen(
    implementation: str,
    method: str,
    contract_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collection = _Collection()
    collection.error = RuntimeError("synthetic database failure")
    client, _ = _client(collection, implementation, monkeypatch)
    path = FIXTURE["paths"]["get"]["path"]

    response = (
        client.get(path) if method == "get" else client.put(path, json={"age": 44})
    )

    expected = FIXTURE["errors"][contract_name]
    assert response.status_code == expected["status"]
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": expected["detail"]}
