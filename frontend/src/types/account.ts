export interface AccountDeltaMetric {
  amount_change: number | null
  percent_change: number | null
}

export interface AccountOverview {
  account_id: string
  report_date: string
  currency: string | null
  total_equity: number | null
  cash: number | null
  stock_value: number | null
  options_value: number | null
  funds_value: number | null
  crypto_value: number | null
  interest_accruals: number | null
  dividend_accruals: number | null
  margin_financing_charge_accruals: number | null
  fifo_total_realized_pnl: number | null
  fifo_total_unrealized_pnl: number | null
  fifo_total_pnl: number | null
  fifo_total_pnl_return_rate: number | null
  cnav_twr: number | null
  ytd_twr: number | null
  crtt_dividends_ytd: number | null
  crtt_broker_interest_ytd: number | null
  crtt_commissions_ytd: number | null
  total_equity_delta: AccountDeltaMetric | null
  fifo_total_realized_pnl_delta: AccountDeltaMetric | null
  fifo_total_unrealized_pnl_delta: AccountDeltaMetric | null
  fifo_total_pnl_delta: AccountDeltaMetric | null
}

export interface AccountSnapshot {
  report_date: string
  total_equity: number | null
  cash: number | null
  stock_value: number | null
}
