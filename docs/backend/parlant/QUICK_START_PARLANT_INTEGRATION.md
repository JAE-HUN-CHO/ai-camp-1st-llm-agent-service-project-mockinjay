# Quick Start: Parlant Session Integration

## Summary

When a user creates a new chat room in the frontend, the backend now proactively creates a Parlant session instead of waiting for the first message.

## What Changed?

### Before
```
Frontend: Create room → Backend: Create MongoDB room → User sends first message → Backend: Create Parlant session (2-5s delay)
```

### After
```
Frontend: Create room → Backend: Create MongoDB room + Parlant session simultaneously → User sends first message → Instant response (0s delay)
```

## Quick Implementation

### 1. Backend Endpoint (Already Implemented)

**Endpoint:** `POST /api/rooms/with-session`

**Request:**
```json
{
  "user_id": "user_123",
  "agent_type": "medical_welfare",
  "profile": "patient"
}
```

**Response:**
```json
{
  "room_id": "room_abc123",
  "parlant_session_id": "ses_xyz789",
  "parlant_customer_id": "cus_def456"
}
```

### 2. Frontend Update (To Be Implemented)

Update your room creation function in `useChatRooms.ts`:

```typescript
// Before
const createRoom = useCallback((options: CreateRoomOptions = {}): ChatRoom => {
  const newRoom: ChatRoom = {
    id: `room_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`,
    // ... other fields
  };
  setRooms((prev) => [newRoom, ...prev]);
  return newRoom;
}, []);

// After
const createRoom = useCallback(async (options: CreateRoomOptions = {}): Promise<ChatRoom> => {
  try {
    // Call backend to create room with Parlant session
    const response = await api.post('/api/rooms/with-session', {
      user_id: getCurrentUserId(),
      room_name: options.title,
      profile: getUserProfile(),
      agent_type: options.agentType,
      metadata: {}
    });

    const { room_id, parlant_session_id } = response.data.data;

    const newRoom: ChatRoom = {
      id: room_id,  // Use backend room_id
      parlantSessionId: parlant_session_id,  // Store session ID
      // ... other fields
    };

    setRooms((prev) => [newRoom, ...prev]);
    return newRoom;
  } catch (error) {
    console.error('Failed to create room:', error);
    // Fallback to local room creation
  }
}, []);
```

## Key Files Modified

### Backend
- ✅ `/backend/app/models/chat.py` - Added `RoomCreateWithSession` and `RoomResponseWithSession` models
- ✅ `/backend/app/api/rooms.py` - Added `POST /api/rooms/with-session` endpoint

### Frontend (To Update)
- ⏳ `/new_frontend/src/hooks/useChatRooms.ts` - Update `createRoom` function
- ⏳ `/new_frontend/src/types/chat.ts` - Add `parlantSessionId` field to `ChatRoom`
- ⏳ `/new_frontend/src/services/api.ts` - Add helper function

## Testing

### 1. Test Backend Endpoint

```bash
# Replace YOUR_TOKEN with actual JWT token
curl -X POST http://localhost:8000/api/rooms/with-session \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "user_id": "675e123456789abcdef01234",
    "room_name": "Test Medical Welfare Chat",
    "profile": "patient",
    "agent_type": "medical_welfare"
  }'
```

### 2. Expected Response

```json
{
  "success": true,
  "message": "Room created successfully with Parlant session",
  "data": {
    "room_id": "room_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "user_id": "675e123456789abcdef01234",
    "room_name": "Test Medical Welfare Chat",
    "created_at": "2025-01-26T10:30:00Z",
    "last_activity": "2025-01-26T10:30:00Z",
    "message_count": 0,
    "metadata": {
      "agent_type": "medical_welfare",
      "profile": "patient"
    },
    "parlant_session_id": "ses_xyz789abc",
    "parlant_customer_id": "cus_abc123def"
  }
}
```

### 3. Check Backend Logs

You should see:
```
INFO: Created room room_a1b2c3d4-e5f6-7890 for user 675e123456789abcdef01234
INFO: Created Parlant session for room room_a1b2c3d4-e5f6-7890: session=ses_xyz789abc, customer=cus_abc123def, agent=medical_welfare
INFO: Started continuous polling for session ses_xyz789abc
```

## Benefits

1. **Performance**: First message latency reduced by 2-5 seconds
2. **UX**: No "setting up" delay for users
3. **Architecture**: Clean session lifecycle management
4. **Reliability**: Errors caught before user sends message

## Troubleshooting

### Backend endpoint returns 500

**Check Parlant server is running:**
```bash
curl http://localhost:8801/api/agents
```

If not running, start the Medical Welfare server:
```bash
cd /Users/apple/Coding/ai-camp-1st-llm-agent-service-project-mockinjay/backend/Agent/medical_welfare/server
python medical_welfare_server.py
```

### Room created but parlant_session_id is null

This is okay! The endpoint gracefully degrades:
- Room is still created successfully
- Parlant session will be created on first message (fallback behavior)
- Check logs for error details

### Frontend error: "user_id is required"

Make sure you're passing the user_id from the authenticated user:
```typescript
const { user } = useAuth();  // Get from auth context
const response = await api.post('/api/rooms/with-session', {
  user_id: user._id,  // MongoDB user ID
  // ...
});
```

## Next Steps

1. Update frontend `useChatRooms.ts` hook
2. Test room creation flow
3. Verify first message has no delay
4. Monitor error rates and performance

## Questions?

See full documentation: `/backend/docs/PARLANT_SESSION_INTEGRATION.md`
