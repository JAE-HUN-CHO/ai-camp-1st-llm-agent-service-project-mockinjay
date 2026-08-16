"""Owner-scoped MongoDB adapter contract with zero unauthorized writes."""

from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.adapters.mongodb.chat_repository import MongoChatRepository
from app.core.actor import ActorContext
from app.features.chat.domain import ChatAccessDenied, ChatMessage, ChatRoomNotFound


class Rooms:
    def __init__(self) -> None:
        self.queries = []

    async def find_one(self, query):
        """
        주어진 조건에 일치하는 채팅방을 조회합니다.
        
        Parameters:
        	query (dict): 채팅방 조회 조건
        
        Returns:
        	dict | None: 조건에 일치하는 채팅방 정보 또는 `None`
        """
        self.queries.append(query)
        if query == {"room_id": "room-a", "user_id": "user-a", "is_deleted": False}:
            return {"room_id": "room-a", "user_id": "user-a"}
        return None


class Manager:
    def __init__(self) -> None:
        """
        테스트용 방 조회 객체와 대화 쓰기 기록을 초기화합니다.
        """
        self.rooms = Rooms()
        self.writes = []

    async def connect(self):
        return None

    @property
    def db(self):
        """채팅방 컬렉션을 데이터베이스 매핑으로 제공합니다.
        
        Returns:
        	dict: `chat_rooms` 키에 채팅방 컬렉션을 매핑한 데이터베이스 정보
        """
        return {"chat_rooms": self.rooms}

    async def save_conversation(self, *args):
        """대화 메시지 저장 요청을 기록합니다."""
        self.writes.append(args)


def repository(manager: Manager, *, session_user_id: str = "user-a") -> MongoChatRepository:
    """
    테스트용 MongoDB 채팅 저장소를 구성합니다.
    
    Parameters:
    	session_user_id (str): 세션에 연결할 사용자 ID
    
    Returns:
    	MongoChatRepository: 테스트용 세션 및 컨텍스트 엔지니어가 설정된 저장소
    """
    engineer = SimpleNamespace(
        db_manager=manager,
        get_user_context=lambda _user_id: None,
        analyze_and_update_context=lambda _user_id: None,
    )

    async def get_context(_user_id):
        """
        빈 컨텍스트를 반환합니다.
        
        Parameters:
        	_user_id: 컨텍스트를 요청하는 사용자 식별자입니다.
        
        Returns:
        	dict: 빈 컨텍스트입니다.
        """
        return {}

    async def analyze(_user_id):
        return None

    engineer.get_user_context = get_context
    engineer.analyze_and_update_context = analyze
    context = SimpleNamespace(
        session_manager=SimpleNamespace(
            get_session=lambda session_id: {
                "session_id": session_id,
                "user_id": session_user_id,
                "room_id": "room-a",
            }
        ),
        context_engineer=engineer,
    )
    return MongoChatRepository(context)


@pytest.mark.asyncio
async def test_owned_room_write_revalidates_owner_in_query() -> None:
    manager = Manager()
    adapter = repository(manager)
    actor = await adapter.authorize_actor(
        ActorContext(user_id="user-a", room_id="room-a", session_id="room-a")
    )
    await adapter.save_message(ChatMessage(actor, "query", "answer"))

    assert manager.rooms.queries == [
        {"room_id": "room-a", "user_id": "user-a", "is_deleted": False},
        {"room_id": "room-a", "user_id": "user-a", "is_deleted": False},
    ]
    assert len(manager.writes) == 1


@pytest.mark.asyncio
async def test_cross_user_room_has_zero_writes() -> None:
    manager = Manager()
    adapter = repository(manager)

    with pytest.raises(ChatRoomNotFound):
        await adapter.save_message(
            ChatMessage(
                ActorContext(
                    user_id="user-b",
                    room_id="room-a",
                    session_id="room-a",
                ),
                "query",
                "answer",
            )
        )

    assert manager.writes == []


@pytest.mark.asyncio
async def test_cross_user_session_has_zero_writes() -> None:
    manager = Manager()
    adapter = repository(manager, session_user_id="user-b")

    with pytest.raises(ChatAccessDenied):
        await adapter.save_message(
            ChatMessage(
                ActorContext(
                    user_id="user-a",
                    room_id="room-a",
                    session_id="room-a",
                ),
                "query",
                "answer",
            )
        )

    assert manager.writes == []
