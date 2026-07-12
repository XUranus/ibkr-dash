/** Market event types. */

export type MarketEventCategory =
  | 'MACRO' | 'FED' | 'COMPANY' | 'MARKET' | 'NEWS' | 'CRYPTO' | 'POLICY' | 'MANUAL'

export type MarketEventImportance = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export interface MarketEvent {
  id: string
  event_type: string
  category: string
  title: string
  title_en?: string
  scheduled_at: string
  importance: MarketEventImportance
  source: string
  description?: string
  created_at?: string
}

export interface MarketEventAnalysis {
  id: string
  content_zh: string
  content_en: string
  event_ids: string
  created_at: string
}
