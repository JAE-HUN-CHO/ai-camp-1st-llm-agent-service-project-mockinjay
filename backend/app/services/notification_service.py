"""알림 서비스 비즈니스 로직과 실패 알림 outbox 처리."""
import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from bson import ObjectId
from app.db.connection import (
    get_notification_outbox_collection,
    get_notifications_collection,
    get_notification_settings_collection,
)
from app.models.notification import NotificationCreate

logger = logging.getLogger(__name__)

OUTBOX_RETRY_LIMIT = 8
OUTBOX_MAX_BACKOFF_SECONDS = 3600


async def create_notification(notification: NotificationCreate) -> str:
    """
    새 알림 생성

    Args:
        notification: 알림 생성 데이터

    Returns:
        str: 생성된 알림 ID
    """
    notification_doc = {
        "user_id": notification.user_id,
        "type": notification.type,
        "message": notification.message,
        "link": notification.link,
        "read_status": notification.read_status,
        "created_at": datetime.utcnow()
    }

    result = await get_notifications_collection().insert_one(notification_doc)
    return str(result.inserted_id)


async def record_notification_failure(notification: NotificationCreate, error: str) -> None:
    """Persist a failed delivery so a later worker can retry it."""
    now = datetime.utcnow()
    await get_notification_outbox_collection().insert_one({
        "payload": notification.model_dump(),
        "status": "pending",
        "attempts": 0,
        "last_error": error[:1000],
        "created_at": now,
        "next_attempt_at": now,
    })


async def retry_pending_notifications(limit: int = 20) -> int:
    """Retry due outbox events once and return the number delivered."""
    now = datetime.utcnow()
    collection = get_notification_outbox_collection()
    cursor = collection.find({
        "status": "pending",
        "next_attempt_at": {"$lte": now},
        "attempts": {"$lt": OUTBOX_RETRY_LIMIT},
    }).sort("created_at", 1).limit(limit)
    events = await cursor.to_list(length=limit)
    delivered = 0
    for event in events:
        payload = NotificationCreate.model_validate(event["payload"])
        attempts = int(event.get("attempts", 0)) + 1
        try:
            await create_notification(payload)
        except Exception as exc:
            backoff = min(2 ** attempts, OUTBOX_MAX_BACKOFF_SECONDS)
            await collection.update_one(
                {"_id": event["_id"]},
                {"$set": {
                    "status": "pending",
                    "attempts": attempts,
                    "last_error": str(exc)[:1000],
                    "next_attempt_at": datetime.utcnow() + timedelta(seconds=backoff),
                    "backoff_seconds": backoff,
                }},
            )
            logger.warning("Notification outbox retry failed: %s", exc)
            continue
        await collection.update_one(
            {"_id": event["_id"]},
            {"$set": {
                "status": "delivered",
                "attempts": attempts,
                "delivered_at": datetime.utcnow(),
            }},
        )
        delivered += 1
    return delivered


async def run_notification_outbox_worker(
    stop_event: asyncio.Event,
    interval_seconds: float = 30.0,
) -> None:
    """Run bounded periodic retries until application shutdown."""
    while not stop_event.is_set():
        try:
            await retry_pending_notifications()
        except Exception:
            logger.exception("Notification outbox worker iteration failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except TimeoutError:
            continue


async def get_user_notifications(user_id: str, page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
    """
    사용자의 알림 목록 조회 (페이지네이션)

    Args:
        user_id: 사용자 ID
        page: 페이지 번호 (1부터 시작)
        page_size: 페이지당 항목 수

    Returns:
        List[Dict]: 알림 목록
    """
    skip = (page - 1) * page_size

    cursor = get_notifications_collection().find(
        {"user_id": user_id}
    ).sort("created_at", -1).skip(skip).limit(page_size)

    notifications = await cursor.to_list(length=page_size)

    result = []
    for notif in notifications:
        result.append({
            "id": str(notif["_id"]),
            "user_id": notif["user_id"],
            "type": notif["type"],
            "message": notif["message"],
            "link": notif.get("link"),
            "read_status": notif["read_status"],
            "created_at": notif["created_at"]
        })

    return result


async def get_unread_count(user_id: str) -> int:
    """
    사용자의 읽지 않은 알림 개수 조회

    Args:
        user_id: 사용자 ID

    Returns:
        int: 읽지 않은 알림 개수
    """
    count = await get_notifications_collection().count_documents({
        "user_id": user_id,
        "read_status": False
    })

    return count


async def mark_as_read(notification_id: str, user_id: str) -> bool:
    """
    알림을 읽음으로 표시

    Args:
        notification_id: 알림 ID
        user_id: 사용자 ID (권한 확인용)

    Returns:
        bool: 성공 여부
    """
    result = await get_notifications_collection().update_one(
        {
            "_id": ObjectId(notification_id),
            "user_id": user_id
        },
        {"$set": {"read_status": True}}
    )

    return result.modified_count > 0


async def delete_all_notifications(user_id: str) -> int:
    """
    사용자의 모든 알림 삭제

    Args:
        user_id: 사용자 ID

    Returns:
        int: 삭제된 알림 개수
    """
    result = await get_notifications_collection().delete_many({"user_id": user_id})
    return result.deleted_count


async def get_notification_settings(user_id: str) -> Dict[str, Any]:
    """
    사용자의 알림 설정 조회

    Args:
        user_id: 사용자 ID

    Returns:
        Dict: 알림 설정
    """
    settings = await get_notification_settings_collection().find_one({"user_id": user_id})

    if not settings:
        # 기본 설정 생성 (모두 ON)
        default_settings = {
            "user_id": user_id,
            "quiz_notification": True,
            "community_reply_notification": True,
            "community_like_notification": True,
            "survey_notification": True,
            "challenge_notification": True,
            "level_up_notification": True,
            "point_notification": True,
            "update_notification": True
        }
        await get_notification_settings_collection().insert_one(default_settings)
        settings = default_settings

    return {
        "user_id": settings["user_id"],
        "quiz_notification": settings.get("quiz_notification", True),
        "community_reply_notification": settings.get("community_reply_notification", True),
        "community_like_notification": settings.get("community_like_notification", True),
        "survey_notification": settings.get("survey_notification", True),
        "challenge_notification": settings.get("challenge_notification", True),
        "level_up_notification": settings.get("level_up_notification", True),
        "point_notification": settings.get("point_notification", True),
        "update_notification": settings.get("update_notification", True)
    }


async def update_notification_settings(user_id: str, settings_update: Dict[str, bool]) -> bool:
    """
    사용자의 알림 설정 업데이트

    Args:
        user_id: 사용자 ID
        settings_update: 업데이트할 설정 (필드명: 값)

    Returns:
        bool: 성공 여부
    """
    # 기존 설정이 없으면 생성
    existing = await get_notification_settings_collection().find_one({"user_id": user_id})

    if not existing:
        default_settings = {
            "user_id": user_id,
            "quiz_notification": True,
            "community_reply_notification": True,
            "community_like_notification": True,
            "survey_notification": True,
            "challenge_notification": True,
            "level_up_notification": True,
            "point_notification": True,
            "update_notification": True
        }
        await get_notification_settings_collection().insert_one(default_settings)

    # None이 아닌 값만 업데이트
    update_fields = {k: v for k, v in settings_update.items() if v is not None}

    if not update_fields:
        return False

    result = await get_notification_settings_collection().update_one(
        {"user_id": user_id},
        {"$set": update_fields}
    )

    return result.modified_count > 0 or result.matched_count > 0
