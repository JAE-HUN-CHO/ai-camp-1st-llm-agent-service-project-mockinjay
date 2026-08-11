"""Authenticated room CRUD/history smoke against the local Mongo runtime."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.api.dependencies import get_current_user
from app.api.rooms import router
from app.core.context_system import ContextSystem
from app.db.context_manager import ContextManager

pytestmark = pytest.mark.integration


@pytest.fixture()
def live_client() -> tuple[TestClient, str, ContextSystem]:
    uri = os.getenv("MONGODB_URI")
    if not uri:
        pytest.skip("MONGODB_URI is required for the live Mongo integration smoke")

    user_id = f"e2e-room-{uuid4().hex}"
    context_system = ContextSystem()
    context_system.context_engineer.db_manager = ContextManager(
        uri=uri,
        db_name=os.getenv("DB_NAME", "careguide"),
    )

    app = FastAPI()
    app.state.context_system = context_system
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: user_id
    try:
        with TestClient(app) as client:
            yield client, user_id, context_system
    finally:
        # The test uses a unique subject and removes only its own records.
        mongo = MongoClient(uri, serverSelectionTimeoutMS=3000)
        try:
            database = mongo[os.getenv("DB_NAME", "careguide")]
            database.chat_rooms.delete_many({"user_id": user_id})
            database.conversation_history.delete_many({"user_id": user_id})
        finally:
            mongo.close()
        if context_system.context_engineer.db_manager.client:
            context_system.context_engineer.db_manager.client.close()


def test_room_crud_and_history_use_authenticated_owner(live_client: tuple[TestClient, str, ContextSystem]) -> None:
    client, user_id, _ = live_client

    created = client.post(
        "/api/rooms",
        json={"user_id": user_id, "room_name": "Live smoke", "metadata": {"source": "e2e"}},
    )
    assert created.status_code == 201, created.text
    room = created.json()["data"]
    room_id = room["room_id"]

    listed = client.get(f"/api/rooms?user_id={user_id}")
    assert listed.status_code == 200, listed.text
    assert listed.json()["data"]["total"] == 1
    assert listed.json()["data"]["rooms"][0]["room_id"] == room_id

    uri = os.environ["MONGODB_URI"]
    mongo = MongoClient(uri, serverSelectionTimeoutMS=3000)
    try:
        mongo[os.getenv("DB_NAME", "careguide")].conversation_history.insert_one(
            {
                "user_id": user_id,
                "room_id": room_id,
                "session_id": room_id,
                "agent_type": "test",
                "user_input": "hello",
                "agent_response": "world",
                "timestamp": datetime.now(timezone.utc),
            }
        )
    finally:
        mongo.close()

    detail = client.get(f"/api/rooms/{room_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["data"]["message_count"] == 1

    updated = client.patch(
        f"/api/rooms/{room_id}?user_id={user_id}",
        json={"room_name": "Renamed"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["room_name"] == "Renamed"

    history = client.get(f"/api/rooms/{room_id}/history")
    assert history.status_code == 200, history.text
    assert history.json()["data"]["conversations"][0]["user_input"] == "hello"

    deleted = client.delete(f"/api/rooms/{room_id}?user_id={user_id}")
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["data"]["conversations_deleted"] == 1
    assert client.get(f"/api/rooms/{room_id}").status_code == 404
