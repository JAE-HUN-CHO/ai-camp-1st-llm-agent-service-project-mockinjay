# Parlant 이벤트 스트리밍 시스템 통합 가이드

이 문서는 Parlant 에이전트의 이벤트 기반 아키텍처를 프로젝트에 통합하는 방법을 설명합니다.

## 개요

Parlant 에이전트는 메시지를 한 번에 전송하지 않고, 여러 이벤트로 나누어 스트리밍 방식으로 전송합니다. 이를 올바르게 처리하기 위해서는 이벤트 폴링과 상태 관리가 필요합니다.

## 핵심 개념

### 1. 이벤트 종류

Parlant는 다음과 같은 이벤트를 발행합니다:

- **message**: 에이전트가 생성한 메시지
- **status**: 에이전트의 현재 상태 (acknowledged, processing, typing, ready, error, cancelled)
- **tool**: 에이전트가 도구를 사용한 결과

### 2. 상태 이벤트 흐름

에이전트가 메시지를 생성하는 동안 다음과 같은 상태 순서로 진행됩니다:

```
acknowledged → processing → typing → ready
```

#### 상태별 의미:

1. **acknowledged**: 고객 메시지를 인지하고 응답 작업 시작
2. **processing**: 세션을 평가하고 적절한 응답 준비 중
3. **typing**: 메시지 생성 중
4. **ready**: 에이전트가 유휴 상태이며 새 이벤트를 받을 준비 완료

### 3. 메시지 분할 전송 (Message Splitting)

긴 메시지는 여러 부분으로 나뉘어 전송될 수 있습니다:

```
message (part 1) → ready → typing → message (part 2) → ready → ... → final ready
```

**중요**: 중간에 `ready` 상태가 발생하더라도, 이는 전체 응답이 완료된 것이 아니라 한 부분이 완료된 것일 수 있습니다.

### 4. Trace ID

모든 이벤트는 `correlation_id` (또는 `trace_id`)를 가지며, 이를 통해 관련 이벤트들을 그룹화할 수 있습니다.

```typescript
// trace_id 예시
"abc123::message-1"
"abc123::status-1"
"abc123::message-2"
```

`::` 앞부분 (`abc123`)이 동일한 trace의 이벤트들입니다.

## 구현 상세

### 1. 프론트엔드 폴링 로직 (ChatPage.tsx)

#### 개선된 폴링 알고리즘:

```typescript
const pollAgentUpdatesWithBackoff = async (state: SessionState) => {
  // Track active trace IDs to detect completion
  const activeTraceIds = new Set<string>()

  while (/* polling condition */) {
    const events = await parlClient.listEvents(sessionId, offset, 60)

    // Track message events by trace ID
    for (const event of events) {
      const traceId = event.correlation_id?.split('::')[0]

      if (event.kind === 'message' && event.source === 'agent') {
        activeTraceIds.add(traceId)
      }

      // Remove from active when ready status received
      if (event.kind === 'status' && event.data?.status === 'ready') {
        activeTraceIds.delete(traceId)
      }
    }

    // Only stop when ready AND no active traces
    const hasReadyStatus = events.some(e =>
      e.kind === 'status' && e.data?.status === 'ready'
    )

    if (hasReadyStatus && activeTraceIds.size === 0) {
      // All message parts completed
      break
    }
  }
}
```

#### 핵심 개선 사항:

1. **Trace ID 추적**: 활성 메시지 trace를 Set으로 관리
2. **완료 조건 개선**: `ready` 상태 + 활성 trace 0개일 때만 종료
3. **Long Polling 최적화**: `wait_for_data`를 60초로 증가 (Parlant 권장)

### 2. 메시지 추출 로직 (utils.ts)

```typescript
export function extractAssistantMessages(events: ParlantEvent[]): ChatMessage[] {
  const grouped = groupByCorrelation(events)

  for (const event of events) {
    if (event.kind !== 'message') continue

    const traceId = event.correlation_id?.split('::')[0]
    const statusEvents = grouped[traceId]?.filter(e => e.kind === 'status')
    const lastStatus = statusEvents?.[statusEvents.length - 1]

    const status = lastStatus?.data?.status || 'ready'

    // Message with status
    messages.push({
      role: 'assistant',
      text: extractText(event),
      status,
      correlationId: event.correlation_id
    })
  }

  return messages
}
```

#### 개선 사항:

1. **Trace 기반 그룹화**: `correlation_id`의 base 부분으로 이벤트 그룹화
2. **최신 상태 추적**: 동일 trace의 가장 최근 상태 이벤트 사용
3. **안전한 폴백**: 상태를 찾지 못하면 `ready`로 기본 설정

### 3. ParlantClient 설정

```typescript
async listEvents(
  sessionId: string,
  minOffset: number,
  waitForData = 60,  // Increased from 20
  kinds = 'message,status,tool'
): Promise<ParlantEvent[]> {
  const { data } = await this.axios.get(
    `/sessions/${sessionId}/events`,
    {
      params: {
        min_offset: minOffset,
        wait_for_data: waitForData,
        kinds
      }
    }
  )
  return data || []
}
```

## 테스트 시나리오

### 1. 단일 메시지 응답

```
User: "신장이식 후 관리 방법은?"
↓
Event: status (acknowledged)
Event: status (processing)
Event: status (typing)
Event: message ("신장이식 후에는...")
Event: status (ready)
```

**예상 동작**: ready 상태 수신 시 폴링 종료

### 2. 분할 메시지 응답

```
User: "상세한 식단 가이드 알려줘"
↓
Event: status (typing)
Event: message (part 1)
Event: status (ready)       ← 중간 ready
Event: status (typing)
Event: message (part 2)
Event: status (ready)       ← 최종 ready
```

**예상 동작**:
- 첫 번째 ready에서 trace 제거
- 두 번째 message로 새 trace 추가
- 두 번째 ready에서 trace 제거 + activeTraceIds.size === 0 → 폴링 종료

### 3. 도구 사용 포함 응답

```
User: "최신 논문 찾아줘"
↓
Event: status (processing)
Event: tool (search_medical_qa)
Event: status (typing)
Event: message ("다음 논문들을 찾았습니다...")
Event: status (ready)
```

**예상 동작**: ready 상태 수신 시 폴링 종료, 도구 결과는 extractPaperResults로 처리

## 디버깅 팁

### 1. 콘솔 로그 확인

```typescript
console.log('[ChatPage] poll got events', {
  count: events.length,
  activeTraces: activeTraceIds.size
})
```

- `activeTraces`가 0이 되는 시점 확인
- ready 상태 이벤트 발생 시점 확인

### 2. 네트워크 탭

- `/sessions/{id}/events` 요청 확인
- `min_offset`, `wait_for_data` 파라미터 확인
- 응답 데이터의 `correlation_id` 패턴 확인

### 3. 상태 전환 추적

```typescript
if (event.kind === 'status') {
  console.log('[Status]', {
    traceId,
    status: event.data?.status,
    activeTraces: Array.from(activeTraceIds)
  })
}
```

## 문제 해결

### Q1: 폴링이 너무 일찍 종료됩니다

**원인**: 분할 메시지의 중간 `ready` 상태에서 종료

**해결**: trace ID 추적 로직 확인
```typescript
// ❌ 잘못된 방법
if (hasReadyStatus) break

// ✅ 올바른 방법
if (hasReadyStatus && activeTraceIds.size === 0) break
```

### Q2: 폴링이 너무 오래 실행됩니다

**원인**: trace ID가 제대로 제거되지 않음

**해결**: ready 이벤트에서 trace 제거 로직 확인
```typescript
if (event.kind === 'status' && event.data?.status === 'ready') {
  const traceId = event.correlation_id?.split('::')[0]
  activeTraceIds.delete(traceId)
}
```

### Q3: 메시지가 중복으로 표시됩니다

**원인**: 동일한 offset의 이벤트를 여러 번 읽음

**해결**: offset 업데이트 로직 확인
```typescript
const latestOffset = Math.max(...events.map(e => e.offset || -1))
offset = latestOffset + 1  // 다음 offset으로 이동
```

## 참고 자료

- [Parlant Sessions 문서](https://docs.parlant.io/concepts/sessions)
- [Parlant 이벤트 종류](https://docs.parlant.io/concepts/sessions#event-types)
- [Long Polling 베스트 프랙티스](https://docs.parlant.io/concepts/sessions#polling)

## 다음 단계

1. **에러 처리 강화**: 네트워크 에러, 타임아웃 등 예외 상황 처리
2. **재시도 로직**: 실패한 폴링 요청 재시도
3. **최적화**: 백오프 알고리즘 튜닝
4. **모니터링**: 폴링 성능 메트릭 수집
