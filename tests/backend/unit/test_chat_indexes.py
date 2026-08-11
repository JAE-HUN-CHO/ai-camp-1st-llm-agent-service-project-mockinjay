"""Regression guard for room/history query indexes."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.db.indexes import create_chat_indexes


class _Collection:
    def __init__(self) -> None:
        self.calls = []

    async def create_indexes(self, indexes) -> None:
        self.calls.append(indexes)


class _Database:
    def __init__(self) -> None:
        self.collections = {"chat_rooms": _Collection(), "conversation_history": _Collection()}

    def __getitem__(self, name: str) -> _Collection:
        return self.collections[name]


@pytest.mark.asyncio
async def test_chat_indexes_cover_owner_sort_and_history_queries() -> None:
    database = _Database()

    await create_chat_indexes(database)

    room_indexes = database.collections["chat_rooms"].calls[0]
    history_indexes = database.collections["conversation_history"].calls[0]
    assert {index.document["name"] for index in room_indexes} == {
        "idx_chat_rooms_user_deleted_activity",
        "idx_chat_rooms_room_owner_deleted",
    }
    assert {index.document["name"] for index in history_indexes} == {
        "idx_conversation_history_room_timestamp",
        "idx_conversation_history_user_timestamp",
    }
