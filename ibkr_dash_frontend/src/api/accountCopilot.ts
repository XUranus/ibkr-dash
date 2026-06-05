import { request } from './http'

export interface CopilotSession {
  session_id: string
  title: string
  created_at: string
  message_count: number
}

export interface CopilotMessage {
  id: number
  session_id: string
  role: string
  content: string
  metadata: Record<string, unknown> | null
  created_at: string
}

export interface CopilotChatResponse {
  session_id: string
  run_id: string
  answer: string
  actions: Record<string, unknown>[]
  tool_calls: Record<string, unknown>[]
  pending_approval: Record<string, unknown> | null
  errors: string[]
}

export async function listSessions(limit = 20): Promise<CopilotSession[]> {
  const response = await request<CopilotSession[] | { items: CopilotSession[] }>(
    `/api/copilot/sessions?limit=${limit}`,
  )
  return Array.isArray(response) ? response : (response.items ?? [])
}

export function chat(sessionId: string | null, message: string): Promise<CopilotChatResponse> {
  return request<CopilotChatResponse>('/api/copilot/chat', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, message }),
  })
}

export async function listMessages(sessionId: string, limit = 100): Promise<CopilotMessage[]> {
  const response = await request<CopilotMessage[] | { items: CopilotMessage[] }>(
    `/api/copilot/sessions/${encodeURIComponent(sessionId)}/messages?limit=${limit}`,
  )
  return Array.isArray(response) ? response : (response.items ?? [])
}

export function deleteSession(sessionId: string): Promise<void> {
  return request<void>(`/api/copilot/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  })
}
