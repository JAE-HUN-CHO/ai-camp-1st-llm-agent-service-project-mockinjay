/**
 * Intent-based Router Service
 * 의도분류 기반 라우팅 및 응답 생성
 */

import type { IntentCategory } from '../types';
import { INTENT_CLASSIFICATIONS } from '../types';
import { env } from '../config/env';
import { getAccessToken } from '../shared/auth/token';
import {
  applyChatStreamFrame,
  applyChatTransportDone,
  assertChatStreamSucceeded,
  createChatStreamState,
  type ChatStreamFrame,
} from './chatStreamContract';

/**
 * 클라이언트 메시지에 사용할 고유 식별자를 생성합니다.
 *
 * @returns 생성된 UUID
 */
function createClientMessageId(): string {
  return globalThis.crypto.randomUUID();
}

export type AgentType = 'medical_welfare' | 'nutrition' | 'research_paper' | 'router';

export interface RouterResponse {
  /** 응답 내용 */
  content: string;
  /** 감지된 의도 (백엔드에서 분류됨) */
  intents: IntentCategory[];
  /** 사용된 에이전트 */
  agents: AgentType[];
  /** 신뢰도 (0-1) */
  confidence: number;
  /** 라우터가 직접 응답했는지 여부 */
  isDirectResponse: boolean;
  /** 응급 상황 여부 */
  isEmergency: boolean;
}

/**
 * 백엔드 스트리밍 응답 형식
 */
export interface BackendStreamChunk extends ChatStreamFrame {
  /** 응답 내용 */
  content?: string;
  answer?: string;
  response?: string;
  /** 스트리밍 상태 */
  status?: ChatStreamFrame['status'];
  /** 에이전트 타입 */
  agent_type?: string;
  /** 메타데이터 (의도 정보 포함) */
  metadata?: {
    routed_to?: string[];
    synthesis?: boolean;
    individual_responses?: Record<string, string>;
  };
  /** 에러 메시지 */
  error?: string;
  is_emergency?: boolean;
}

/**
 * 의도 감지 함수 (간소화됨 - 응급 상황만 프론트에서 체크)
 * 나머지 의도 분류는 백엔드 RouterAgent의 LLM이 처리합니다.
 */
export function detectIntent(text: string): IntentCategory[] {
  void text;
  // Emergency decisions are authoritative only at the backend policy boundary.
  return [];
}

/**
 * 간단한 의도에 대한 직접 응답 생성
 * (간소화됨 - 백엔드가 대부분 처리하므로 제거됨)
 * 레거시 호환성을 위해 주석으로 남김
 */
// function generateDirectResponse(_intent: IntentCategory): string | null {
//   return null;
// }

/**
 * 의도에 따른 에이전트 선택
 * (간소화됨 - 백엔드 RouterAgent가 처리하므로 제거됨)
 * 레거시 호환성을 위해 주석으로 남김
 */
// function selectAgents(_intents: IntentCategory[]): AgentType[] {
//   return [];
// }

/**
 * False Negative 방지를 위한 Disclaimer 추가
 */
function addMedicalDisclaimer(content: string, intents: IntentCategory[]): string {
  const needsDisclaimer = intents.some(
    (intent) => INTENT_CLASSIFICATIONS[intent].requiresStrictValidation
  );

  if (!needsDisclaimer) return content;

  return `${content}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ **중요 안내사항**
본 답변은 진단이나 치료를 대체할 수 없으며, 참고용 정보입니다.
증상이 지속되거나 악화되면 반드시 의료진과 상담하세요.

응급 상황 시 즉시 119에 연락하거나 가까운 병원을 방문하시기 바랍니다.`;
}

/**
 * 지정된 에이전트로 백엔드에 질의를 보내 응답 내용을 가져옵니다.
 *
 * @param agent - `router`인 경우 자동 에이전트 선택을 요청합니다.
 * @returns 백엔드의 응답 내용
 * @throws 백엔드 요청이 실패한 경우
 */
async function callBackendAgent(
  query: string,
  agent: AgentType
): Promise<string> {
  const token = getAccessToken();
  const headers: Record<string, string> = {'Content-Type': 'application/json'};
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${env.apiBaseUrl}/api/chat/message`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      query: query,
      agent_type: agent === 'router' ? 'auto' : agent,
      session_id: 'default',
      client_message_id: createClientMessageId(),
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const data = await response.json();
  const content = data.response || data.answer || '응답을 받지 못했습니다.';

  return content;
}

/**
 * 스트리밍 호출 옵션
 */
export interface StreamCallOptions {
  sessionId?: string;
  userId?: string;
  roomId?: string;
  userProfile?: 'general' | 'patient' | 'researcher';
  clientMessageId?: string;
}

/**
 * 백엔드 스트리밍 API를 호출하여 응답을 실시간으로 전달하고 라우팅 결과를 수집합니다.
 *
 * @param query - 사용자 질문
 * @param agent - 요청에 사용할 에이전트 유형
 * @param onChunk - 수신한 응답 내용과 스트림 상태를 전달하는 콜백
 * @param onError - 요청 또는 스트림 처리 중 오류가 발생할 때 호출할 선택적 콜백
 * @param options - 세션, 사용자, 방, 프로필 및 클라이언트 메시지 ID 설정
 * @returns 감지된 에이전트, 의도 범주 및 긴급 응답 여부
 * @throws 백엔드 요청, SSE 프레임 파싱 또는 스트림 완료 검증에 실패한 경우
 */
export async function callBackendAgentStream(
  query: string,
  agent: AgentType,
  onChunk: (content: string, isComplete: boolean, metadata?: BackendStreamChunk) => void,
  onError?: (error: Error) => void,
  options?: StreamCallOptions | 'general' | 'patient' | 'researcher',
  signal?: AbortSignal
): Promise<{ agents: AgentType[]; intents: IntentCategory[]; isEmergency: boolean }> {
  // 하위 호환성: options가 문자열(userProfile)인 경우 처리
  let sessionId = 'default';
  let userId: string | undefined;
  let roomId: string | undefined;
  let userProfile: 'general' | 'patient' | 'researcher' = 'general';
  let clientMessageId = createClientMessageId();

  if (typeof options === 'string') {
    userProfile = options;
  } else if (options) {
    sessionId = options.sessionId || 'default';
    userId = options.userId;
    roomId = options.roomId;
    userProfile = options.userProfile || 'general';
    clientMessageId = options.clientMessageId || clientMessageId;
  }

  const authToken = getAccessToken();

  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
    }

    const response = await fetch(`${env.apiBaseUrl}/api/chat/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        query: query,
        agent_type: agent === 'router' ? 'auto' : agent,
        session_id: sessionId,
        user_id: userId,
        room_id: roomId,
        user_profile: userProfile,
        client_message_id: clientMessageId,
      }),
      signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is null');
    }

    const decoder = new TextDecoder();
    let streamState = createChatStreamState();
    let detectedAgents: AgentType[] = [];
    let detectedIntents: IntentCategory[] = [];
    let isEmergency = false;
    let sseBuffer = '';

    const processEvent = (frame: string): boolean => {
      const dataLines = frame
        .split('\n')
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).replace(/^ /, ''));
      if (dataLines.length === 0) return false;

      const data = dataLines.join('\n');
      if (data === '[DONE]') {
        streamState = applyChatTransportDone(streamState);
        assertChatStreamSucceeded(streamState);
        return true;
      }

      let parsed: BackendStreamChunk;
      try {
        parsed = JSON.parse(data) as BackendStreamChunk;
      } catch (error) {
        throw new Error('Invalid SSE JSON frame', { cause: error });
      }
      streamState = applyChatStreamFrame(streamState, parsed);
      if (streamState.terminal === 'error') {
        throw new Error(streamState.error || 'Chat stream failed');
      }
      if (streamState.terminal === 'cancelled') {
        throw new Error(streamState.error || 'Chat stream cancelled');
      }

      isEmergency = isEmergency || parsed.is_emergency === true;
      if (parsed.metadata?.routed_to && parsed.metadata.routed_to.length > 0) {
        const validAgents: readonly AgentType[] = [
          'medical_welfare',
          'nutrition',
          'research_paper',
          'router',
        ];
        const routedAgents = parsed.metadata.routed_to
          .filter((agentName): agentName is string => typeof agentName === 'string')
          .filter((agentName): agentName is AgentType =>
            validAgents.includes(agentName as AgentType)
          );
        if (routedAgents.length > 0) {
          detectedAgents = routedAgents;
          detectedIntents = mapAgentsToIntents(routedAgents);
        }
      }

      if (parsed.agent_type) {
        const agentType = parsed.agent_type as AgentType;
        if (!detectedAgents.includes(agentType)) detectedAgents.push(agentType);
      }

      const content = parsed.content || parsed.answer || parsed.response || '';
      if (content && parsed.status !== 'processing' && parsed.status !== 'synthesizing') {
        onChunk(streamState.content, false, parsed);
      }
      return false;
    };

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        sseBuffer += decoder.decode();
        if (sseBuffer.trim() && processEvent(sseBuffer.replace(/\r\n/g, '\n'))) {
          onChunk(streamState.content, true);
          return { agents: detectedAgents, intents: detectedIntents, isEmergency };
        }
        assertChatStreamSucceeded(streamState);
        onChunk(streamState.content, true);
        break;
      }

      sseBuffer += decoder.decode(value, { stream: true });
      sseBuffer = sseBuffer.replace(/\r\n/g, '\n');
      let boundary = sseBuffer.indexOf('\n\n');
      while (boundary >= 0) {
        const frame = sseBuffer.slice(0, boundary);
        sseBuffer = sseBuffer.slice(boundary + 2);
        if (processEvent(frame)) {
          onChunk(streamState.content, true);
          return { agents: detectedAgents, intents: detectedIntents, isEmergency };
        }
        boundary = sseBuffer.indexOf('\n\n');
      }
    }

    return { agents: detectedAgents, intents: detectedIntents, isEmergency };
  } catch (error) {
    if (onError) {
      onError(error as Error);
    }
    throw error;
  }
}

/**
 * 에이전트 타입을 의도 카테고리로 매핑
 */
function mapAgentsToIntents(agents: AgentType[]): IntentCategory[] {
  const intentMap: Record<AgentType, IntentCategory> = {
    'medical_welfare': 'MEDICAL_INFO',
    'nutrition': 'DIET_INFO',
    'research_paper': 'RESEARCH',
    'router': 'CHIT_CHAT',
  };

  return agents.map(agent => intentMap[agent] || 'CHIT_CHAT');
}

/**
 * 백엔드 RouterAgent를 통해 질의를 스트리밍 방식으로 처리합니다.
 *
 * @param query - 사용자 질문
 * @param onChunk - 스트리밍 콘텐츠와 완료 여부를 전달받는 콜백
 * @param onError - 스트리밍 오류를 전달받는 선택적 콜백
 * @param options - 세션, 사용자 및 스트리밍 관련 옵션
 * @param signal - 요청 취소에 사용하는 AbortSignal
 * @returns 스트리밍 콘텐츠, 감지된 의도와 에이전트, 신뢰도 및 응급 상태를 포함한 라우터 응답
 */
export async function routeQueryStream(
  query: string,
  onChunk: (content: string, isComplete: boolean) => void,
  onError?: (error: Error) => void,
  options?: StreamCallOptions | 'general' | 'patient' | 'researcher',
  signal?: AbortSignal
): Promise<RouterResponse> {
  // The backend EmergencySafetyPolicy runs before every model/agent/provider.
  let finalContent = '';
  let backendAgents: AgentType[] = [];
  let backendIntents: IntentCategory[] = [];
  let isEmergency = false;

  // A terminal error, cancellation, EOF, or transport-only [DONE] remains a
  // failure. ChatPage owns the explicit RESPONSE_GENERATION_FAILED bubble.
  const result = await callBackendAgentStream(
    query,
    'router', // 항상 router로 시작 (자동 분류)
    (content, isComplete) => {
      finalContent = content;
      onChunk(content, isComplete);
    },
    onError,
    options,
    signal
  );
  const { agents, intents } = result;
  isEmergency = result.isEmergency;

  // 타입 안전성을 위해 필터링
  backendAgents = agents.filter((a): a is AgentType =>
    ['medical_welfare', 'nutrition', 'research_paper', 'router'].includes(a)
  );
  backendIntents = intents.filter((i): i is IntentCategory =>
    ['NON_MEDICAL', 'ILLEGAL_REQUEST', 'MEDICAL_INFO', 'DIET_INFO', 'RESEARCH',
     'WELFARE_INFO', 'HEALTH_RECORD', 'LEARNING', 'POLICY', 'CHIT_CHAT'].includes(i)
  );

  // 3. Medical Disclaimer 추가 (필요 시)
  const finalIntents: IntentCategory[] = backendIntents.length > 0 ? backendIntents : ['CHIT_CHAT'];
  finalContent = addMedicalDisclaimer(finalContent, finalIntents);

  return {
    content: finalContent,
    intents: finalIntents,
    agents: backendAgents,
    confidence: 0.85,
    isDirectResponse: false,
    isEmergency,
  };
}

/**
 * 복합 의도 응답 생성 (여러 에이전트 결과 결합)
 * (간소화됨 - 백엔드 RouterAgent가 synthesis를 처리하므로 제거됨)
 * 레거시 호환성을 위해 주석으로 남김
 */
// async function combineAgentResponses(
//   query: string,
//   agents: AgentType[]
// ): Promise<string> {
//   // 백엔드 RouterAgent가 synthesis를 처리하므로 사용하지 않음
//   return '';
// }

/**
 * 메인 라우터 함수 (간소화됨 - 비스트리밍 버전)
 * Main router function (simplified - non-streaming version).
 *
 * 백엔드 RouterAgent가 의도를 분류하고 처리합니다.
 * Backend RouterAgent classifies intents and handles processing.
 *
 * 참고: 이 함수는 레거시 호환성을 위해 유지됩니다.
 * Note: This function is maintained for legacy compatibility.
 * 가능하면 routeQueryStream()을 사용하세요.
 * Use routeQueryStream() when possible for better user experience.
 *
 * @param query - 사용자 질문 (User query)
 * @returns 라우터 응답 객체 (Router response object)
 */
export async function routeQuery(query: string): Promise<RouterResponse> {
  // The backend EmergencySafetyPolicy is the single authoritative pre-filter.
  let content: string;
  try {
    content = await callBackendAgent(query, 'router');
  } catch (_error) {
    content = `죄송합니다. 백엔드 서버와 통신 중 오류가 발생했습니다.

**가능한 원인:**
- 백엔드 서버가 실행 중이 아닐 수 있습니다
- 네트워크 연결 문제일 수 있습니다

백엔드 서버를 확인해주세요: http://localhost:8000

응급 상황이라면 즉시 119에 연락하거나 가까운 병원을 방문하세요.`;

    return {
      content,
      intents: ['CHIT_CHAT'],
      agents: [],
      confidence: 0.0,
      isDirectResponse: true,
      isEmergency: false,
    };
  }

  // 3. Medical Disclaimer 추가
  // 참고: 비스트리밍 버전에서는 백엔드에서 의도 정보를 받을 수 없으므로
  // 의료 관련 키워드가 있으면 항상 disclaimer를 추가합니다.
  const medicalKeywords = ['증상', '치료', '투석', '질병', '진단', '약', '병원', '검사', '수치'];
  const hasMedicalContent = medicalKeywords.some(keyword => query.toLowerCase().includes(keyword));

  if (hasMedicalContent) {
    content = addMedicalDisclaimer(content, ['MEDICAL_INFO']);
  }

  return {
    content,
    intents: [], // 비스트리밍에서는 백엔드 의도를 받을 수 없음
    agents: ['router'],
    confidence: 0.85,
    isDirectResponse: false,
    isEmergency: false,
  };
}

/**
 * 의도별 추천 에이전트 반환
 */
export function getRecommendedAgent(intent: IntentCategory): AgentType {
  const classification = INTENT_CLASSIFICATIONS[intent];
  return classification.recommendedAgent || 'research_paper'; // 기본값은 research_paper
}
