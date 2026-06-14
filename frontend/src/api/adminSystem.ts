import { request } from './http'
import type { AdminSystemStatus } from '@/types/adminSystem'

export function fetchSystemStatus(): Promise<AdminSystemStatus> {
  return request<AdminSystemStatus>('/api/admin/system/status')
}
