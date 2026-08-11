"""Regression guard for the canonical quiz points ledger seam."""

import asyncio
import inspect
import sys
from datetime import datetime
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[3] / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.mypage.points_service import (
    POINTS_RESERVATION_TTL_SECONDS,
    PointsService,
)


def test_points_service_exposes_idempotency_key() -> None:
    parameter = inspect.signature(PointsService.add_points).parameters["idempotency_key"]

    assert parameter.default is None


def test_stale_reservations_are_expired_without_auto_awarding() -> None:
    class Result:
        modified_count = 2

    class History:
        def __init__(self) -> None:
            self.query = None
            self.update = None

        async def update_many(self, query, update):
            self.query = query
            self.update = update
            return Result()

    history = History()
    service = PointsService()
    service._points_history_collection = history
    now = datetime.utcnow()

    assert asyncio.run(service.expire_stale_reservations(now)) == 2
    assert history.query["status"] == "pending"
    assert history.query["createdAt"]["$lt"] < now
    assert history.update["$set"]["status"] == "expired"
    assert history.update["$set"]["expiredAt"] == now
    assert POINTS_RESERVATION_TTL_SECONDS == 300
