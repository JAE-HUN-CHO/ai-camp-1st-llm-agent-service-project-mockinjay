"""HTTP contract checks for room ownership with an injected local fake store."""

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.api.dependencies import get_current_user
from app.api.rooms import router
from app.core.context_system import context_system

pytestmark = pytest.mark.integration


class _FakeRooms:
    def __init__(self) -> None:
        self.documents: list[dict] = []

    async def count_documents(self, query: dict) -> int:
        return sum(
            document.get("user_id") == query.get("user_id")
            and document.get("is_deleted") is query.get("is_deleted")
            for document in self.documents
        )

    async def insert_one(self, document: dict) -> None:
        self.documents.append(document)


class _FakeDatabase:
    def __init__(self) -> None:
        self.chat_rooms = _FakeRooms()


class _FakeManager:
    def __init__(self) -> None:
        self.db = _FakeDatabase()

    async def connect(self) -> None:
        return None


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.state.context_system = context_system
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: "user-1"
    original_manager = context_system.context_engineer.db_manager
    context_system.context_engineer.db_manager = _FakeManager()
    try:
        yield TestClient(app)
    finally:
        context_system.context_engineer.db_manager = original_manager
        app.dependency_overrides.clear()


def test_room_create_rejects_caller_owned_by_another_user(client: TestClient) -> None:
    response = client.post("/api/rooms", json={"user_id": "user-2", "room_name": "private"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied: user mismatch"


def test_room_create_persists_under_authenticated_subject(client: TestClient) -> None:
    response = client.post("/api/rooms", json={"user_id": "user-1", "room_name": "private"})

    assert response.status_code == 201
    assert response.json()["data"]["user_id"] == "user-1"
