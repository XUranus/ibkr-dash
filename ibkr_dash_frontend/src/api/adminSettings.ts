import { request } from './http'

export interface SettingItem {
  key: string
  label: string
  value: string
  display_value: string
  type: string
  default: string
  is_set: boolean
}

export interface SettingsByCategory {
  [category: string]: SettingItem[]
}

export function fetchAllSettings(): Promise<SettingsByCategory> {
  return request<SettingsByCategory>('/api/admin/settings')
}

export function updateSettings(settings: Record<string, string>): Promise<{ updated: number }> {
  return request<{ updated: number }>('/api/admin/settings', {
    method: 'PUT',
    body: JSON.stringify(settings),
  })
}

export function resetSettings(keys?: string[]): Promise<{ reset: number }> {
  return request<{ reset: number }>('/api/admin/settings/reset', {
    method: 'POST',
    body: JSON.stringify({ keys: keys || null }),
  })
}
