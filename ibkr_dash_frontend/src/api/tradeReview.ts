import { request } from './http'
import type { TradeReviewHealth, TradeReviewListResponse, TradeReviewResult } from '@/types/tradeReview'

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

export function fetchTradeReviewHealth(): Promise<TradeReviewHealth> {
  return request<TradeReviewHealth>('/api/trade-review/health')
}

export async function startSymbolReviewTask(payload: {
  symbol: string
  start_date?: string
  end_date?: string
}): Promise<TradeReviewResult> {
  const raw = await request<Record<string, unknown>>('/api/trade-review/review', {
    method: 'POST',
    body: JSON.stringify({
      symbol: payload.symbol,
      start_date: payload.start_date || undefined,
      end_date: payload.end_date || undefined,
    }),
  })
  return normalizeTradeReviewResponse(raw)
}

export async function startSingleTradeReviewTask(tradeId: string, symbol: string): Promise<TradeReviewResult> {
  const raw = await request<Record<string, unknown>>('/api/trade-review/review', {
    method: 'POST',
    body: JSON.stringify({ symbol, trade_id: tradeId }),
  })
  return normalizeTradeReviewResponse(raw)
}

export async function fetchRecentTradeReviews(params: { limit?: number; symbol?: string; review_type?: string } = {}): Promise<TradeReviewResult[]> {
  const response = await request<TradeReviewListResponse>(`/api/trade-review/reviews${toQueryString(params)}`)
  return response.items ?? []
}

export async function fetchTradeReviewDetail(reviewId: string): Promise<TradeReviewResult> {
  const raw = await request<Record<string, unknown>>(`/api/trade-review/reviews/${encodeURIComponent(reviewId)}`)
  return normalizeTradeReviewResponse(raw)
}

/** Flatten the backend response: merge review_output fields to top level. */
function normalizeTradeReviewResponse(raw: Record<string, unknown>): TradeReviewResult {
  const output = raw.review_output
  const flattened = typeof output === 'object' && output !== null
    ? { ...raw, ...(output as Record<string, unknown>) }
    : raw
  return flattened as unknown as TradeReviewResult
}

export function fetchTradeReviewReport(reviewId: string, lang: string = 'zh'): Promise<{ report: string }> {
  return request<{ report: string }>(`/api/trade-review/reviews/${encodeURIComponent(reviewId)}/report?lang=${lang}`)
}
