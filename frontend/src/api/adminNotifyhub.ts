import { request } from './http'
import type { NotifyHubSettings, NotifyHubSettingsUpdate, NotifyHubTestResponse } from '@/types/adminNotifyhub'

export function fetchNotifyHubSettings(): Promise<NotifyHubSettings> {
  return request<NotifyHubSettings>('/api/admin/notifyhub/settings')
}

export function updateNotifyHubSettings(payload: NotifyHubSettingsUpdate): Promise<NotifyHubSettings> {
  return request<NotifyHubSettings>('/api/admin/notifyhub/settings', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function testNotifyHub(): Promise<NotifyHubTestResponse> {
  return request<NotifyHubTestResponse>('/api/admin/notifyhub/test', {
    method: 'POST',
  })
}
