from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Optional
import hashlib
import json
import os
from datetime import datetime
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContextManager:
    """
    Context Manager for handling conversation history and user context persistence.
    """

    def __init__(self, uri: str = None, db_name: str = "careguide"):
        self.uri = uri or os.getenv(
            "MONGODB_URI",
            "mongodb://careguide:careguide_local@localhost:27017/?authSource=admin",
        )
        self.db_name = db_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None

    async def connect(self):
        """Connect to MongoDB"""
        if not self.client:
            self.client = AsyncIOMotorClient(self.uri)
            self.db = self.client[self.db_name]
            logger.info(f"✅ Context Manager connected: {self.db_name}")

    async def close(self):
        """MongoDB 클라이언트 연결을 종료합니다."""
        if self.client:
            self.client.close()
            logger.info("Context Manager connection closed")

    async def save_conversation(
        self,
        user_id: str,
        session_id: str,
        agent_type: str,
        user_input: str,
        agent_response: str,
        room_id: str = None,
        client_message_id: str = None,
    ) -> bool:
        """
        대화 한 턴을 대화 기록에 저장합니다.
        
        Args:
            user_id: 사용자 ID
            session_id: 세션 ID
            agent_type: 에이전트 유형
            user_input: 사용자 입력
            agent_response: 에이전트 응답
            room_id: 채팅방 ID. 지정하지 않으면 세션 ID를 사용합니다.
            client_message_id: 재시도 시 중복 저장을 방지하기 위해 클라이언트가 재사용하는 메시지 ID
        
        Returns:
            새 대화 문서가 저장되었으면 True, 동일한 사용자와 클라이언트 메시지 ID로 이미 저장된 문서가 있으면 False
        """
        if self.db is None:
            await self.connect()

        normalized_room_id = room_id or session_id
        document = {
            "user_id": user_id,
            "session_id": session_id,
            "room_id": normalized_room_id,
            "agent_type": agent_type,
            "user_input": user_input,
            "agent_response": agent_response,
            "timestamp": datetime.utcnow()
        }
        if client_message_id:
            document["client_message_id"] = client_message_id
            document["_schema_version"] = 2
            scope = json.dumps(
                [user_id, client_message_id],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            digest = hashlib.sha256(scope.encode("utf-8")).hexdigest()
            document["_id"] = f"chat-v1:{digest}"
            result = await self.db.conversation_history.update_one(
                {"_id": document["_id"]},
                {"$setOnInsert": document},
                upsert=True,
            )
            return result.upserted_id is not None

        await self.db.conversation_history.insert_one(document)
        return True

    async def get_recent_conversations(self, user_id: str, limit: int = 5) -> List[Dict]:
        """
        사용자의 모든 에이전트 대화 중 최근 기록을 시간순으로 조회합니다.
        
        Parameters:
        	user_id (str): 대화를 조회할 사용자 ID
        	limit (int): 반환할 최대 대화 수
        
        Returns:
        	List[Dict]: 오래된 대화부터 정렬된 대화 기록 목록
        """
        if self.db is None:
            await self.connect()

        cursor = self.db.conversation_history.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(limit)

        results = await cursor.to_list(length=limit)
        # Return in chronological order for context
        return sorted(results, key=lambda x: x["timestamp"])

    async def get_conversations_by_agent(self, user_id: str, agent_type: str, limit: int = 50) -> List[Dict]:
        """
        Get recent conversations for a specific agent type.

        Args:
            user_id: User ID
            agent_type: Agent type (e.g., 'nutrition', 'medical_welfare')
            limit: Maximum number of conversations to return

        Returns:
            List of conversation documents for the specified agent
        """
        if self.db is None:
            await self.connect()

        cursor = self.db.conversation_history.find(
            {"user_id": user_id, "agent_type": agent_type}
        ).sort("timestamp", -1).limit(limit)

        results = await cursor.to_list(length=limit)
        # Return in chronological order for context
        return sorted(results, key=lambda x: x["timestamp"])

    async def get_conversations_by_session_and_agent(
        self,
        session_id: str,
        agent_type: str,
        limit: int = 50,
        user_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        Get conversations for a specific session and agent type.

        Args:
            session_id: Session ID
            agent_type: Agent type (e.g., 'nutrition', 'medical_welfare')
            limit: Maximum number of conversations to return

        Returns:
            List of conversation documents for the specified session and agent
        """
        if self.db is None:
            await self.connect()

        query = {"session_id": session_id, "agent_type": agent_type}
        if user_id:
            query["user_id"] = user_id

        cursor = self.db.conversation_history.find(query).sort("timestamp", -1).limit(limit)

        results = await cursor.to_list(length=limit)
        # Return in chronological order for context
        return sorted(results, key=lambda x: x["timestamp"])

    async def save_user_context(self, user_id: str, summary: str, keywords: List[str]):
        """
        Save or update user context (summary and keywords).
        """
        if self.db is None:
            await self.connect()

        await self.db.user_context.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "summary": summary,
                    "keywords": keywords,
                    "last_updated": datetime.utcnow()
                }
            },
            upsert=True
        )

    async def get_user_context(self, user_id: str) -> Optional[Dict]:
        """
        Get user context.
        """
        if self.db is None:
            await self.connect()

        return await self.db.user_context.find_one({"user_id": user_id})

    async def get_conversations_by_room(self, room_id: str, limit: int = 50) -> List[Dict]:
        """
        Get conversations for a specific room.

        Args:
            room_id: 채팅방 ID
            limit: 최대 개수

        Returns:
            List[Dict]: 해당 채팅방의 대화 목록
        """
        if self.db is None:
            await self.connect()

        cursor = self.db.conversation_history.find(
            {"room_id": room_id}
        ).sort("timestamp", -1).limit(limit)

        results = await cursor.to_list(length=limit)
        # Return in chronological order for context
        return sorted(results, key=lambda x: x["timestamp"])

    async def get_user_rooms(self, user_id: str) -> List[Dict]:
        """
        Get list of chat rooms for a user.

        Args:
            user_id: 사용자 ID

        Returns:
            List[Dict]: 채팅방 목록 (room_id, 마지막 메시지 시간, 마지막 메시지 등)
        """
        if self.db is None:
            await self.connect()

        # Aggregate to get unique rooms with latest message
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$room_id",
                "last_message_time": {"$first": "$timestamp"},
                "last_user_input": {"$first": "$user_input"},
                "last_agent_response": {"$first": "$agent_response"},
                "last_agent_type": {"$first": "$agent_type"},
                "message_count": {"$sum": 1}
            }},
            {"$sort": {"last_message_time": -1}}
        ]

        results = await self.db.conversation_history.aggregate(pipeline).to_list(length=None)

        return [{
            "room_id": r["_id"],
            "last_message_time": r["last_message_time"],
            "last_user_input": r["last_user_input"],
            "last_agent_response": r["last_agent_response"][:100] + "..." if len(r["last_agent_response"]) > 100 else r["last_agent_response"],
            "last_agent_type": r["last_agent_type"],
            "message_count": r["message_count"]
        } for r in results]
