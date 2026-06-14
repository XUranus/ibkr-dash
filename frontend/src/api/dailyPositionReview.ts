import { request } from './http'
import type {
  DailyPositionReviewDateListResponse,
  DailyPositionReviewHealth,
  DailyPositionReviewListResponse,
  DailyPositionReviewResult,
} from '@/types/dailyPositionReview'

function toQueryString(params: Record<string, string | number | undefined | null>): string {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.set(key, String(value))
    }
  })
  const queryStr = searchParams.toString()
  return queryStr ? `?${queryStr}` : ''
}

export function fetchDailyPositionReviewHealth(): Promise<DailyPositionReviewHealth> {
  return request<DailyPositionReviewHealth>('/api/daily-position-review/health')
}

export async function fetchDailyPositionReviewDates(limit = 60): Promise<string[]> {
  const response = await request<DailyPositionReviewDateListResponse>(
    `/api/daily-position-review/dates${toQueryString({ limit })}`,
  )
  return response.items ?? []
}

export async function fetchDailyPositionReview(reportDate: string): Promise<DailyPositionReviewResult> {
  const raw = await request<Record<string, unknown>>(`/api/daily-position-review/reviews/${encodeURIComponent(reportDate)}`)
  return normalizeDailyReviewResponse(raw)
}

export async function fetchRecentDailyPositionReviews(limit = 20): Promise<DailyPositionReviewResult[]> {
  const response = await request<DailyPositionReviewListResponse>(
    `/api/daily-position-review/reviews${toQueryString({ limit })}`,
  )
  return response.items ?? []
}

export async function startDailyPositionReviewTask(reportDate: string): Promise<DailyPositionReviewResult> {
  const raw = await request<Record<string, unknown>>('/api/daily-position-review/generate', {
    method: 'POST',
    body: JSON.stringify({ report_date: reportDate }),
  })
  return normalizeDailyReviewResponse(raw)
}

/** Flatten the backend response: merge review_output fields to top level. */
function normalizeDailyReviewResponse(raw: Record<string, unknown>): DailyPositionReviewResult {
  const output = raw.review_output
  const flattened = typeof output === 'object' && output !== null
    ? { ...raw, ...(output as Record<string, unknown>) }
    : raw
  return flattened as unknown as DailyPositionReviewResult
}
