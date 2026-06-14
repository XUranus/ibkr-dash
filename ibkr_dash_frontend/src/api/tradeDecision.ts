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

export async function analyzeEntryDecision(payload: {
  symbol: string
  question?: string
}): Promise<TradeDecisionResult> {
  const raw = await request<Record<string, unknown>>('/api/trade-decision/analyze', {
    method: 'POST',
    body: JSON.stringify({
      symbol: payload.symbol,
      decision_type: 'entry_decision',
      question: payload.question || undefined,
    }),
  })
  return normalizeTradeDecisionResponse(raw)
}

export async function analyzeHoldingDecision(payload: {
  symbol: string
  question?: string
}): Promise<TradeDecisionResult> {
  const raw = await request<Record<string, unknown>>('/api/trade-decision/analyze', {
    method: 'POST',
    body: JSON.stringify({
      symbol: payload.symbol,
      decision_type: 'holding_decision',
      question: payload.question || undefined,
    }),
  })
  return normalizeTradeDecisionResponse(raw)
}

export async function fetchRecentTradeDecisions(params: { limit?: number; symbol?: string; decision_type?: string } = {}): Promise<TradeDecisionResult[]> {
  const response = await request<TradeDecisionListResponse>(`/api/trade-decision/decisions${toQueryString(params)}`)
  return response.items ?? []
}

export async function fetchTradeDecisionDetail(decisionId: string): Promise<TradeDecisionResult> {
  const raw = await request<Record<string, unknown>>(`/api/trade-decision/decisions/${encodeURIComponent(decisionId)}`)
  return normalizeTradeDecisionResponse(raw)
}

/** Flatten the backend response: merge decision_output fields to top level. */
function normalizeTradeDecisionResponse(raw: Record<string, unknown>): TradeDecisionResult {
  const output = raw.decision_output
  const flattened = typeof output === 'object' && output !== null
    ? { ...raw, ...(output as Record<string, unknown>) }
    : raw
  return flattened as unknown as TradeDecisionResult
}

export function fetchTradeDecisionReport(decisionId: string, lang: string = 'zh'): Promise<{ report: string }> {
  return request<{ report: string }>(`/api/trade-decision/decisions/${encodeURIComponent(decisionId)}/report?lang=${lang}`)
}
