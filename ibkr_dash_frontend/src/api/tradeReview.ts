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

export function startSymbolReviewTask(payload: {
  symbol: string
  start_date?: string
  end_date?: string
}): Promise<TradeReviewResult> {
  return request<TradeReviewResult>('/api/trade-review/review', {
    method: 'POST',
    body: JSON.stringify({
      symbol: payload.symbol,
      start_date: payload.start_date || undefined,
      end_date: payload.end_date || undefined,
    }),
  })
}

export function startSingleTradeReviewTask(tradeId: string, symbol: string): Promise<TradeReviewResult> {
  return request<TradeReviewResult>('/api/trade-review/review', {
    method: 'POST',
    body: JSON.stringify({ symbol, trade_id: tradeId }),
  })
}

export async function fetchRecentTradeReviews(params: { limit?: number; symbol?: string; review_type?: string } = {}): Promise<TradeReviewResult[]> {
  const response = await request<TradeReviewListResponse>(`/api/trade-review/reviews${toQueryString(params)}`)
  return response.items ?? []
}

export function fetchTradeReviewDetail(reviewId: string): Promise<TradeReviewResult> {
  return request<TradeReviewResult>(`/api/trade-review/reviews/${encodeURIComponent(reviewId)}`)
}

export function fetchTradeReviewReport(reviewId: string, lang: string = 'zh'): Promise<{ report: string }> {
  return request<{ report: string }>(`/api/trade-review/reviews/${encodeURIComponent(reviewId)}/report?lang=${lang}`)
}
