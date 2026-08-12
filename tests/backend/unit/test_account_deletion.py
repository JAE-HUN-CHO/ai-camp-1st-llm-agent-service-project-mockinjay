from pathlib import Path
import sys

import pytest
from fastapi import HTTPException
from bson import ObjectId

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.api import auth_enhanced
from app.models.auth_enhanced import DeleteAccountRequest


class _Result:
    def __init__(self, *, matched_count: int = 1, deleted_count: int = 1):
        self.matched_count = matched_count
        self.deleted_count = deleted_count


class _Collection:
    def __init__(self, name: str, events: list[tuple], fail_on: str | None = None):
        self.name = name
        self.events = events
        self.fail_on = fail_on

    async def update_one(self, query, update, **kwargs):
        self.events.append(("update_one", self.name, query, update))
        if self.fail_on == "update_one":
            raise RuntimeError("update failed")
        return _Result()

    async def update_many(self, query, update, **kwargs):
        self.events.append(("update_many", self.name, query, update))
        if self.fail_on == "update_many":
            raise RuntimeError("update failed")
        return _Result(deleted_count=0)

    async def delete_many(self, query, **kwargs):
        self.events.append(("delete_many", self.name, query))
        if self.fail_on == "delete_many":
            raise RuntimeError("delete failed")
        return _Result(deleted_count=0)

    async def delete_one(self, query, **kwargs):
        self.events.append(("delete_one", self.name, query))
        if self.fail_on == "delete_one":
            raise RuntimeError("delete failed")
        return _Result()


class _Database:
    def __init__(self, events: list[tuple], fail_collection: str | None = None):
        self.collections = {
            name: _Collection(
                name,
                events,
                fail_on="delete_many" if name == fail_collection else None,
            )
            for name, _fields in auth_enhanced._USER_OWNED_COLLECTIONS
        }
        for name in ("posts", "comments", "likes", "post_anonymous_users"):
            self.collections[name] = _Collection(
                name,
                events,
                fail_on="delete_many" if name == fail_collection else None,
            )

    def __getitem__(self, name: str):
        return self.collections[name]


@pytest.mark.asyncio
async def test_user_owned_cleanup_uses_canonical_collections_and_fields():
    events: list[tuple] = []
    database = _Database(events)
    user_id = "507f1f77bcf86cd799439011"

    await auth_enhanced._delete_user_owned_data(database, user_id)

    deleted_collections = {event[1] for event in events if event[0] == "delete_many"}
    assert "chat_rooms" in deleted_collections
    assert "conversation_history" in deleted_collections
    assert "rooms" not in deleted_collections
    assert "conversations" not in deleted_collections

    bookmark_event = next(
        event
        for event in events
        if event[0] == "delete_many" and event[1] == "bookmarks"
    )
    assert {"userId", "user_id"} == {
        next(iter(condition)) for condition in bookmark_event[2]["$or"]
    }

    posts_event = next(
        event
        for event in events
        if event[0] == "update_many" and event[1] == "posts"
    )
    assert posts_event[3]["$set"] == {
        "isDeleted": True,
        "userId": "deleted_user",
    }


@pytest.mark.asyncio
async def test_delete_account_deletes_identity_last_and_marks_progress(monkeypatch):
    events: list[tuple] = []
    users = _Collection("users", events)
    database = _Database(events)
    monkeypatch.setattr(auth_enhanced, "get_users_collection", lambda: users)
    monkeypatch.setattr(auth_enhanced, "verify_password", lambda *_args: True)
    monkeypatch.setattr("app.db.connection.db", database)

    response = await auth_enhanced.delete_account(
        DeleteAccountRequest(password="password", confirmation="DELETE"),
        {"_id": ObjectId("507f1f77bcf86cd799439011"), "password": "hashed"},
    )

    assert response.success is True
    user_events = [event for event in events if event[1] == "users"]
    assert user_events[0][0] == "update_one"
    assert user_events[0][3]["$set"]["deletion_status"] == "in_progress"
    assert user_events[-1][0] == "delete_one"
    assert events.index(user_events[-1]) > events.index(user_events[0])


@pytest.mark.asyncio
async def test_delete_account_records_failure_for_retry(monkeypatch):
    events: list[tuple] = []
    users = _Collection("users", events)
    database = _Database(events, fail_collection="conversation_history")
    monkeypatch.setattr(auth_enhanced, "get_users_collection", lambda: users)
    monkeypatch.setattr(auth_enhanced, "verify_password", lambda *_args: True)
    monkeypatch.setattr("app.db.connection.db", database)

    with pytest.raises(HTTPException) as error:
        await auth_enhanced.delete_account(
            DeleteAccountRequest(password="password", confirmation="DELETE"),
            {"_id": ObjectId("507f1f77bcf86cd799439011"), "password": "hashed"},
        )

    assert error.value.status_code == 500
    user_events = [event for event in events if event[1] == "users"]
    assert user_events[0][3]["$set"]["deletion_status"] == "in_progress"
    assert user_events[-1][0] == "update_one"
    assert user_events[-1][3]["$set"]["deletion_status"] == "failed"
    assert not any(event[0] == "delete_one" for event in user_events)
