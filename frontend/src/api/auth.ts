import { request } from './http'
import type { AuthSession } from '@/types/auth'

export function fetchAuthSession(): Promise<AuthSession> {
  return request<AuthSession>('/api/auth/session')
}

export function login(payload: { username: string; password: string }): Promise<AuthSession> {
  return request<AuthSession>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function logout(): Promise<AuthSession> {
  return request<AuthSession>('/api/auth/logout', {
    method: 'POST',
  })
}
