"""
Chat API Router - Proxy to Parlant Server
Routes all /api/chat requests to the Parlant agent server
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import httpx
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

from app.features.chat.runtime import get_stream_registry, get_context_system
import json
import asyncio

# Parlant server configuration
# Parlant server configuration
PARLANT_HOST = os.getenv("PARLANT_HOST", "127.0.0.1")
RESEARCH_PORT = int(os.getenv("RESEARCH_PORT", "8800"))
WELFARE_PORT = int(os.getenv("WELFARE_PORT", "8801"))

RESEARCH_BASE_URL = f"http://{PARLANT_HOST}:{RESEARCH_PORT}"
WELFARE_BASE_URL = f"http://{PARLANT_HOST}:{WELFARE_PORT}"

# Default to Research for backward compatibility
PARLANT_BASE_URL = RESEARCH_BASE_URL

# HTTP client for proxying
client = httpx.AsyncClient(timeout=30.0)
_background_tasks: set[asyncio.Task] = set()
_ALLOWED_PROFILES = {"general", "patient", "researcher"}


def _normalize_profile(value: object) -> str:
    return value if isinstance(value, str) and value in _ALLOWED_PROFILES else "general"

# Import Agents to ensure registration
from Agent.medical_welfare.agent import MedicalWelfareAgent
from Agent.research_paper.agent import ResearchPaperAgent
from Agent.core.contracts import AgentRequest
from app.services.agent_runtime import AgentRuntime, get_agent_runtime
from app.api.dependencies import (
    authorize_chat_actor,
    get_request_user_id,
    require_user_match,
)
from app.bootstrap.container import ChatContainer, get_chat_container
from app.core.actor import ActorContext
from app.core.emergency_safety import EMERGENCY_RESPONSE, emergency_safety_policy
from app.features.chat.application import ChatCommand, PreparedChatStream
from app.features.chat.domain import (
    ChatAccessDenied,
    ChatError,
    ChatProviderTimeout,
    ChatProviderUnavailable,
    ChatRoomNotFound,
    ChatSessionNotFound,
)


def _authorize_user(request: Request, requested_user_id: Optional[str]) -> str:
    """인증된 JWT 주체와 요청된 사용자 식별자를 확인합니다.
    
    Parameters:
    	requested_user_id (Optional[str]): 요청에 포함된 사용자 식별자
    
    Returns:
    	str: 인증된 사용자의 식별자
    """
    current_user_id = get_request_user_id(request)
    require_user_match(requested_user_id, current_user_id)
    return current_user_id


def _authorize_session(request: Request, context_system, session_id: str) -> str:
    """Ensure an existing session belongs to the authenticated subject."""
    current_user_id = get_request_user_id(request)
    session = context_system.session_manager.get_session(session_id)
    if session and session.get("user_id") != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied: session ownership mismatch")
    return current_user_id


async def _emergency_sse():
    event = {
        "status": "complete",
        "content": EMERGENCY_RESPONSE,
        "agent_type": "emergency_safety",
        "is_emergency": True,
    }
    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


async def _persist_chat_response(
    context_system,
    *,
    user_id: str,
    session_id: str,
    room_id: str | None,
    query: str,
    answer: str,
    agent_type: str = "ollama_rag",
    client_message_id: str | None = None,
) -> None:
    """
    직접 생성된 채팅 응답을 대화 기록에 저장하고 사용자 컨텍스트를 갱신합니다.
    
    Parameters:
    	user_id (str): 대화를 저장할 사용자 식별자
    	session_id (str): 대화를 저장할 세션 식별자
    	room_id (str | None): 대화를 저장할 방 식별자
    	query (str): 사용자의 원본 질문
    	answer (str): 저장할 채팅 응답
    	agent_type (str): 응답을 생성한 에이전트 유형
    	client_message_id (str | None): 클라이언트가 부여한 메시지 식별자
    
    저장에 필요한 값이 없거나 대화 저장에 실패하면 현재 응답 처리를 중단하지 않습니다.
    """
    if not (answer and user_id and session_id and query):
        return
    try:
        created = await context_system.context_engineer.db_manager.save_conversation(
            user_id,
            session_id,
            agent_type,
            query,
            answer,
            room_id,
            client_message_id,
        )
        if created is False:
            return
        task = asyncio.create_task(
            context_system.context_engineer.analyze_and_update_context(user_id)
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
    except Exception as exc:  # history persistence must not hide a valid answer
        logger.warning("History saving failed for direct Ollama response: %s", exc)


def _raise_hex_chat_error(error: ChatError) -> None:
    """
    도메인 채팅 오류를 적절한 HTTP 예외로 변환합니다.
    
    Parameters:
    	error (ChatError): 변환할 채팅 도메인 오류
    
    Raises:
    	HTTPException: 오류 유형에 해당하는 HTTP 상태 코드와 메시지를 포함합니다.
    """
    if isinstance(error, ChatAccessDenied):
        raise HTTPException(status_code=403, detail="Access denied") from error
    if isinstance(error, (ChatRoomNotFound, ChatSessionNotFound)):
        raise HTTPException(status_code=404, detail="Chat resource not found") from error
    if isinstance(error, ChatProviderTimeout):
        raise HTTPException(status_code=504, detail="Local chat provider timeout") from error
    if isinstance(error, ChatProviderUnavailable):
        raise HTTPException(status_code=503, detail="Local chat provider unavailable") from error
    raise HTTPException(status_code=503, detail="Chat request failed") from error


async def _hex_chat_message(
    *,
    container: ChatContainer,
    query: str,
    user_id: str,
    session_id: str,
    room_id: str | None,
    profile: str,
    client_message_id: str | None,
) -> JSONResponse:
    """
    Hex Chat 사용 사례를 실행하고 생성된 답변과 메타데이터를 JSON 응답으로 반환합니다.
    
    Parameters:
    	container (ChatContainer): Chat 실행 컨테이너
    	query (str): 사용자의 채팅 질의
    	user_id (str): 요청한 사용자의 식별자
    	session_id (str): 채팅 세션 식별자
    	room_id (str | None): 채팅방 식별자
    	profile (str): 채팅 프로필
    	client_message_id (str | None): 클라이언트가 지정한 메시지 식별자
    
    Returns:
    	JSONResponse: 답변, 에이전트 유형, 출처 및 메타데이터를 포함한 JSON 응답
    """
    use_case = container.send_chat_message
    if use_case is None:
        raise RuntimeError("hex Chat use case is not configured")
    try:
        generation = await use_case.execute(
            ChatCommand(
                actor=ActorContext(
                    user_id=user_id,
                    room_id=room_id,
                    session_id=session_id,
                ),
                query=query,
                profile=profile,
                client_message_id=client_message_id,
            )
        )
    except ChatError as error:
        container.telemetry.record("message", "failure")
        _raise_hex_chat_error(error)

    outcome = "success" if generation.persisted else "persistence_failure"
    container.telemetry.record("message", outcome)
    return JSONResponse(
        content=json.loads(
            json.dumps(
                {
                    "answer": generation.answer,
                    "content": generation.answer,
                    "status": "success",
                    "agent_type": generation.agent_type,
                    "sources": list(generation.sources),
                    "metadata": dict(generation.metadata),
                },
                default=str,
            )
        )
    )


async def _prepare_hex_chat_stream(
    *,
    request: Request,
    container: ChatContainer,
    query: str,
    user_id: str,
    session_id: str,
    room_id: str | None,
    profile: str,
    client_message_id: str | None,
) -> StreamingResponse:
    """
    Hex 채팅 스트리밍 요청을 준비하고 SSE 응답을 생성합니다.
    
    Parameters:
        request (Request): 클라이언트 연결 상태 확인에 사용할 요청 객체
        container (ChatContainer): 스트리밍 채팅 실행 및 텔레메트리를 제공하는 컨테이너
        query (str): 사용자가 보낸 채팅 질의
        user_id (str): 채팅 요청을 수행하는 사용자 식별자
        session_id (str): 채팅 세션 식별자
        room_id (str | None): 채팅방 식별자
        profile (str): 적용할 채팅 프로필
        client_message_id (str | None): 중복 처리를 위한 클라이언트 메시지 식별자
    
    Returns:
        StreamingResponse: 채팅 이벤트를 Server-Sent Events 형식으로 전달하는 응답
    
    Raises:
        RuntimeError: 스트리밍 채팅 실행 사례가 구성되지 않은 경우
    """
    use_case = container.stream_chat_message
    if use_case is None:
        raise RuntimeError("hex Chat stream use case is not configured")
    try:
        prepared = await use_case.prepare(
            ChatCommand(
                actor=ActorContext(
                    user_id=user_id,
                    room_id=room_id,
                    session_id=session_id,
                ),
                query=query,
                profile=profile,
                client_message_id=client_message_id,
            )
        )
    except ChatError as error:
        container.telemetry.record("stream", "failure")
        _raise_hex_chat_error(error)

    return StreamingResponse(
        _hex_chat_stream_events(request, container, prepared),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _hex_chat_stream_events(
    request: Request,
    container: ChatContainer,
    prepared: PreparedChatStream,
):
    """
    스트리밍 채팅 이벤트를 SSE 형식으로 전달하고 스트림 상태와 종료 텔레메트리를 관리합니다.
    
    Parameters:
    	request (Request): 클라이언트 연결 상태와 스트림 레지스트리에 접근하기 위한 요청 객체
    	container (ChatContainer): 스트리밍 채팅 유스케이스와 텔레메트리를 제공하는 컨테이너
    	prepared (PreparedChatStream): 스트리밍 채팅 실행에 필요한 인증 및 요청 정보
    
    Yields:
    	str: 채팅 이벤트 또는 스트림 종료를 나타내는 SSE 데이터
    """
    use_case = container.stream_chat_message
    if use_case is None:
        raise RuntimeError("hex Chat stream use case is not configured")

    stream_registry = get_stream_registry(request)
    session_id = prepared.actor.session_id or f"default:{prepared.actor.user_id}"
    stream_registry.set(
        session_id,
        {
            "session_id": session_id,
            "room_id": prepared.actor.room_id,
            "user_id": prepared.actor.user_id,
            "started_at": datetime.utcnow(),
            "cancel_requested": False,
            "partial_response": "",
        },
    )
    terminal = "failure"

    async def is_cancelled() -> bool:
        """스트리밍 세션의 취소 요청 또는 클라이언트 연결 종료 여부를 확인합니다.
        
        Returns:
        	bool: 취소가 요청되었거나 클라이언트 연결이 종료되었으면 `True`, 그렇지 않으면 `False`.
        """
        metadata = stream_registry.get(session_id, {})
        return bool(metadata.get("cancel_requested")) or await request.is_disconnected()

    try:
        async for event in use_case.events(prepared, is_cancelled=is_cancelled):
            if event.status in {"complete", "success"}:
                terminal = "success"
            elif event.status == "cancelled":
                terminal = "cancelled"
            elif event.status == "error":
                terminal = "failure"
            metadata = stream_registry.get(session_id)
            if metadata is not None and event.content:
                metadata["partial_response"] = event.content
            yield f"data: {json.dumps(event.as_payload(), ensure_ascii=False, default=str)}\n\n"
    finally:
        stream_registry.pop(session_id, None)
        container.telemetry.record("stream", terminal)
    yield "data: [DONE]\n\n"


async def _direct_ollama_stream(
    service,
    context_system,
    container: ChatContainer,
    *,
    query: str,
    profile: str,
    user_context,
    user_id: str,
    session_id: str,
    room_id: str | None,
    client_message_id: str | None,
):
    """
    로컬 Ollama 서비스의 응답을 서버 전송 이벤트로 스트리밍합니다.
    
    Parameters:
    	service: 스트리밍 응답을 생성하는 로컬 채팅 서비스
    	context_system: 완료된 응답을 저장하고 후속 처리를 수행하는 컨텍스트 시스템
    	container (ChatContainer): 텔레메트리를 기록하는 채팅 컨테이너
    	query (str): 사용자의 채팅 요청
    	profile (str): 채팅에 사용할 사용자 프로필
    	user_context: 응답 생성에 사용할 사용자 컨텍스트
    	user_id (str): 요청한 사용자 식별자
    	session_id (str): 채팅 세션 식별자
    	room_id (str | None): 채팅방 식별자
    	client_message_id (str | None): 클라이언트가 제공한 메시지 식별자
    
    Yields:
    	str: 스트리밍 데이터, 완료 또는 오류 상태, 마지막 스트림 종료 신호를 포함하는 SSE 형식 문자열
    """
    accumulated = ""
    terminal_emitted = False
    completed = False
    try:
        async for chunk in service.stream(
            query, profile=profile, user_context=user_context
        ):
            if isinstance(chunk, dict):
                content = chunk.get("content", "")
                status = chunk.get("status")
            else:
                content = str(chunk)
                status = "streaming"
            if status in {"streaming", "complete"}:
                accumulated = content if status == "complete" else accumulated + content
            terminal_emitted = terminal_emitted or status == "complete"
            yield f"data: {json.dumps(chunk, ensure_ascii=False, default=str)}\n\n"
        if not terminal_emitted:
            terminal = {
                "status": "complete",
                "content": accumulated,
                "agent_type": "ollama_rag",
            }
            yield f"data: {json.dumps(terminal, ensure_ascii=False)}\n\n"
        completed = True
    except Exception:
        logger.error("Direct Ollama stream failed", exc_info=True)
        yield 'data: {"status":"error","error":"local provider stream failed"}\n\n'

    if completed:
        await _persist_chat_response(
            context_system,
            user_id=user_id,
            session_id=session_id,
            room_id=room_id,
            query=query,
            answer=accumulated,
            client_message_id=client_message_id,
        )
    container.telemetry.record("stream", "success" if completed else "failure")
    yield "data: [DONE]\n\n"


async def close_parlant_server(agent_runtime: AgentRuntime | None = None):
    """Close the HTTP client and shutdown agents on shutdown"""
    await client.aclose()

    if agent_runtime is not None:
        await agent_runtime.close()
    
    # Shutdown agent servers if they were started
    try:
        await MedicalWelfareAgent.shutdown_server()
        await ResearchPaperAgent.shutdown_server()
        logger.info("Agent servers shut down")
    except Exception as e:
        logger.warning(f"Error shutting down agent servers: {e}")
        
    logger.info("Parlant proxy client closed")


@router.get("/info")
async def chat_info():
    """
    Get chat service information
    """
    return {
        "service": "Chat API (Router + Parlant Proxy)",
        "router_agent": "active",
        "servers": {
            "research": RESEARCH_BASE_URL,
            "welfare": WELFARE_BASE_URL
        },
        "status": "operational"
    }


@router.get("/rooms")
async def get_user_rooms(user_id: str, request: Request):
    """
    Get list of chat rooms for a user

    DEPRECATED: Use /api/rooms endpoint instead for full room management

    Args:
        user_id: User ID

    Returns:
        List of chat rooms with last message info
    """
    try:
        current_user_id = _authorize_user(request, user_id)
        context_system = get_context_system(request)
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        # Ensure db_manager is connected
        db_manager = context_system.context_engineer.db_manager
        await db_manager.connect()

        rooms = await db_manager.get_user_rooms(current_user_id)

        return {
            "user_id": current_user_id,
            "rooms": rooms,
            "count": len(rooms)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user rooms: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rooms/{room_id}/history")
async def get_room_history(room_id: str, request: Request, limit: int = 50):
    """
    Get conversation history for a specific room

    Args:
        room_id: Room ID
        limit: Maximum number of conversations

    Returns:
        List of conversations in the room
    """
    try:
        current_user_id = _authorize_user(request, None)
        context_system = get_context_system(request)
        db_manager = context_system.context_engineer.db_manager
        await db_manager.connect()
        owned_room = await db_manager.db.chat_rooms.find_one(
            {"room_id": room_id, "user_id": current_user_id, "is_deleted": False}
        )
        if not owned_room:
            raise HTTPException(status_code=404, detail="Room not found")
        conversations = await context_system.context_engineer.db_manager.get_conversations_by_room(
            room_id, limit
        )

        formatted_conversations = []
        for conv in conversations:
            formatted_conversations.append({
                "timestamp": conv.get("timestamp").isoformat() if conv.get("timestamp") else None,
                "user_input": conv.get("user_input"),
                "agent_response": conv.get("agent_response"),
                "agent_type": conv.get("agent_type"),
                "session_id": conv.get("session_id"),
                "room_id": conv.get("room_id")
            })

        return {
            "room_id": room_id,
            "count": len(formatted_conversations),
            "conversations": formatted_conversations
        }

    except Exception as e:
        logger.error(f"Error fetching room history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{agent_type}")
async def get_agent_history(
    agent_type: str,
    request: Request,
    user_id: str = None,
    session_id: str = None,
    limit: int = 50
):
    """
    Get conversation history for a specific agent type

    Args:
        agent_type: Agent type (e.g., 'nutrition', 'medical_welfare', 'research_paper')
        user_id: Optional user ID to filter by user
        session_id: Optional session ID to filter by session
        limit: Maximum number of conversations to return (default: 50)

    Returns:
        List of conversations for the specified agent
    """
    try:
        current_user_id = _authorize_user(request, user_id)
        context_system = get_context_system(request)
        if session_id:
            _authorize_session(request, context_system, session_id)
        # Validate agent_type
        valid_agents = ["nutrition", "medical_welfare", "research_paper", "quiz", "trend_visualization"]
        if agent_type not in valid_agents:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agent_type. Must be one of: {', '.join(valid_agents)}"
            )

        # Query based on provided filters
        if session_id and agent_type:
            # Get from MongoDB by session and agent
            conversations = await context_system.context_engineer.db_manager.get_conversations_by_session_and_agent(
                session_id, agent_type, limit, user_id=current_user_id
            )
        elif current_user_id and agent_type:
            # Get from MongoDB by user and agent
            conversations = await context_system.context_engineer.db_manager.get_conversations_by_agent(
                current_user_id, agent_type, limit
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Either user_id or session_id must be provided"
            )

        # Format response
        formatted_conversations = []
        for conv in conversations:
            formatted_conversations.append({
                "timestamp": conv.get("timestamp").isoformat() if conv.get("timestamp") else None,
                "user_input": conv.get("user_input"),
                "agent_response": conv.get("agent_response"),
                "agent_type": conv.get("agent_type"),
                "session_id": conv.get("session_id")
            })

        return {
            "agent_type": agent_type,
            "count": len(formatted_conversations),
            "conversations": formatted_conversations
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching agent history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_all_history(
    request: Request,
    user_id: str = None,
    session_id: str = None,
    limit: int = 50
):
    """
    Get conversation history for all agents

    Args:
        user_id: Optional user ID to filter by user
        session_id: Optional session ID to filter by session (not used yet)
        limit: Maximum number of conversations to return (default: 50)

    Returns:
        List of all conversations
    """
    try:
        current_user_id = _authorize_user(request, user_id)
        if session_id:
            context_system = get_context_system(request)
            _authorize_session(request, context_system, session_id)
        context_system = get_context_system(request)

        # Get all conversations for the user
        conversations = await context_system.context_engineer.db_manager.get_recent_conversations(
            current_user_id, limit
        )

        # Format response
        formatted_conversations = []
        for conv in conversations:
            formatted_conversations.append({
                "timestamp": conv.get("timestamp").isoformat() if conv.get("timestamp") else None,
                "user_input": conv.get("user_input"),
                "agent_response": conv.get("agent_response"),
                "agent_type": conv.get("agent_type"),
                "session_id": conv.get("session_id")
            })

        return {
            "count": len(formatted_conversations),
            "conversations": formatted_conversations
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message")
async def chat_message(request: Request):
    """
    인증된 사용자의 채팅 메시지를 처리합니다.
    
    응급 안전 정책을 적용한 뒤 설정된 채팅 런타임을 통해 응답을 생성하며, 필요에 따라 JSON 응답 또는 Server-Sent Events 스트림으로 반환합니다. 처리된 대화는 세션 및 채팅방 정보와 함께 저장됩니다.
    
    Parameters:
        request (Request): 채팅 요청과 인증 정보를 담은 FastAPI 요청 객체.
    
    Returns:
        JSONResponse 또는 StreamingResponse: 생성된 답변이나 스트리밍 채팅 이벤트.
    
    Raises:
        HTTPException: 요청 본문이 잘못되었거나 인증에 실패한 경우 400 또는 500 상태 코드로 발생합니다.
    """
    container = None
    try:
        context_system = get_context_system(request)
        body = await request.json()
        query = body.get("query") or body.get("message")
        session_id = body.get("session_id", "default")
        user_id = _authorize_user(request, body.get("user_id"))
        room_id = body.get("room_id") # Optional - for multiple chat rooms

        if not query:
            raise HTTPException(status_code=400, detail="Query is required")

        profile = _normalize_profile(
            body.get("profile") or body.get("user_profile", "general")
        )
        client_message_id = body.get("client_message_id")
        container = get_chat_container(request)
        if client_message_id is not None and (
            not isinstance(client_message_id, str)
            or not client_message_id.strip()
            or len(client_message_id) > 128
        ):
            raise HTTPException(status_code=400, detail="Invalid client_message_id")
        if container.is_hex:
            return await _hex_chat_message(
                container=container,
                query=query,
                user_id=user_id,
                session_id=session_id,
                room_id=room_id,
                profile=profile,
                client_message_id=client_message_id,
            )

        decision = emergency_safety_policy.evaluate(query)
        if decision.blocked:
            container.telemetry.record("message", "success")
            return JSONResponse(
                content={
                    "answer": EMERGENCY_RESPONSE,
                    "content": EMERGENCY_RESPONSE,
                    "status": "success",
                    "agent_type": "emergency_safety",
                    "sources": [],
                    "metadata": {
                        "provider": "emergency_pre_filter",
                        "is_emergency": True,
                    },
                }
            )

        actor = await authorize_chat_actor(
            request,
            context_system,
            requested_user_id=body.get("user_id"),
            room_id=room_id,
            session_id=session_id,
        )
        user_id = actor.user_id
        session_id = actor.session_id

        # --- Context Engineering: Injection ---
        context = body.get("context", {})

        if user_id:
            try:
                # 1. Get Context
                user_context = await context_system.context_engineer.get_user_context(user_id)

                # 2. Inject Context
                if user_context.get("summary") or user_context.get("keywords"):
                    if "user_history" not in context:
                        context["user_history"] = user_context
                    logger.info("Injected redacted user context")
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"Context injection failed: {e}")

        # Handle explicit agent selection
        agent_type = body.get("agent_type")
        if agent_type and agent_type != "auto":
            context["target_agent"] = agent_type

        # Get user profile for Parlant customer tag
        # 사용자 프로필 추출 (Parlant 고객 태그용)
        # The canonical runtime uses the local Ollama/RAG service directly.
        # Tests and legacy callers may still inject a router-only runtime, so
        # retain that seam as an explicit fallback.
        runtime = get_agent_runtime(request)
        chat_service = getattr(runtime, "chat_service", None) if getattr(runtime, "use_ollama", True) else None
        if chat_service is not None:
            user_context = context.get("user_history")
            result = await chat_service.generate(
                query, profile=profile, user_context=user_context
            )
            answer = result.get("answer", "")
            await _persist_chat_response(
                context_system,
                user_id=user_id,
                session_id=session_id,
                room_id=room_id,
                query=query,
                answer=answer,
                client_message_id=client_message_id,
            )
            container.telemetry.record("message", "success")
            return JSONResponse(
                content=json.loads(json.dumps({
                    "answer": answer,
                    "content": answer,
                    "status": "success",
                    "agent_type": "ollama_rag",
                    "sources": result.get("sources", []),
                    "metadata": result.get("metadata", {}),
                }, default=str))
            )

        # Create AgentRequest
        agent_request = AgentRequest(
            query=query,
            session_id=session_id,
            user_id=user_id,
            context=context,
            profile=profile  # Pass profile for Parlant integration
        )

        router_agent = runtime.router_agent

        async def event_generator():
            """
            라우터 에이전트의 채팅 스트림을 SSE 이벤트로 생성합니다.
            
            스트림 취소와 처리 오류를 이벤트로 알리고, 성공적으로 완료된 응답은 대화 기록에 저장한 뒤 종료 이벤트를 전송합니다.
            """
            accumulated_response = ""
            final_agent_type = None
            completed = False
            failed = False
            stream_registry = get_stream_registry(request)

            # Register this stream as active
            stream_info = {
                "session_id": session_id,
                "room_id": room_id,
                "user_id": user_id,
                "started_at": datetime.utcnow(),
                "cancel_requested": False,
                "partial_response": ""
            }
            stream_registry.set(session_id, stream_info)

            try:
                async for chunk in router_agent.process_stream(agent_request):
                    # Check for cancellation request
                    if stream_registry.get(session_id, {}).get("cancel_requested"):
                        logger.info("Chat stream cancelled")
                        completed = False
                        failed = True
                        yield f"data: {json.dumps({'status': 'cancelled', 'message': 'Stream stopped by user'})}\n\n"
                        break
                    content = ""
                    current_agent_type = None

                    if isinstance(chunk, dict):
                        if "content" in chunk:
                            content = chunk["content"]
                        elif "answer" in chunk:
                            content = chunk["answer"]

                        if "agent_type" in chunk:
                            current_agent_type = chunk["agent_type"]

                        yield f"data: {json.dumps(chunk)}\n\n"

                    elif hasattr(chunk, 'dict'):
                        resp_dict = chunk.dict()
                        content = resp_dict.get("answer", "")
                        current_agent_type = resp_dict.get("agent_type")
                        yield f"data: {json.dumps(resp_dict, default=str)}\n\n"
                    else:
                        content = str(chunk)
                        yield f"data: {json.dumps({'content': content})}\n\n"

                    if current_agent_type:
                        final_agent_type = current_agent_type

                    if isinstance(chunk, dict) and chunk.get("status") in {"error", "cancelled"}:
                        failed = True

                    if isinstance(chunk, dict) and chunk.get("status") in {"complete", "success"}:
                        accumulated_response = content
                        completed = True
                    elif isinstance(chunk, dict) and chunk.get("status") == "streaming":
                        accumulated_response += content
                    elif isinstance(chunk, dict) and chunk.get("status") == "new_message":
                        # Each new_message is a separate message, append with newline
                        if accumulated_response:
                            accumulated_response += "\n\n" + content
                        else:
                            accumulated_response = content
                    elif hasattr(chunk, 'dict'):
                        accumulated_response = content
                        completed = completed or resp_dict.get("status") in {"complete", "success"}
                        failed = failed or resp_dict.get("status") in {"error", "cancelled"}

                    # Update partial response for cancellation handling
                    if session_id in stream_registry:
                        stream_registry.get(session_id)["partial_response"] = accumulated_response

                if accumulated_response and not completed and not failed:
                    completed = True
                    yield f"data: {json.dumps({'status': 'complete', 'content': accumulated_response, 'agent_type': final_agent_type or 'research_paper'})}\n\n"

            except Exception:
                completed = False
                logger.error("Chat stream failed", exc_info=True)
                yield 'data: {"status":"error","error":"local chat stream failed"}\n\n'
            finally:
                # Remove from active streams
                stream_registry.pop(session_id, None)

            # Save to DB after stream completes
            try:
                if (
                    completed
                    and not failed
                    and session_id
                    and query
                    and user_id
                    and accumulated_response
                ):
                    save_agent_type = final_agent_type or "research_paper"

                    created = await context_system.context_engineer.db_manager.save_conversation(
                        user_id,
                        session_id,
                        save_agent_type,
                        query,
                        accumulated_response,
                        room_id,
                        client_message_id,
                    )
                    if created is not False:
                        asyncio.create_task(
                            context_system.context_engineer.analyze_and_update_context(user_id)
                        )
                    logger.info("Saved redacted streaming conversation metadata")
            except Exception as e:
                logger.warning(f"History saving failed in stream: {e}")

            container.telemetry.record(
                "message",
                "success" if completed and not failed else "failure",
            )
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        if container is not None:
            container.telemetry.record("message", "failure")
        logger.error(f"Chat processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: Request):
    """
    채팅 요청을 처리하고 Server-Sent Events 형식으로 응답을 스트리밍합니다.
    
    긴급 안전 정책에 의해 차단된 요청에는 고정된 긴급 응답을 보내며, 구성에 따라
    Hex Chat, Ollama 또는 Router Agent를 사용합니다. 성공적으로 완료된 대화는 대화
    기록에 저장됩니다.
    
    Returns:
    	StreamingResponse: 채팅 이벤트와 스트림 종료 신호를 포함하는 SSE 응답
    """
    container = None
    try:
        context_system = get_context_system(request)
        body = await request.json()
        query = body.get("query") or body.get("message")
        session_id = body.get("session_id", "default")
        user_id = _authorize_user(request, body.get("user_id"))
        room_id = body.get("room_id") # Optional - for multiple chat rooms

        # Debug: Log session and room info for room-based session separation
        logger.info("Authenticated chat stream request received")

        if not query:
            raise HTTPException(status_code=400, detail="Query is required")

        profile = _normalize_profile(
            body.get("profile") or body.get("user_profile", "general")
        )
        client_message_id = body.get("client_message_id")
        container = get_chat_container(request)
        if client_message_id is not None and (
            not isinstance(client_message_id, str)
            or not client_message_id.strip()
            or len(client_message_id) > 128
        ):
            raise HTTPException(status_code=400, detail="Invalid client_message_id")
        if container.is_hex:
            return await _prepare_hex_chat_stream(
                request=request,
                container=container,
                query=query,
                user_id=user_id,
                session_id=session_id,
                room_id=room_id,
                profile=profile,
                client_message_id=client_message_id,
            )

        decision = emergency_safety_policy.evaluate(query)
        if decision.blocked:
            container.telemetry.record("stream", "success")
            return StreamingResponse(
                _emergency_sse(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        actor = await authorize_chat_actor(
            request,
            context_system,
            requested_user_id=body.get("user_id"),
            room_id=room_id,
            session_id=session_id,
        )
        user_id = actor.user_id
        session_id = actor.session_id

        # --- Context Engineering: Injection ---
        context = body.get("context", {})
        
        if user_id:
            try:
                # 1. Get Context
                user_context = await context_system.context_engineer.get_user_context(user_id)
                
                # 2. Inject Context
                if user_context.get("summary") or user_context.get("keywords"):
                    if "user_history" not in context:
                        context["user_history"] = user_context
                    logger.info("Injected redacted user context")
            except Exception as e:
                logger.warning(f"Context injection failed: {e}")

        # Handle explicit agent selection
        agent_type = body.get("agent_type")
        if agent_type and agent_type != "auto":
            context["target_agent"] = agent_type

        # Get user profile for Parlant customer tag
        # 사용자 프로필 추출 (Parlant 고객 태그용)
        runtime = get_agent_runtime(request)
        chat_service = getattr(runtime, "chat_service", None) if getattr(runtime, "use_ollama", True) else None
        if chat_service is not None:
            user_context = context.get("user_history")
            return StreamingResponse(
                _direct_ollama_stream(
                    chat_service,
                    context_system,
                    container,
                    query=query,
                    profile=profile,
                    user_context=user_context,
                    user_id=user_id,
                    session_id=session_id,
                    room_id=room_id,
                    client_message_id=client_message_id,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        # Create AgentRequest
        agent_request = AgentRequest(
            query=query,
            session_id=session_id,
            user_id=user_id,
            context=context,
            profile=profile  # Pass profile for Parlant integration
        )

        router_agent = runtime.router_agent

        async def event_generator():
            """
            라우터 에이전트의 응답을 SSE 이벤트로 변환하고 대화 기록을 저장합니다.
            
            Returns:
            	str: 응답 청크, 완료 또는 오류 상태, 스트림 종료를 나타내는 SSE 이벤트
            """
            accumulated_response = ""
            final_agent_type = None
            completed = False
            failed = False

            try:
                async for chunk in router_agent.process_stream(agent_request):
                    # Determine content and agent_type from chunk
                    content = ""
                    current_agent_type = None

                    if isinstance(chunk, dict):
                        # Handle dict chunks (from Router or Streaming Agents)
                        if "content" in chunk:
                            content = chunk["content"]
                        elif "answer" in chunk:
                            content = chunk["answer"]

                        if "agent_type" in chunk:
                            current_agent_type = chunk["agent_type"]

                        sse_data = f"data: {json.dumps(chunk)}\n\n"
                        logger.info("Sending redacted SSE frame")
                        yield sse_data

                    elif hasattr(chunk, 'dict'): # AgentResponse (Pydantic)
                        # Handle full response (Non-streaming Agents)
                        resp_dict = chunk.dict()
                        content = resp_dict.get("answer", "")
                        current_agent_type = resp_dict.get("agent_type")
                        # Ensure consistent format with 'content' field for frontend compatibility
                        resp_dict["content"] = content  # Add content field for frontend
                        sse_data = f"data: {json.dumps(resp_dict, default=str)}\n\n"
                        logger.info("Sending redacted structured SSE frame")
                        logger.debug(f"📤 SSE full data keys: {list(resp_dict.keys())}")
                        yield sse_data
                    else:
                        # Handle raw string or other types
                        content = str(chunk)
                        sse_data = f"data: {json.dumps({'content': content})}\n\n"
                        logger.info("Sending redacted compatibility SSE frame")
                        yield sse_data

                    # Accumulate for history
                    # Note: For synthesized responses, the last chunk usually contains the full answer.
                    # For streaming, we might need to append. 
                    # RouterAgent sends "status": "complete" with full content for synthesis.
                    # Single agent streaming sends parts.
                    
                    if current_agent_type:
                        final_agent_type = current_agent_type

                    if isinstance(chunk, dict) and chunk.get("status") in {"error", "cancelled"}:
                        failed = True
                    
                    if isinstance(chunk, dict) and chunk.get("status") in {"complete", "success"}:
                        # Final synthesized answer
                        accumulated_response = content
                        completed = True
                    elif isinstance(chunk, dict) and chunk.get("status") == "streaming":
                        # Streaming parts
                        accumulated_response += content
                    elif isinstance(chunk, dict) and chunk.get("status") == "new_message":
                        # Each new_message is a separate message, append with newline
                        if accumulated_response:
                            accumulated_response += "\n\n" + content
                        else:
                            accumulated_response = content
                    elif hasattr(chunk, 'dict'):
                        # Full response object
                        accumulated_response = content
                        completed = completed or resp_dict.get("status") in {"complete", "success"}
                        failed = failed or resp_dict.get("status") in {"error", "cancelled"}

                if accumulated_response and not completed and not failed:
                    completed = True
                    yield f"data: {json.dumps({'status': 'complete', 'content': accumulated_response, 'agent_type': final_agent_type or 'research_paper'})}\n\n"

            except Exception:
                completed = False
                logger.error("Chat stream failed", exc_info=True)
                yield 'data: {"status":"error","error":"local chat stream failed"}\n\n'

            # Save to DB after stream completes
            try:
                if (
                    completed
                    and not failed
                    and session_id
                    and query
                    and user_id
                    and accumulated_response
                ):
                    # Use final_agent_type or default to router/research_paper
                    save_agent_type = final_agent_type or "research_paper"

                    created = await context_system.context_engineer.db_manager.save_conversation(
                        user_id,
                        session_id,
                        save_agent_type,
                        query,
                        accumulated_response,
                        room_id,
                        client_message_id,
                    )
                    # Trigger analysis (fire and forget)
                    if created is not False:
                        asyncio.create_task(
                            context_system.context_engineer.analyze_and_update_context(user_id)
                        )
                    logger.info("Saved redacted streaming conversation metadata")
            except Exception as e:
                logger.warning(f"History saving failed in stream: {e}")

            container.telemetry.record(
                "stream",
                "success" if completed and not failed else "failure",
            )
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        if container is not None:
            container.telemetry.record("stream", "failure")
        logger.error(f"Chat stream error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))





@router.api_route("/welfare/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_welfare(path: str, request: Request):
    """Proxy to Medical Welfare Agent (Port 8801)"""
    return await _proxy_request(path, request, WELFARE_BASE_URL)


@router.api_route("/research/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_research(path: str, request: Request):
    """Proxy to Research Paper Agent (Port 8800)"""
    return await _proxy_request(path, request, RESEARCH_BASE_URL)


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_default(path: str, request: Request):
    """
    Default Proxy (Research Agent - Port 8800)
    Kept for backward compatibility
    """
    return await _proxy_request(path, request, RESEARCH_BASE_URL)


async def _proxy_request(path: str, request: Request, base_url: str):
    """Internal proxy handler"""
    try:
        context_system = get_context_system(request)
        # Build target URL
        url = f"{base_url}/{path}"
        if request.url.query:
            url = f"{url}?{request.url.query}"

        # Prepare headers (exclude host and content-length)
        headers = {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in ["host", "content-length"]
        }

        # --- Context Engineering: Injection (Only for POST) ---
        if request.method == "POST":
            # Authenticate before reading or parsing attacker-controlled body
            # bytes so malformed payloads cannot bypass the actor boundary.
            get_request_user_id(request)
            if "application/json" not in request.headers.get("content-type", "").lower():
                raise HTTPException(status_code=415, detail="POST proxy body must be JSON")
            body = await request.body()
            try:
                body_json = json.loads(body)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise HTTPException(status_code=400, detail="Invalid JSON body") from exc
            if not isinstance(body_json, dict):
                raise HTTPException(status_code=400, detail="JSON body must be an object")

            session_id = body_json.get("session_id")
            query = body_json.get("query") or body_json.get("message")
            actor = await authorize_chat_actor(
                request,
                context_system,
                requested_user_id=body_json.get("user_id"),
                room_id=body_json.get("room_id"),
                session_id=session_id,
            )
            body_json["user_id"] = actor.user_id
            body_json["session_id"] = actor.session_id

            if query and emergency_safety_policy.evaluate(query).blocked:
                return JSONResponse(
                    content={
                        "status": "success",
                        "content": EMERGENCY_RESPONSE,
                        "agent_type": "emergency_safety",
                        "is_emergency": True,
                    }
                )

            if actor.session_id and query:
                try:
                    user_context = await context_system.context_engineer.get_user_context(
                        actor.user_id
                    )
                    if user_context.get("summary") or user_context.get("keywords"):
                        context = body_json.setdefault("context", {})
                        if not isinstance(context, dict):
                            raise HTTPException(status_code=400, detail="context must be an object")
                        context["user_history"] = user_context
                        logger.info("Injected redacted user context into proxy request")
                except HTTPException:
                    raise
                except Exception:
                    logger.warning("Context injection failed", exc_info=True)

            body = json.dumps(body_json).encode("utf-8")
            headers["content-length"] = str(len(body))
        else:
            body = await request.body()

        logger.info("Proxying authenticated request to local Parlant")

        # Forward request to Parlant server
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
        )

        # Return response with proper content handling
        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type:
            try:
                return JSONResponse(
                    content=response.json(),
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            except Exception as e:
                # JSON 파싱 실패, 텍스트 응답으로 폴백 (JSON parsing failed, fallback to text response)
                logger.warning(f"Failed to parse JSON response: {e}")
                pass

        # Return text response
        return JSONResponse(
            content={"response": response.text},
            status_code=response.status_code,
            headers=dict(response.headers)
        )

    except HTTPException:
        raise
    except httpx.ConnectError:
        logger.error(f"Cannot connect to Parlant server at {base_url}")
        raise HTTPException(
            status_code=503,
            detail=f"Parlant server unavailable at {base_url}. Please ensure the Parlant server is running."
        )
    except httpx.TimeoutException:
        logger.error("Timeout connecting to Parlant server")
        raise HTTPException(
            status_code=504,
            detail="Parlant server timeout"
        )
    except Exception as e:
        logger.error(f"Proxy error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Proxy error: {str(e)}"
        )
