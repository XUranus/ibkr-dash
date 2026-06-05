import { request } from './http'
import type { PromptItem, PromptCreatePayload } from '@/types/adminPrompts'

export async function fetchAdminPrompts(promptKey?: string): Promise<PromptItem[]> {
  const query = promptKey ? `?prompt_key=${encodeURIComponent(promptKey)}` : ''
  const response = await request<PromptItem[] | { items: PromptItem[] }>(`/api/admin/prompts${query}`)
  return Array.isArray(response) ? response : (response.items ?? [])
}

export function createAdminPrompt(payload: PromptCreatePayload): Promise<PromptItem> {
  return request<PromptItem>('/api/admin/prompts', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function fetchActivePrompt(promptKey: string): Promise<PromptItem> {
  return request<PromptItem>(`/api/admin/prompts/${encodeURIComponent(promptKey)}/active`)
}
