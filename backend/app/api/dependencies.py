from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from jose import jwt, JWTError
from app.db.connection import get_users_collection
from app.config import settings
from bson import ObjectId
from bson.errors import InvalidId

security = HTTPBearer()


@dataclass(frozen=True, slots=True)
class ActorContext:
    """Trusted request actor and the resources already bound to that actor."""

    user_id: str
    room_id: str | None = None
    session_id: str | None = None
    health_record_id: str | None = None


def get_request_user_id(request: Request) -> str:
    """Return the JWT subject populated by AuthenticationMiddleware."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 정보가 없습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return str(user_id)


def require_user_match(requested_user_id: str | None, current_user_id: str) -> None:
    """Reject caller-supplied identities that differ from the JWT subject."""
    if requested_user_id and requested_user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: user mismatch")

async def get_current_user(credentials = Depends(security)) -> str:
    """
    JWT 토큰을 검증하고 사용자 ID를 반환합니다.
    
    Args:
        credentials: Bearer 토큰
        
    Returns:
        str: 사용자 ID (MongoDB _id)
        
    Raises:
        HTTPException: 토큰이 유효하지 않은 경우
    """
    token = credentials.credentials
    
    try:
        if not settings.secret_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="인증 정보를 확인할 수 없습니다",
            )

        # JWT 토큰 디코딩
        payload = jwt.decode(
            token, 
            settings.secret_key,
            algorithms=["HS256"]
        )
        user_id: str = payload.get("user_id")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 인증 토큰입니다"
            )
            
        return user_id
        
    except HTTPException:
        raise
    except (JWTError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰 검증에 실패했습니다"
        )


async def get_actor_context(user_id: str = Depends(get_current_user)) -> ActorContext:
    """Build a trusted actor from the verified JWT subject."""
    return ActorContext(user_id=str(user_id))


async def authorize_chat_actor(
    request: Request,
    context_system: Any,
    *,
    requested_user_id: str | None,
    room_id: str | None,
    session_id: str | None,
) -> ActorContext:
    """Bind room/session identifiers to the JWT subject before downstream calls."""
    user_id = get_request_user_id(request)
    require_user_match(requested_user_id, user_id)

    owned_room = None
    if room_id:
        db_manager = context_system.context_engineer.db_manager
        await db_manager.connect()
        database = db_manager.db
        collection = database["chat_rooms"]
        owned_room = await collection.find_one(
            {"room_id": room_id, "user_id": user_id, "is_deleted": False}
        )
        if not owned_room:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    session = None
    if session_id and session_id != "default":
        session = context_system.session_manager.get_session(session_id)
        # Persisted rooms survive process restarts while SessionManager is only
        # an in-memory accelerator. The canonical client uses room_id as the
        # compatibility session identifier, so Mongo ownership is sufficient
        # when that cache entry is absent.
        if not session and not (owned_room and session_id == room_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        if session and str(session.get("user_id")) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: session ownership mismatch",
            )

        if room_id and session and session.get("room_id") not in {None, room_id}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: session room mismatch",
            )

    return ActorContext(user_id=user_id, room_id=room_id, session_id=session_id)


async def require_admin(user_id: str = Depends(get_current_user)) -> str:
    """
    관리자 권한을 확인합니다.

    Args:
        user_id: JWT 토큰에서 추출한 사용자 ID

    Returns:
        str: 관리자 사용자 ID

    Raises:
        HTTPException: 관리자가 아닌 경우
    """
    try:
        user_object_id = ObjectId(user_id)
    except (InvalidId, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 토큰입니다",
        )

    user = await get_users_collection().find_one({"_id": user_object_id})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )

    # role이 없는 기존 사용자는 일반 사용자로 간주
    if user.get("role", "user") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다"
        )

    return user_id
