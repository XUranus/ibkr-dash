import { request } from './http'
import type { DividendListResponse, DividendSummaryResponse } from '@/types/dividends'

export interface DividendQuery {
  start_date?: string
  end_date?: string
  currency?: string
  symbol?: string
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

export function fetchDividends(params: DividendQuery): Promise<DividendListResponse> {
  return request<DividendListResponse>(`/api/dividends${toQueryString(params)}`)
}

export function fetchDividendSummary(
  params: Omit<DividendQuery, 'sort_by' | 'sort_order' | 'page' | 'page_size'>,
): Promise<DividendSummaryResponse> {
  return request<DividendSummaryResponse>(`/api/dividends/summary${toQueryString(params)}`)
}
