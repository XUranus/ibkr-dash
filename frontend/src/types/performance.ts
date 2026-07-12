/** Performance types. */

export type AccountPerformanceDataQuality = 'complete' | 'partial' | 'missing'

export interface AccountPerformancePoint {
  date: string
  nav: number | null
  net_cash_flow: number
  investment_pnl: number | null
  daily_return: number | null
  twr_index: number | null
  data_quality: AccountPerformanceDataQuality
  data_limitations: string[]
}

export interface AccountPerformanceSummary {
  start_date: string | null
  end_date: string | null
  start_nav: number | null
  end_nav: number | null
  total_net_cash_flow: number
  money_gain: number | null
  twr_total_return: number | null
  annualized_return: number | null
  max_drawdown: number | null
  volatility: number | null
  sharpe_ratio: number | null
  data_quality: AccountPerformanceDataQuality
  data_limitations: string[]
}

export interface PerformanceMethodology {
  return_method: string
  cashflow_adjusted: boolean
  base_index: number
}

export interface PerformanceSeriesResponse {
  summary: AccountPerformanceSummary
  series: AccountPerformancePoint[]
  methodology: PerformanceMethodology
}
