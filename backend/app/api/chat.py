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
from app.core.emergency_safety import EMERGENCY_RESPONSE, emergency_safety_policy


def _authorize_user(request: Request, requested_user_id: Optional[str]) -> str:
    """Bind caller-supplied user filters to the authenticated JWT subject."""
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
) -> None:
    """Persist a direct Ollama response using the same history contract."""
    if not (answer and user_id and session_id and query):
        return
    try:
        await context_system.context_engineer.db_manager.save_conversation(
            user_id, session_id, agent_type, query, answer, room_id
        )
        task = asyncio.create_task(
            context_system.context_engineer.analyze_and_update_context(user_id)
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
    except Exception as exc:  # history persistence must not hide a valid answer
        logger.warning("History saving failed for direct Ollama response: %s", exc)


async def _direct_ollama_stream(
    service,
    context_system,
    *,
    query: str,
    profile: str,
    user_context,
    user_id: str,
    session_id: str,
    room_id: str | None,
):
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
        )
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
    Main Chat Endpoint - Uses RouterAgent with streaming support
    """
    try:
        context_system = get_context_system(request)
        body = await request.json()
        query = body.get("query") or body.get("message")
        session_id = body.get("session_id", "default")
        user_id = _authorize_user(request, body.get("user_id"))
        room_id = body.get("room_id") # Optional - for multiple chat rooms

        if not query:
            raise HTTPException(status_code=400, detail="Query is required")

        decision = emergency_safety_policy.evaluate(query)
        if decision.blocked:
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
        profile = _normalize_profile(body.get("profile") or body.get("user_profile", "general"))

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
            )
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

                    await context_system.context_engineer.db_manager.save_conversation(
                        user_id, session_id, save_agent_type, query, accumulated_response, room_id
                    )
                    asyncio.create_task(context_system.context_engineer.analyze_and_update_context(user_id))
                    logger.info("Saved redacted streaming conversation metadata")
            except Exception as e:
                logger.warning(f"History saving failed in stream: {e}")

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
        logger.error(f"Chat processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: Request):
    """
    Streaming Chat Endpoint - Uses RouterAgent to handle complex intents with streaming
    """
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

        decision = emergency_safety_policy.evaluate(query)
        if decision.blocked:
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
        profile = _normalize_profile(body.get("profile") or body.get("user_profile", "general"))

        runtime = get_agent_runtime(request)
        chat_service = getattr(runtime, "chat_service", None) if getattr(runtime, "use_ollama", True) else None
        if chat_service is not None:
            user_context = context.get("user_history")
            return StreamingResponse(
                _direct_ollama_stream(
                    chat_service,
                    context_system,
                    query=query,
                    profile=profile,
                    user_context=user_context,
                    user_id=user_id,
                    session_id=session_id,
                    room_id=room_id,
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

                    await context_system.context_engineer.db_manager.save_conversation(
                        user_id, session_id, save_agent_type, query, accumulated_response, room_id
                    )
                    # Trigger analysis (fire and forget)
                    asyncio.create_task(context_system.context_engineer.analyze_and_update_context(user_id))
                    logger.info("Saved redacted streaming conversation metadata")
            except Exception as e:
                logger.warning(f"History saving failed in stream: {e}")

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
