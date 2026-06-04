import { request } from './http'
import type {
  CopilotApprovalRequest,
  CopilotApprovalResponse,
  CopilotDemoSeedResponse,
  CopilotEvent,
  CopilotEventListResponse,
  CopilotHealthResponse,
  CopilotMemory,
  CopilotMemoryListResponse,
  CopilotMessageListResponse,
  CopilotRun,
  CopilotRunTraceResponse,
  CopilotSendMessageResponse,
  CopilotSendMessageStreamResponse,
  CopilotSession,
  CopilotSessionListResponse,
} from '@/types/accountCopilot'

function toQueryString(params: Record<string, string | number | boolean | undefined | null>): string {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.set(key, String(value))
    }
  })
  const qs = searchParams.toString()
  return qs ? `?${qs}` : ''
}

export function createSession(payload: { title?: string } = {}): Promise<CopilotSession> {
  return request<CopilotSession>('/api/agent/account-copilot/sessions', {
    method: 'POST',
    body: JSON.stringify({ title: payload.title || undefined }),
  })
}

export function getCopilotHealth(): Promise<CopilotHealthResponse> {
  return request<CopilotHealthResponse>('/api/agent/account-copilot/health')
}

export function seedDemoSession(): Promise<CopilotDemoSeedResponse> {
  return request<CopilotDemoSeedResponse>('/api/agent/account-copilot/demo/seed', { method: 'POST' })
}

export async function listSessions(limit = 20): Promise<CopilotSession[]> {
  const response = await request<CopilotSessionListResponse>(
    `/api/agent/account-copilot/sessions${toQueryString({ limit })}`,
  )
  return response.items
}

export function getSession(sessionId: string): Promise<CopilotSession> {
  return request<CopilotSession>(`/api/agent/account-copilot/sessions/${encodeURIComponent(sessionId)}`)
}

export function updateSession(sessionId: string, payload: { title?: string; status?: 'active' | 'archived' }): Promise<CopilotSession> {
  return request<CopilotSession>(`/api/agent/account-copilot/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export async function listMessages(sessionId: string, limit = 50): Promise<CopilotMessageListResponse['items']> {
  const response = await request<CopilotMessageListResponse>(
    `/api/agent/account-copilot/sessions/${encodeURIComponent(sessionId)}/messages${toQueryString({ limit })}`,
  )
  return response.items
}

export function sendMessage(sessionId: string, content: string): Promise<CopilotSendMessageResponse> {
  return request<CopilotSendMessageResponse>(
    `/api/agent/account-copilot/sessions/${encodeURIComponent(sessionId)}/messages`,
    { method: 'POST', body: JSON.stringify({ content }) },
  )
}

export function sendMessageStream(sessionId: string, content: string): Promise<CopilotSendMessageStreamResponse> {
  return request<CopilotSendMessageStreamResponse>(
    `/api/agent/account-copilot/sessions/${encodeURIComponent(sessionId)}/messages/stream`,
    { method: 'POST', body: JSON.stringify({ content }) },
  )
}

export function getRun(runId: string): Promise<CopilotRun> {
  return request<CopilotRun>(`/api/agent/account-copilot/runs/${encodeURIComponent(runId)}`)
}

export function getRunTrace(runId: string): Promise<CopilotRunTraceResponse> {
  return request<CopilotRunTraceResponse>(`/api/agent/account-copilot/runs/${encodeURIComponent(runId)}/trace`)
}

export function approveRun(runId: string, payload: CopilotApprovalRequest): Promise<CopilotApprovalResponse> {
  return request<CopilotApprovalResponse>(`/api/agent/account-copilot/runs/${encodeURIComponent(runId)}/approval`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function cancelRun(runId: string, reason?: string): Promise<CopilotRun> {
  return request<CopilotRun>(`/api/agent/account-copilot/runs/${encodeURIComponent(runId)}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })
}

export async function listRunEvents(
  runId: string,
  params: { after_seq?: number; limit?: number } = {},
): Promise<CopilotEvent[]> {
  const response = await request<CopilotEventListResponse>(
    `/api/agent/account-copilot/runs/${encodeURIComponent(runId)}/events/list${toQueryString({
      after_seq: params.after_seq,
      limit: params.limit,
    })}`,
  )
  return response.items
}

export async function listSessionMemories(
  sessionId: string,
  params: { limit?: number; memory_type?: string } = {},
): Promise<CopilotMemory[]> {
  const response = await request<CopilotMemoryListResponse>(
    `/api/agent/account-copilot/sessions/${encodeURIComponent(sessionId)}/memories${toQueryString({
      limit: params.limit,
      memory_type: params.memory_type,
    })}`,
  )
  return response.items
}

export function rebuildSessionMemories(sessionId: string): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(
    `/api/agent/account-copilot/sessions/${encodeURIComponent(sessionId)}/memories/rebuild`,
    { method: 'POST' },
  )
}
