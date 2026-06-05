import { request } from './http'
import type { EmailSettings, EmailSettingsUpdate, EmailTestResponse } from '@/types/adminEmail'

export function fetchEmailSettings(): Promise<EmailSettings> {
  return request<EmailSettings>('/api/admin/email/settings')
}

export function updateEmailSettings(payload: EmailSettingsUpdate): Promise<EmailSettings> {
  return request<EmailSettings>('/api/admin/email/settings', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function sendEmailTest(): Promise<EmailTestResponse> {
  return request<EmailTestResponse>('/api/admin/email/test', {
    method: 'POST',
  })
}
