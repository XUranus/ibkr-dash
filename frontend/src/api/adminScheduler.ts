import { request } from './http'
import type { ImportHistoryResponse, TriggerAiReportResponse, TriggerImportResponse } from '@/types/adminScheduler'

export function triggerImport(): Promise<TriggerImportResponse> {
  return request<TriggerImportResponse>('/api/admin/scheduler/trigger-import', {
    method: 'POST',
  })
}

export function triggerAiReport(): Promise<TriggerAiReportResponse> {
  return request<TriggerAiReportResponse>('/api/admin/scheduler/trigger-ai-report', {
    method: 'POST',
  })
}

export function fetchImportHistory(limit = 100): Promise<ImportHistoryResponse> {
  return request<ImportHistoryResponse>(`/api/admin/scheduler/import-history?limit=${limit}`)
}
