import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import PositionsView from '../PositionsView'

vi.mock('@/hooks/useAccountOverview', () => ({
  useAccountOverview: () => ({
    overview: {
      report_date: '2025-06-01',
      cash: 25000,
      total_equity: 150000,
    },
    ensureLoaded: vi.fn().mockResolvedValue(null),
    refresh: vi.fn(),
  }),
}))

vi.mock('@/api/positions', () => ({
  fetchPositions: vi.fn().mockResolvedValue({
    items: [
      {
        symbol: 'AAPL',
        description: 'APPLE INC',
        asset_class: 'STK',
        position_value: 15000,
        percent_of_nav: 10.0,
        qty: 100,
        avg_cost: 150,
        market_price: 150,
        unrealized_pnl: 0,
      },
      {
        symbol: 'SGOV',
        description: 'ISHARES 0-3 MONTH TREASURY BOND ETF',
        asset_class: 'STK',
        position_value: 10000,
        percent_of_nav: 6.67,
        qty: 100,
        avg_cost: 100,
        market_price: 100,
        unrealized_pnl: 0,
      },
    ],
    summary: {
      top_positions: [
        {
          symbol: 'AAPL',
          description: 'APPLE INC',
          asset_class: 'STK',
          position_value: 15000,
          percent_of_nav: 10.0,
        },
      ],
    },
    total_count: 2,
  }),
  fetchPositionDetail: vi.fn().mockResolvedValue({
    symbol: 'AAPL',
    description: 'APPLE INC',
    bars: [],
    trades: [],
  }),
}))

vi.mock('@/components/PieDistributionCard', () => ({
  default: ({ title }: { title: string }) => <div data-testid={`pie-${title}`}>{title}</div>,
}))

vi.mock('@/components/PositionTable', () => ({
  default: () => <div data-testid="position-table" />,
}))

function renderPositions() {
  return render(
    <MemoryRouter>
      <PositionsView />
    </MemoryRouter>,
  )
}

describe('PositionsView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders without crashing', async () => {
    renderPositions()
    await screen.findByText('Position Concentration')
    expect(true).toBe(true)
  })

  it('shows loading state initially', () => {
    renderPositions()
    // LoadingBlock renders a surface-panel
    expect(document.querySelector('.surface-panel')).toBeInTheDocument()
  })

  it('displays position concentration section after loading', async () => {
    renderPositions()
    expect(await screen.findByText('Position Concentration')).toBeInTheDocument()
  })

  it('displays top positions in summary', async () => {
    renderPositions()
    await screen.findByText('Position Concentration')
    expect(screen.getByText('AAPL')).toBeInTheDocument()
    expect(screen.getByText('APPLE INC')).toBeInTheDocument()
  })

  it('renders asset classes pie chart', async () => {
    renderPositions()
    await screen.findByText('Position Concentration')
    expect(screen.getByTestId('pie-Asset Classes')).toBeInTheDocument()
  })

  it('renders industry distribution pie chart', async () => {
    renderPositions()
    await screen.findByText('Position Concentration')
    expect(screen.getByTestId('pie-Industry Distribution')).toBeInTheDocument()
  })

  it('renders position table', async () => {
    renderPositions()
    await screen.findByText('Position Concentration')
    expect(screen.getByTestId('position-table')).toBeInTheDocument()
  })

  it('displays position details section header', async () => {
    renderPositions()
    await screen.findByText('Position Details')
    expect(screen.getByText('Position Details')).toBeInTheDocument()
  })
})
