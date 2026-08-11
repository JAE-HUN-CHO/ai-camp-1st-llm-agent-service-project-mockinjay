# Parlant Session Integration Guide

## Overview

This document explains how to integrate frontend chat room creation with backend Parlant session management for proactive session initialization.

## Architecture

### Before Integration
1. Frontend creates room with local ID
2. Backend creates MongoDB room record
3. Parlant session created **lazily** on first message
4. Session cache: `frontend_session_id → parlant_session_id`

### After Integration
1. Frontend creates room and calls new endpoint
2. Backend creates MongoDB room record
3. **Parlant session created immediately**
4. Session cache populated proactively
5. Background polling started for the session
6. First message uses existing session (no delay)

## Backend Implementation

### 1. New Pydantic Models

**Location:** `/Users/apple/Coding/ai-camp-1st-llm-agent-service-project-mockinjay/backend/app/models/chat.py`

#### RoomCreateWithSession
```python
class RoomCreateWithSession(BaseModel):
    """Request model for creating room with Parlant session"""
    user_id: str
    room_name: Optional[str] = None
    profile: str = "general"  # For Parlant customer tags
    agent_type: Optional[str] = None  # "medical_welfare" or "research_paper"
    metadata: Optional[Dict[str, Any]] = {}
```

#### RoomResponseWithSession
```python
class RoomResponseWithSession(BaseModel):
    """Response model with Parlant session info"""
    room_id: str
    user_id: str
    room_name: Optional[str]
    created_at: datetime
    last_activity: datetime
    message_count: int
    metadata: Dict[str, Any]
    parlant_session_id: Optional[str]  # NEW
    parlant_customer_id: Optional[str]  # NEW
```

### 2. New API Endpoint

**Location:** `/Users/apple/Coding/ai-camp-1st-llm-agent-service-project-mockinjay/backend/app/api/rooms.py`

**Endpoint:** `POST /api/rooms/with-session`

**Features:**
- Creates MongoDB room record
- Creates Parlant customer (if needed) with profile tags
- Creates Parlant session for specified agent
- Populates session cache: `room_id → (parlant_session_id, customer_id)`
- Starts background polling task
- Returns both room and Parlant session IDs

**Request:**
```json
{
  "user_id": "user_123",
  "room_name": "Kidney Disease Discussion",
  "profile": "patient",
  "agent_type": "medical_welfare",
  "metadata": {
    "tags": ["kidney", "dialysis"]
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Room created successfully with Parlant session",
  "data": {
    "room_id": "room_a1b2c3d4-e5f6-7890",
    "user_id": "user_123",
    "room_name": "Kidney Disease Discussion",
    "created_at": "2025-01-26T10:30:00Z",
    "last_activity": "2025-01-26T10:30:00Z",
    "message_count": 0,
    "metadata": {
      "tags": ["kidney", "dialysis"],
      "agent_type": "medical_welfare",
      "profile": "patient"
    },
    "parlant_session_id": "ses_xyz789",
    "parlant_customer_id": "cus_abc123"
  }
}
```

### 3. How It Works

```python
# 1. Create MongoDB room
room_id = f"room_{uuid.uuid4()}"
await db_manager.db.chat_rooms.insert_one(room_doc)

# 2. Import appropriate Parlant agent
if agent_type == "medical_welfare":
    from Agent.medical_welfare.agent import MedicalWelfareAgent
    agent_class = MedicalWelfareAgent
elif agent_type == "research_paper":
    from Agent.research_paper.agent import ResearchPaperAgent
    agent_class = ResearchPaperAgent

# 3. Create AgentRequest with room_id as session_id
agent_request = AgentRequest(
    query="",  # Empty query for session creation
    session_id=room_id,  # Use room_id as session_id
    user_id=request.user_id,
    profile=request.profile,
    context={}
)

# 4. Initialize agent and create Parlant session
agent_instance = agent_class()
await agent_instance._initialize()

# 5. Create session (populates cache and starts polling)
parlant_session_id, customer_id, _ = await agent_instance._get_valid_parlant_session(agent_request)

# 6. Return session info to frontend
return {
    "room_id": room_id,
    "parlant_session_id": parlant_session_id,
    "parlant_customer_id": customer_id
}
```

## Frontend Integration

### 1. Update Room Creation Hook

**Location:** `/Users/apple/Coding/ai-camp-1st-llm-agent-service-project-mockinjay/new_frontend/src/hooks/useChatRooms.ts`

**Modify `createRoom` function:**

```typescript
const createRoom = useCallback(async (options: CreateRoomOptions = {}): Promise<ChatRoom> => {
  const now = new Date();

  // Generate frontend room ID (temporary)
  const tempRoomId = `room_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;

  // Call backend to create room with Parlant session
  try {
    const response = await api.post('/api/rooms/with-session', {
      user_id: getCurrentUserId(), // Get from auth context
      room_name: options.title || generateRoomTitle(options.agentType || 'auto'),
      profile: getUserProfile(), // Get from user context
      agent_type: options.agentType,
      metadata: {}
    });

    const { room_id, parlant_session_id, parlant_customer_id } = response.data.data;

    // Create room with backend-assigned ID
    const newRoom: ChatRoom = {
      id: room_id, // Use backend room_id
      title: options.title || generateRoomTitle(options.agentType || 'auto'),
      agentType: options.agentType || 'auto',
      messageCount: 0,
      createdAt: now,
      updatedAt: now,
      isPinned: false,
      isArchived: false,
      parlantSessionId: parlant_session_id, // Store session ID
      parlantCustomerId: parlant_customer_id
    };

    setRooms((prev) => [newRoom, ...prev]);
    setCurrentRoomId(newRoom.id);

    console.log('✅ Room created with Parlant session:', {
      room_id,
      parlant_session_id,
      agent_type: options.agentType
    });

    return newRoom;

  } catch (error) {
    console.error('Failed to create room with session:', error);

    // Fallback: Create room locally without Parlant session
    const fallbackRoom: ChatRoom = {
      id: tempRoomId,
      title: options.title || generateRoomTitle(options.agentType || 'auto'),
      agentType: options.agentType || 'auto',
      messageCount: 0,
      createdAt: now,
      updatedAt: now,
      isPinned: false,
      isArchived: false,
    };

    setRooms((prev) => [fallbackRoom, ...prev]);
    setCurrentRoomId(fallbackRoom.id);

    return fallbackRoom;
  }
}, []);
```

### 2. Update ChatRoom Type

**Location:** `/Users/apple/Coding/ai-camp-1st-llm-agent-service-project-mockinjay/new_frontend/src/types/chat.ts`

```typescript
export interface ChatRoom {
  id: string;
  title: string;
  agentType: AgentType | 'auto';
  messageCount: number;
  lastMessage?: string;
  lastMessageTime?: Date;
  createdAt: Date;
  updatedAt: Date;
  isPinned: boolean;
  isArchived: boolean;

  // NEW: Parlant session info
  parlantSessionId?: string;
  parlantCustomerId?: string;
}
```

### 3. Update API Service

**Location:** `/Users/apple/Coding/ai-camp-1st-llm-agent-service-project-mockinjay/new_frontend/src/services/api.ts`

Add helper function:

```typescript
export const createRoomWithSession = async (params: {
  user_id: string;
  room_name?: string;
  profile?: string;
  agent_type?: string;
  metadata?: Record<string, any>;
}) => {
  const response = await api.post('/api/rooms/with-session', params);
  return response.data;
};
```

### 4. Example Usage in ChatPage

```typescript
const handleCreateNewRoom = async (agentType?: AgentType) => {
  try {
    // Show loading state
    setIsCreatingRoom(true);

    // Create room with Parlant session
    const newRoom = await createRoom({
      agentType: agentType || 'auto',
      title: `${agentType} 상담`
    });

    // Room is ready with Parlant session
    // First message will use existing session (no delay)
    console.log('✅ Room ready:', newRoom);

  } catch (error) {
    console.error('Failed to create room:', error);
    toast.error('방 생성에 실패했습니다.');
  } finally {
    setIsCreatingRoom(false);
  }
};
```

## Benefits

### 1. Performance
- **First message latency reduced by ~2-5 seconds**
- No session creation overhead on first message
- Background polling already started

### 2. User Experience
- Instant first response
- No "setting up session" delay
- Smoother conversation flow

### 3. Reliability
- Session validation happens upfront
- Errors caught before user sends message
- Fallback mechanism if session creation fails

### 4. Architecture
- Clean separation: room creation = session creation
- Consistent session lifecycle
- Better resource management

## Error Handling

The endpoint implements graceful degradation:

```python
try:
    # Try to create Parlant session
    parlant_session_id, customer_id, _ = await agent._get_valid_parlant_session(request)
except Exception as e:
    # Log error but don't fail room creation
    logger.error(f"Failed to create Parlant session: {e}")
    # Room is still created, session will be created on first message
    parlant_session_id = None
    customer_id = None
```

**Result:** Room creation always succeeds, even if Parlant server is temporarily unavailable.

## Testing

### 1. Backend Test

```bash
curl -X POST http://localhost:8000/api/rooms/with-session \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "user_id": "user_123",
    "room_name": "Test Room",
    "profile": "patient",
    "agent_type": "medical_welfare"
  }'
```

Expected response:
```json
{
  "success": true,
  "message": "Room created successfully with Parlant session",
  "data": {
    "room_id": "room_...",
    "parlant_session_id": "ses_...",
    "parlant_customer_id": "cus_..."
  }
}
```

### 2. Check Logs

Backend logs should show:
```
INFO: Created room room_xxx for user user_123
INFO: Created Parlant session for room room_xxx: session=ses_yyy, customer=cus_zzz, agent=medical_welfare
INFO: Started continuous polling for session ses_yyy
```

### 3. Verify Session Cache

```python
# In agent.py
print(MedicalWelfareAgent._session_cache)
# Should contain: {'room_xxx': ('ses_yyy', 'cus_zzz')}

print(MedicalWelfareAgent._active_sessions)
# Should contain: {'ses_yyy': {...}}
```

## Migration Strategy

### Phase 1: Add New Endpoint (No Breaking Changes)
- Deploy backend with new `/api/rooms/with-session` endpoint
- Keep existing `/api/rooms` endpoint for compatibility
- Frontend can still use old endpoint

### Phase 2: Frontend Gradual Migration
- Update `useChatRooms` hook to use new endpoint
- Add fallback to old endpoint if new one fails
- Test with subset of users

### Phase 3: Full Migration
- Switch all frontend room creation to new endpoint
- Monitor error rates and performance
- Consider deprecating old endpoint

## Troubleshooting

### Issue: Parlant session creation fails

**Check:**
1. Parlant server running? `curl http://localhost:8801/api/agents`
2. Agent ID configured? Check `MedicalWelfareAgent._agent_id`
3. Database accessible? Check MongoDB connection
4. User has `parlant_customer_id`? Check user document

**Solution:**
- Room still created successfully
- Session will be created on first message (fallback)

### Issue: Session not found on first message

**Check:**
1. Session cache: `MedicalWelfareAgent._session_cache`
2. Room ID matches session ID in cache
3. Session not expired/deleted

**Solution:**
- Agent will automatically recover and create new session
- See `_get_valid_parlant_session()` stale session handling

## Related Files

### Backend
- `/backend/app/api/rooms.py` - New endpoint implementation
- `/backend/app/models/chat.py` - Request/response models
- `/backend/Agent/medical_welfare/agent.py` - Session creation logic
- `/backend/Agent/research_paper/agent.py` - Session creation logic

### Frontend
- `/new_frontend/src/hooks/useChatRooms.ts` - Room creation hook
- `/new_frontend/src/types/chat.ts` - ChatRoom type
- `/new_frontend/src/services/api.ts` - API client
- `/new_frontend/src/pages/ChatPageEnhanced.tsx` - Usage example

## API Reference

### POST /api/rooms/with-session

Creates a new chat room with proactive Parlant session initialization.

**Request:**
```typescript
{
  user_id: string;          // Required
  room_name?: string;       // Optional, auto-generated if not provided
  profile?: string;         // Optional, default: "general"
  agent_type?: string;      // Optional: "medical_welfare" | "research_paper"
  metadata?: object;        // Optional
}
```

**Response:**
```typescript
{
  success: boolean;
  message: string;
  data: {
    room_id: string;
    user_id: string;
    room_name: string;
    created_at: string;
    last_activity: string;
    message_count: number;
    metadata: object;
    parlant_session_id: string | null;
    parlant_customer_id: string | null;
  }
}
```

**Status Codes:**
- `201` - Room and session created successfully
- `400` - Invalid request or room limit exceeded
- `401` - Unauthorized
- `500` - Server error (room may still be created without session)

## Conclusion

This integration provides a seamless bridge between frontend room creation and Parlant session management, eliminating first-message latency and improving overall user experience.
