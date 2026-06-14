import { request } from './http'

export interface MarketEvent {
  id: string
  event_type: string
  category: string
  title: string
  title_en: string | null
  scheduled_at: string
  importance: string
  source: string
  description: string | null
}

export interface MarketEventResponse {
  items: MarketEvent[]
  total: number
}

export function fetchUpcomingEvents(days: number = 30): Promise<MarketEventResponse> {
  return request<MarketEventResponse>(`/api/market-events/upcoming?days=${days}&limit=20`)
}

export function fetchTodayEvents(): Promise<MarketEventResponse> {
  return request<MarketEventResponse>('/api/market-events/today')
}

export function seedMarketEvents(): Promise<{ seeded: number }> {
  return request<{ seeded: number }>('/api/market-events/seed', { method: 'POST' })
}
