import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AppHeader from '../AppHeader'

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    initialized: true,
    loading: false,
    authenticated: false,
    username: null,
    ensureAuth: vi.fn().mockResolvedValue(undefined),
    loginWithCredentials: vi.fn().mockResolvedValue(undefined),
    logout: vi.fn().mockResolvedValue(undefined),
  }),
}))

vi.mock('@/hooks/useAccountOverview', () => ({
  useAccountOverview: () => ({
    overview: null,
    ensureLoaded: vi.fn().mockResolvedValue(null),
    refresh: vi.fn(),
  }),
}))

function renderHeader(path = '/') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppHeader />
    </MemoryRouter>,
  )
}

describe('AppHeader', () => {
  it('renders the app title', () => {
    renderHeader()
    expect(screen.getByText('Portfolio Analytics')).toBeInTheDocument()
  })

  it('renders the eyebrow label', () => {
    renderHeader()
    expect(screen.getByText('IBKR DASHBOARD')).toBeInTheDocument()
  })

  it('renders base navigation items', () => {
    renderHeader()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Positions')).toBeInTheDocument()
  })

  it('renders Login button when not authenticated', () => {
    renderHeader()
    expect(screen.getByText('Login')).toBeInTheDocument()
  })

  it('renders the LIVE API tag', () => {
    renderHeader()
    expect(screen.getByText('LIVE API')).toBeInTheDocument()
  })

  it('does not render protected nav items when not authenticated', () => {
    renderHeader()
    expect(screen.queryByText('Trades')).not.toBeInTheDocument()
    expect(screen.queryByText('Cash Flows')).not.toBeInTheDocument()
    expect(screen.queryByText('Copilot')).not.toBeInTheDocument()
  })
})
