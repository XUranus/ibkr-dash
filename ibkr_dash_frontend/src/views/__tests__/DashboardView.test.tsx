import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import DashboardView from '../DashboardView'

vi.mock('@/hooks/useAccountOverview', () => ({
  useAccountOverview: () => ({
    overview: {
      report_date: '2025-06-01',
      total_equity: 100000,
      cash: 20000,
      stock_value: 80000,
      fifo_total_pnl: 5000,
      fifo_total_realized_pnl: 3000,
      fifo_total_unrealized_pnl: 2000,
      total_equity_delta: { amount_change: 1000, percent_change: 1.0 },
      fifo_total_pnl_delta: { amount_change: 200, percent_change: 0.5 },
      cnav_twr: 0.5,
      ytd_twr: 12.5,
      crtt_dividends_ytd: 1500,
      crtt_broker_interest_ytd: 100,
      crtt_commissions_ytd: -200,
    },
    ensureLoaded: vi.fn().mockResolvedValue({
      report_date: '2025-06-01',
      total_equity: 100000,
      cash: 20000,
      stock_value: 80000,
      fifo_total_pnl: 5000,
      fifo_total_realized_pnl: 3000,
      fifo_total_unrealized_pnl: 2000,
      total_equity_delta: { amount_change: 1000, percent_change: 1.0 },
      fifo_total_pnl_delta: { amount_change: 200, percent_change: 0.5 },
      cnav_twr: 0.5,
      ytd_twr: 12.5,
      crtt_dividends_ytd: 1500,
      crtt_broker_interest_ytd: 100,
      crtt_commissions_ytd: -200,
    }),
    refresh: vi.fn(),
  }),
}))

vi.mock('@/api/charts', () => ({
  fetchEquityCurve: vi.fn().mockResolvedValue({ items: [] }),
  fetchPerformanceCalendar: vi.fn().mockResolvedValue({ items: [] }),
}))

vi.mock('@/components/EquityCurveSimple', () => ({
  default: () => <div data-testid="equity-curve" />,
}))

vi.mock('@/components/PerformanceCalendar', () => ({
  default: () => <div data-testid="perf-calendar" />,
}))

function renderDashboard() {
  return render(
    <MemoryRouter>
      <DashboardView />
    </MemoryRouter>,
  )
}

describe('DashboardView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders without crashing', async () => {
    renderDashboard()
    // Wait for loading to complete
    await screen.findByText('Total Equity')
    expect(true).toBe(true)
  })

  it('displays stat cards after loading', async () => {
    renderDashboard()
    expect(await screen.findByText('Total Equity')).toBeInTheDocument()
    expect(screen.getByText('Cash')).toBeInTheDocument()
    expect(screen.getByText('Stock Value')).toBeInTheDocument()
  })

  it('displays stat card values', async () => {
    renderDashboard()
    await screen.findByText('Total Equity')
    // formatNumber(100000) = "100,000.00"
    expect(screen.getByText('100,000.00')).toBeInTheDocument()
  })

  it('renders equity curve component', async () => {
    renderDashboard()
    await screen.findByText('Total Equity')
    expect(screen.getByTestId('equity-curve')).toBeInTheDocument()
  })

  it('renders performance calendar component', async () => {
    renderDashboard()
    await screen.findByText('Total Equity')
    expect(screen.getByTestId('perf-calendar')).toBeInTheDocument()
  })
})
