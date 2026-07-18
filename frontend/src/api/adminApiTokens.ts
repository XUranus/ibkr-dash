import { request } from './http'

export interface ApiToken {
  id: number
  token?: string
  token_preview?: string
  name: string
  description: string
  scopes: string[] | string
  last_used_at: string | null
  expires_at: string | null
  revoked: boolean
  created_at: string | null
}

export interface CreateTokenRequest {
  name: string
  description?: string
  scopes?: string[]
  expires_at?: string | null
}

export function listApiTokens(): Promise<ApiToken[]> {
  return request<ApiToken[]>('/api/admin/api-tokens')
}

export function createApiToken(req: CreateTokenRequest): Promise<ApiToken> {
  return request<ApiToken>('/api/admin/api-tokens', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function revokeApiToken(tokenId: number): Promise<{ success: boolean }> {
  return request<{ success: boolean }>(`/api/admin/api-tokens/${tokenId}/revoke`, {
    method: 'POST',
  })
}

export function deleteApiToken(tokenId: number): Promise<{ success: boolean }> {
  return request<{ success: boolean }>(`/api/admin/api-tokens/${tokenId}`, {
    method: 'DELETE',
  })
}
