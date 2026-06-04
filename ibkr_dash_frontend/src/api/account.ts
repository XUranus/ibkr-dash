import { request } from './http'
import type { AccountOverview } from '@/types/account'

export function fetchAccountOverview(): Promise<AccountOverview> {
  return request<AccountOverview>('/api/account/overview')
}

export function fetchLatestReportDate(): Promise<{ report_date: string }> {
  return request<{ report_date: string }>('/api/account/latest-report-date')
}
