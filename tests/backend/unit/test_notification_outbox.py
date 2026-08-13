from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.models.notification import NotificationCreate
from app.services import notification_service


class _Cursor:
    def __init__(self, events):
        self.events = events

    def sort(self, *_args):
        return self

    def limit(self, _limit):
        return self

    async def to_list(self, length):
        return self.events[:length]


class _OutboxCollection:
    def __init__(self, events=None):
        self.events = events or []
        self.inserted = []
        self.updates = []

    async def insert_one(self, document):
        self.inserted.append(document)
        return SimpleNamespace(inserted_id="outbox-1")

    def find(self, _query):
        return _Cursor(self.events)

    async def update_one(self, query, update):
        self.updates.append((query, update))
        return SimpleNamespace(modified_count=1, matched_count=1)


@pytest.mark.asyncio
async def test_failed_notification_is_recorded_for_retry(monkeypatch):
    outbox = _OutboxCollection()
    monkeypatch.setattr(notification_service, "get_notification_outbox_collection", lambda: outbox)
    notification = NotificationCreate(
        user_id="user-1",
        type="community_like",
        message="좋아요",
        link="/community/detail/post-1",
    )

    await notification_service.record_notification_failure(notification, "provider unavailable")

    assert outbox.inserted[0]["status"] == "pending"
    assert outbox.inserted[0]["payload"]["user_id"] == "user-1"
    assert outbox.inserted[0]["last_error"] == "provider unavailable"


@pytest.mark.asyncio
async def test_pending_notification_is_retried_and_marked_delivered(monkeypatch):
    notification = NotificationCreate(
        user_id="user-1",
        type="community_reply",
        message="댓글",
    )
    outbox = _OutboxCollection([{
        "_id": "outbox-1",
        "payload": notification.model_dump(),
        "status": "pending",
        "attempts": 0,
        "next_attempt_at": notification_service.datetime.utcnow(),
        "event_id": "event-1",
    }])
    delivered = []
    monkeypatch.setattr(notification_service, "get_notification_outbox_collection", lambda: outbox)

    async def fake_create(payload, idempotency_key=None):
        delivered.append(payload)
        return "notification-1"

    monkeypatch.setattr(notification_service, "create_notification", fake_create)

    assert await notification_service.retry_pending_notifications() == 1
    assert delivered[0].user_id == "user-1"
    assert outbox.updates[-1][1]["$set"]["status"] == "delivered"


@pytest.mark.asyncio
async def test_retry_limit_moves_event_to_terminal_failed(monkeypatch):
    notification = NotificationCreate(user_id="user-1", type="community_reply", message="댓글")
    outbox = _OutboxCollection([{
        "_id": "outbox-2",
        "payload": notification.model_dump(),
        "status": "pending",
        "attempts": notification_service.OUTBOX_RETRY_LIMIT - 1,
        "next_attempt_at": notification_service.datetime.utcnow(),
        "event_id": "event-2",
    }])
    monkeypatch.setattr(notification_service, "get_notification_outbox_collection", lambda: outbox)

    async def fail_create(_payload, idempotency_key=None):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(notification_service, "create_notification", fail_create)

    assert await notification_service.retry_pending_notifications() == 0
    failed = outbox.updates[-1][1]["$set"]
    assert failed["status"] == "failed"
    assert failed["attempts"] == notification_service.OUTBOX_RETRY_LIMIT
    assert "failed_at" in failed
