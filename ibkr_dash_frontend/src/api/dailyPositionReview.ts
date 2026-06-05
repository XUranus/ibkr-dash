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

export function fetchDailyPositionReview(reportDate: string): Promise<DailyPositionReviewResult> {
  return request<DailyPositionReviewResult>(`/api/daily-position-review/reviews/${encodeURIComponent(reportDate)}`)
}

export async function fetchRecentDailyPositionReviews(limit = 20): Promise<DailyPositionReviewResult[]> {
  const response = await request<DailyPositionReviewListResponse>(
    `/api/daily-position-review/reviews${toQueryString({ limit })}`,
  )
  return response.items ?? []
}

export function startDailyPositionReviewTask(reportDate: string): Promise<DailyPositionReviewResult> {
  return request<DailyPositionReviewResult>('/api/daily-position-review/generate', {
    method: 'POST',
    body: JSON.stringify({ report_date: reportDate }),
  })
}
