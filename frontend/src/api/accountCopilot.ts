import { request } from './http'
import type {
  AgentMonitoringOverviewResponse,
  AgentRecentLlmCall,
  AgentRecentToolCall,
  AgentStructuredOutputEvent,
  CopilotToolReliabilityLatestResponse,
  CopilotToolReliabilityProbeResponse,
} from '@/types/accountCopilot'

export interface CopilotSession {
  session_id: string
  title: string
  created_at: string
  message_count: number
}

export interface CopilotMessage {
  id: number | string
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

// --- Agent Monitoring APIs ---

export function getAgentMonitoringOverview(params: { hours?: number; bucket?: string } = {}): Promise<AgentMonitoringOverviewResponse> {
  const qs = new URLSearchParams()
  if (params.hours) qs.set('hours', String(params.hours))
  if (params.bucket) qs.set('bucket', params.bucket)
  const text = qs.toString()
  return request<AgentMonitoringOverviewResponse>(`/api/copilot/monitoring/overview${text ? `?${text}` : ''}`)
}

export function getAgentRecentToolCalls(params: { limit?: number; agent_name?: string } = {}): Promise<{ items: AgentRecentToolCall[] }> {
  const qs = new URLSearchParams()
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.agent_name) qs.set('agent_name', params.agent_name)
  const text = qs.toString()
  return request<{ items: AgentRecentToolCall[] }>(`/api/copilot/monitoring/tool-calls${text ? `?${text}` : ''}`)
}

export function getAgentRecentLlmCalls(params: { limit?: number; agent_name?: string } = {}): Promise<{ items: AgentRecentLlmCall[] }> {
  const qs = new URLSearchParams()
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.agent_name) qs.set('agent_name', params.agent_name)
  const text = qs.toString()
  return request<{ items: AgentRecentLlmCall[] }>(`/api/copilot/monitoring/llm-calls${text ? `?${text}` : ''}`)
}

export function getStructuredOutputRecent(params: { limit?: number; agent_name?: string } = {}): Promise<{ items: AgentStructuredOutputEvent[] }> {
  const qs = new URLSearchParams()
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.agent_name) qs.set('agent_name', params.agent_name)
  const text = qs.toString()
  return request<{ items: AgentStructuredOutputEvent[] }>(`/api/copilot/monitoring/structured-output${text ? `?${text}` : ''}`)
}

export function getToolReliabilityLatest(): Promise<CopilotToolReliabilityLatestResponse> {
  return request<CopilotToolReliabilityLatestResponse>('/api/copilot/monitoring/tool-reliability/latest')
}

export function runToolReliabilityProbe(payload: {
  include_live?: boolean
  include_longbridge?: boolean
  include_ibkr?: boolean
  include_agent_eval?: boolean
  symbol?: string
  keyword?: string
  max_tools?: number
}): Promise<CopilotToolReliabilityProbeResponse> {
  return request<CopilotToolReliabilityProbeResponse>('/api/copilot/monitoring/tool-reliability/probe', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
