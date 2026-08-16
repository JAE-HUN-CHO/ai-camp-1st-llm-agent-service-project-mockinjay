/**
 * Intent-based Router Service
 * 의도분류 기반 라우팅 및 응답 생성
 */

import type { IntentCategory } from '../types';
import { INTENT_CLASSIFICATIONS } from '../types';
import { env } from '../config/env';
import { getAccessToken } from '../shared/auth/token';

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
export interface BackendStreamChunk {
  /** 응답 내용 */
  content?: string;
  answer?: string;
  response?: string;
  /** 스트리밍 상태 */
  status?: 'streaming' | 'processing' | 'complete' | 'new_message';
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
 * 백엔드 API 호출
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
}

/**
 * 백엔드 스트리밍 API를 호출하고 의도 정보를 추출합니다.
 * Calls backend streaming API and extracts intent information.
 *
 * 실시간으로 응답 청크를 받아 콜백 함수로 전달합니다.
 * Receives response chunks in real-time and passes them to callback function.
 *
 * @param query - 사용자 질문 (User query)
 * @param agent - 사용할 에이전트 타입 (Agent type to use)
 * @param onChunk - 각 청크를 받을 때마다 호출되는 콜백 함수
 *                  Callback function called for each chunk
 * @param onError - 에러 발생 시 호출되는 콜백 함수 (선택)
 *                  Optional callback function for errors
 * @param options - 추가 옵션 (세션ID, 사용자ID, 방ID, 프로필)
 *                  Additional options (sessionId, userId, roomId, userProfile)
 * @param signal - 취소 시그널 (AbortSignal)
 * @returns 감지된 에이전트 목록과 의도 카테고리
 *          Detected agents list and intent categories
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

  if (typeof options === 'string') {
    userProfile = options;
  } else if (options) {
    sessionId = options.sessionId || 'default';
    userId = options.userId;
    roomId = options.roomId;
    userProfile = options.userProfile || 'general';
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
    let accumulatedContent = '';
    let detectedAgents: AgentType[] = [];
    let detectedIntents: IntentCategory[] = [];
    let isEmergency = false;

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        onChunk(accumulatedContent, true);
        break;
      }

      const chunk = decoder.decode(value, { stream: true });

      // SSE 형식 파싱: "data: {...}\n\n"
      const lines = chunk.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6); // "data: " 제거

          if (data === '[DONE]') {
            onChunk(accumulatedContent, true);
            return { agents: detectedAgents, intents: detectedIntents, isEmergency };
          }

          try {
            const parsed: BackendStreamChunk = JSON.parse(data);
            isEmergency = isEmergency || parsed.is_emergency === true;

            // 의도 정보 추출 (metadata.routed_to)
            // Extract intent information from metadata
            if (parsed.metadata?.routed_to && parsed.metadata.routed_to.length > 0) {
              // 유효한 에이전트 타입만 필터링 (Filter valid agent types only)
              const VALID_AGENTS: readonly AgentType[] = ['medical_welfare', 'nutrition', 'research_paper', 'router'];
              const routedAgents = parsed.metadata.routed_to
                .filter((agentName): agentName is string => typeof agentName === 'string')
                .filter((agentName): agentName is AgentType =>
                  VALID_AGENTS.includes(agentName as AgentType)
                ) as AgentType[];

              if (routedAgents.length > 0) {
                detectedAgents = routedAgents;
                detectedIntents = mapAgentsToIntents(routedAgents);
              }
            }

            // 에이전트 타입 추출
            if (parsed.agent_type && !detectedAgents.includes(parsed.agent_type as AgentType)) {
              const agentType = parsed.agent_type as AgentType;
              if (!detectedAgents.includes(agentType)) {
                detectedAgents.push(agentType);
              }
            }

            // 콘텐츠 추출
            let content = '';
            if (parsed.content) {
              content = parsed.content;
            } else if (parsed.answer) {
              content = parsed.answer;
            } else if (parsed.response) {
              content = parsed.response;
            }

            if (content) {
              // 스트리밍 청크인 경우 누적
              if (parsed.status === 'streaming') {
                accumulatedContent += content;
                onChunk(accumulatedContent, false, parsed);
              } else if (parsed.status === 'new_message') {
                // 새 메시지 - 줄바꿈으로 구분하여 누적
                if (accumulatedContent) {
                  accumulatedContent += '\n\n' + content;
                } else {
                  accumulatedContent = content;
                }
                onChunk(accumulatedContent, false, parsed);
              } else {
                // 완료, 성공, 또는 기타 상태인 경우 (complete, success, undefined 등)
                // Handle complete, success, or any other status
                accumulatedContent = content;
                onChunk(accumulatedContent, false, parsed);
              }
            }

            // 에러 처리
            if (parsed.error) {
              throw new Error(parsed.error);
            }
          } catch (_e) {
            // JSON 파싱 실패 시 무시 (불완전한 청크일 수 있음)
            // Ignore JSON parse failures (may be incomplete chunks)
          }
        }
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
 * 스트리밍 메인 라우터 함수 (간소화됨)
 * Main streaming router function (simplified).
 *
 * 백엔드 RouterAgent가 의도를 분류하고 처리합니다.
 * Backend RouterAgent classifies intents and handles processing.
 *
 * 프론트엔드는 응급 상황만 즉시 체크하고, 나머지는 백엔드로 전달합니다.
 * Frontend only checks emergency situations immediately, and forwards the rest to backend.
 *
 * @param query - 사용자 질문 (User query)
 * @param onChunk - 스트리밍 청크를 받을 콜백 함수
 *                  Callback function to receive streaming chunks
 * @param onError - 에러 처리 콜백 함수 (선택)
 *                  Optional error handling callback
 * @param options - 스트리밍 옵션 또는 사용자 프로필 (하위 호환성)
 *                  Streaming options or user profile (backward compatible)
 * @param signal - 취소 시그널 (AbortSignal)
 * @returns 라우터 응답 객체 (의도, 에이전트, 컨텐츠 등)
 *          Router response object (intents, agents, content, etc.)
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

  try {
    // 백엔드 스트리밍 호출 (의도 정보 추출)
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
  } catch (_error) {
    // 폴백: 응급 키워드만 체크하여 기본 응답
    const fallbackContent = `죄송합니다. 백엔드 서버와 통신 중 오류가 발생했습니다.

**가능한 원인:**
- 백엔드 서버가 실행 중이 아닐 수 있습니다
- 네트워크 연결 문제일 수 있습니다

백엔드 서버를 확인해주세요: http://localhost:8000

응급 상황이라면 즉시 119에 연락하거나 가까운 병원을 방문하세요.`;

    onChunk(fallbackContent, true);

    return {
      content: fallbackContent,
      intents: ['CHIT_CHAT'],
      agents: [],
      confidence: 0.0,
      isDirectResponse: true,
      isEmergency: false,
    };
  }

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
