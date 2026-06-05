import { request } from './http'
import type { IbkrSettings, IbkrSettingsUpdate, IbkrTestResponse } from '@/types/adminIbkr'

export function fetchIbkrSettings(): Promise<IbkrSettings> {
  return request<IbkrSettings>('/api/admin/ibkr/settings')
}

export function updateIbkrSettings(payload: IbkrSettingsUpdate): Promise<IbkrSettings> {
  return request<IbkrSettings>('/api/admin/ibkr/settings', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function testIbkrConnection(): Promise<IbkrTestResponse> {
  return request<IbkrTestResponse>('/api/admin/ibkr/test', {
    method: 'POST',
  })
}
