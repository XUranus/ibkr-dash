import type { PaginationInfo } from './common'

export interface CashFlowItem {
  account_id: string
  currency: string | null
  description: string | null
  date_time: string | null
  settle_date: string | null
  available_for_trading_date: string | null
  amount: number | null
  flow_direction: string | null
  flow_type: string | null
  transaction_id: string | null
  report_date: string | null
  client_reference: string | null
}

export interface CashFlowListResponse {
  items: CashFlowItem[]
  pagination: PaginationInfo
}

export interface CashFlowSummaryResponse {
  record_count: number
  deposit_count: number
  withdrawal_count: number
  total_deposit_amount: number | null
  total_withdrawal_amount: number | null
  net_amount: number | null
  by_currency: CashFlowCurrencySummaryItem[]
}

export interface CashFlowCurrencySummaryItem {
  currency: string | null
  record_count: number
  deposit_count: number
  withdrawal_count: number
  total_deposit_amount: number
  total_withdrawal_amount: number
  net_amount: number
}
