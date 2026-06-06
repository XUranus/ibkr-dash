import type { AccountDeltaMetric, AccountOverview } from '@/types/account'
import { formatNumber, formatSignedNumber, formatSignedPercent, formatPercent } from './format'

export interface DashboardStatCard {
  title: string
  value: string
  helper?: string
  helperData?: Record<string, string>
  tone: 'neutral' | 'positive' | 'negative' | 'accent'
  deltaAmount?: string
  deltaPercent?: string
  deltaTone?: 'neutral' | 'positive' | 'negative' | 'accent'
}

function deltaTone(metric: AccountDeltaMetric | null): 'neutral' | 'positive' | 'negative' | 'accent' {
  if (!metric || !metric.amount_change) return 'neutral'
  return metric.amount_change > 0 ? 'positive' : 'negative'
}

function metricTone(value: number | null, fallback: 'neutral' | 'accent' = 'neutral'): 'neutral' | 'positive' | 'negative' | 'accent' {
  if (value === null || value === 0) return fallback
  return value > 0 ? 'positive' : 'negative'
}

export function buildDashboardStatCards(overview: AccountOverview): DashboardStatCard[] {
  return [
    {
      title: 'dashboard.totalEquity',
      value: formatNumber(overview.total_equity),
      helper: overview.report_date,
      tone: 'accent',
      deltaAmount: formatSignedNumber(overview.total_equity_delta?.amount_change ?? null),
      deltaPercent: formatSignedPercent(overview.total_equity_delta?.percent_change ?? null),
      deltaTone: deltaTone(overview.total_equity_delta),
    },
    { title: 'dashboard.cash', value: formatNumber(overview.cash), tone: 'neutral' },
    { title: 'dashboard.stockValue', value: formatNumber(overview.stock_value), tone: 'neutral' },
    {
      title: 'dashboard.realizedPnl',
      value: formatNumber(overview.fifo_total_realized_pnl),
      tone: overview.fifo_total_realized_pnl !== null && overview.fifo_total_realized_pnl < 0 ? 'negative' : 'positive',
    },
    {
      title: 'dashboard.unrealizedPnl',
      value: formatNumber(overview.fifo_total_unrealized_pnl),
      tone: overview.fifo_total_unrealized_pnl !== null && overview.fifo_total_unrealized_pnl < 0 ? 'negative' : 'positive',
    },
    {
      title: 'dashboard.totalPnl',
      value: formatNumber(overview.fifo_total_pnl),
      tone: overview.fifo_total_pnl !== null && overview.fifo_total_pnl < 0 ? 'negative' : 'positive',
      deltaAmount: formatSignedNumber(overview.fifo_total_pnl_delta?.amount_change ?? null),
      deltaPercent: formatSignedPercent(overview.fifo_total_pnl_delta?.percent_change ?? null),
      deltaTone: deltaTone(overview.fifo_total_pnl_delta),
    },
    {
      title: 'dashboard.dailyTwr',
      value: formatPercent(overview.cnav_twr),
      helper: 'dashboard.dailyTwrHelper',
      tone: metricTone(overview.cnav_twr, 'accent'),
    },
    {
      title: 'dashboard.ytdTwr',
      value: formatPercent(overview.ytd_twr),
      helper: 'dashboard.ytdTwrHelper',
      helperData: { startDate: `${overview.report_date.slice(0, 4)}-01-01` },
      tone: metricTone(overview.ytd_twr, 'accent'),
    },
    { title: 'dashboard.ytdDividends', value: formatNumber(overview.crtt_dividends_ytd), tone: 'neutral' },
    { title: 'dashboard.ytdInterest', value: formatNumber(overview.crtt_broker_interest_ytd), tone: 'neutral' },
    { title: 'dashboard.ytdCommissions', value: formatNumber(overview.crtt_commissions_ytd), tone: 'negative' },
  ]
}
