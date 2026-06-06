import React, { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import App from '@/App'
import ErrorBoundary from '@/components/ErrorBoundary'
import { useAuth } from '@/hooks/useAuth'

const LoadingFallback = () => (
  <div style={{ display: 'grid', placeItems: 'center', minHeight: '40vh', color: '#adc0df' }}>
    Loading...
  </div>
)

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { authenticated, initialized } = useAuth()

  if (!initialized) return <LoadingFallback />
  if (!authenticated) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 20px' }}>
        <p style={{ color: 'var(--color-text-muted)', marginBottom: 16 }}>
          Please log in to access this page.
        </p>
        <button className="btn btn--accent" onClick={() => window.location.href = '/'}>
          Go to Login
        </button>
      </div>
    )
  }
  return <>{children}</>
}

const DashboardView = lazy(() => import('@/views/DashboardView'))
const PositionsView = lazy(() => import('@/views/PositionsView'))
const TradesView = lazy(() => import('@/views/TradesView'))
const CashFlowsView = lazy(() => import('@/views/CashFlowsView'))
const DividendsView = lazy(() => import('@/views/DividendsView'))
const StockResearchView = lazy(() => import('@/views/StockResearchView'))
const DailyPositionReviewView = lazy(() => import('@/views/DailyPositionReviewView'))
const TradeDecisionAgentView = lazy(() => import('@/views/TradeDecisionAgentView'))
const TradeReviewAgentView = lazy(() => import('@/views/TradeReviewAgentView'))
const AccountCopilotView = lazy(() => import('@/views/AccountCopilotView'))
const AdminSystemView = lazy(() => import('@/views/AdminSystemView'))
const AdminLlmView = lazy(() => import('@/views/AdminLlmView'))
const AdminPromptsView = lazy(() => import('@/views/AdminPromptsView'))
const AdminAgentMonitoringView = lazy(() => import('@/views/AdminAgentMonitoringView'))
const AdminIbkrView = lazy(() => import('@/views/AdminIbkrView'))
const AdminEmailView = lazy(() => import('@/views/AdminEmailView'))
const AdminLongbridgeMcpView = lazy(() => import('@/views/AdminLongbridgeMcpView'))
const AdminHarnessView = lazy(() => import('@/views/AdminHarnessView'))
const BootstrapView = lazy(() => import('@/views/BootstrapView'))

function lazyView(Component: React.LazyExoticComponent<React.ComponentType>) {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Component />
    </Suspense>
  )
}

function lazyViewWithErrorBoundary(Component: React.LazyExoticComponent<React.ComponentType>) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<LoadingFallback />}>
        <Component />
      </Suspense>
    </ErrorBoundary>
  )
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: lazyViewWithErrorBoundary(DashboardView) },
      { path: 'positions', element: lazyViewWithErrorBoundary(PositionsView) },
      { path: 'trades', element: lazyViewWithErrorBoundary(TradesView) },
      { path: 'cash-flows', element: lazyViewWithErrorBoundary(CashFlowsView) },
      { path: 'dividends', element: lazyViewWithErrorBoundary(DividendsView) },
      { path: 'stock-research', element: <ProtectedRoute>{lazyViewWithErrorBoundary(StockResearchView)}</ProtectedRoute> },
      { path: 'daily-position-review', element: <ProtectedRoute>{lazyViewWithErrorBoundary(DailyPositionReviewView)}</ProtectedRoute> },
      { path: 'trade-decision', element: <ProtectedRoute>{lazyViewWithErrorBoundary(TradeDecisionAgentView)}</ProtectedRoute> },
      { path: 'trade-review', element: <ProtectedRoute>{lazyViewWithErrorBoundary(TradeReviewAgentView)}</ProtectedRoute> },
      { path: 'copilot', element: <ProtectedRoute>{lazyViewWithErrorBoundary(AccountCopilotView)}</ProtectedRoute> },
      { path: 'admin/system', element: <ProtectedRoute>{lazyViewWithErrorBoundary(AdminSystemView)}</ProtectedRoute> },
      { path: 'admin/llm', element: <ProtectedRoute>{lazyViewWithErrorBoundary(AdminLlmView)}</ProtectedRoute> },
      { path: 'admin/ibkr', element: <ProtectedRoute>{lazyViewWithErrorBoundary(AdminIbkrView)}</ProtectedRoute> },
      { path: 'admin/email', element: <ProtectedRoute>{lazyViewWithErrorBoundary(AdminEmailView)}</ProtectedRoute> },
      { path: 'admin/longbridge-mcp', element: <ProtectedRoute>{lazyViewWithErrorBoundary(AdminLongbridgeMcpView)}</ProtectedRoute> },
      { path: 'admin/harness', element: <ProtectedRoute>{lazyViewWithErrorBoundary(AdminHarnessView)}</ProtectedRoute> },
      { path: 'admin/prompts', element: <ProtectedRoute>{lazyViewWithErrorBoundary(AdminPromptsView)}</ProtectedRoute> },
      { path: 'admin/agent-monitoring', element: <ProtectedRoute>{lazyViewWithErrorBoundary(AdminAgentMonitoringView)}</ProtectedRoute> },
      { path: 'bootstrap', element: lazyViewWithErrorBoundary(BootstrapView) },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
])
