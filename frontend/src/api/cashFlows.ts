import { request } from './http'
import type { CashFlowListResponse, CashFlowSummaryResponse } from '@/types/cashFlows'

export interface CashFlowQuery {
  start_date?: string
  end_date?: string
  currency?: string
  flow_direction?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

function toQueryString(params: Record<string, any>): string {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') {
      searchParams.set(key, String(value))
    }
  })
  const qs = searchParams.toString()
  return qs ? `?${qs}` : ''
}

export function fetchCashFlows(params: CashFlowQuery): Promise<CashFlowListResponse> {
  return request<CashFlowListResponse>(`/api/cash-flows${toQueryString(params)}`)
}

export function fetchCashFlowSummary(
  params: Omit<CashFlowQuery, 'sort_by' | 'sort_order' | 'page' | 'page_size'>,
): Promise<CashFlowSummaryResponse> {
  return request<CashFlowSummaryResponse>(`/api/cash-flows/summary${toQueryString(params)}`)
}
