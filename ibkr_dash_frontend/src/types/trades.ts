import type { PaginationInfo } from './common'

export interface TradeItem {
  account_id: string
  trade_date: string | null
  date_time: string | null
  currency: string | null
  symbol: string | null
  description: string | null
  asset_class: string | null
  buy_sell: string | null
  quantity: number | null
  trade_price: number | null
  proceeds: number | null
  ib_commission: number | null
  net_cash: number | null
  fifo_pnl_realized: number | null
  exchange: string | null
  order_type: string | null
  transaction_id: string | null
  trade_id: string | null
}

export interface TradeListResponse {
  items: TradeItem[]
  pagination: PaginationInfo
}

export interface TradeSummaryResponse {
  trade_count: number
  buy_count: number
  sell_count: number
  total_commission: number
  total_realized_pnl: number
  total_proceeds: number
  symbols_count: number
}
