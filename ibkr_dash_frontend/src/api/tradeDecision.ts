import { request } from './http'
import type { TradeDecisionHealth, TradeDecisionListResponse, TradeDecisionResult } from '@/types/tradeDecision'

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

export function fetchTradeDecisionHealth(): Promise<TradeDecisionHealth> {
  return request<TradeDecisionHealth>('/api/trade-decision/health')
}

export function analyzeEntryDecision(payload: {
  symbol: string
  question?: string
}): Promise<TradeDecisionResult> {
  return request<TradeDecisionResult>('/api/trade-decision/analyze', {
    method: 'POST',
    body: JSON.stringify({
      symbol: payload.symbol,
      decision_type: 'entry_decision',
      question: payload.question || undefined,
    }),
  })
}

export function analyzeHoldingDecision(payload: {
  symbol: string
  question?: string
}): Promise<TradeDecisionResult> {
  return request<TradeDecisionResult>('/api/trade-decision/analyze', {
    method: 'POST',
    body: JSON.stringify({
      symbol: payload.symbol,
      decision_type: 'holding_decision',
      question: payload.question || undefined,
    }),
  })
}

export async function fetchRecentTradeDecisions(params: { limit?: number; symbol?: string; decision_type?: string } = {}): Promise<TradeDecisionResult[]> {
  const response = await request<TradeDecisionListResponse>(`/api/trade-decision/decisions${toQueryString(params)}`)
  return response.items ?? []
}

export function fetchTradeDecisionDetail(decisionId: string): Promise<TradeDecisionResult> {
  return request<TradeDecisionResult>(`/api/trade-decision/decisions/${encodeURIComponent(decisionId)}`)
}

export function fetchTradeDecisionReport(decisionId: string, lang: string = 'zh'): Promise<{ report: string }> {
  return request<{ report: string }>(`/api/trade-decision/decisions/${encodeURIComponent(decisionId)}/report?lang=${lang}`)
}
