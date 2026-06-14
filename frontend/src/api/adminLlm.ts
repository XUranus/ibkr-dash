import { request } from './http'
import type {
  LlmChatTestResponse,
  LlmHealth,
  LlmProvider,
  LlmProviderTestResponse,
} from '@/types/adminLlm'

export function fetchLlmHealth(): Promise<LlmHealth> {
  return request<LlmHealth>('/api/admin/llm/health')
}

export async function fetchLlmProviders(): Promise<LlmProvider[]> {
  // Backend returns a plain array, not { items: [...] }
  const response = await request<LlmProvider[] | { items: LlmProvider[] }>('/api/admin/llm/providers')
  return Array.isArray(response) ? response : (response.items ?? [])
}

export function testLlmProvider(prompt: string): Promise<LlmProviderTestResponse> {
  return request<LlmProviderTestResponse>('/api/admin/llm/test', {
    method: 'POST',
    body: JSON.stringify({ message: prompt }),
  })
}

export function testActiveLlmChat(message: string): Promise<LlmChatTestResponse> {
  return request<LlmChatTestResponse>('/api/admin/llm/test', {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}
