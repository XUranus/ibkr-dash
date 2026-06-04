import React, { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import App from '@/App'
import ErrorBoundary from '@/components/ErrorBoundary'

const LoadingFallback = () => (
  <div style={{ display: 'grid', placeItems: 'center', minHeight: '40vh', color: '#adc0df' }}>
    Loading...
  </div>
)

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
      { path: 'stock-research', element: lazyViewWithErrorBoundary(StockResearchView) },
      { path: 'daily-position-review', element: lazyViewWithErrorBoundary(DailyPositionReviewView) },
      { path: 'trade-decision', element: lazyViewWithErrorBoundary(TradeDecisionAgentView) },
      { path: 'trade-review', element: lazyViewWithErrorBoundary(TradeReviewAgentView) },
      { path: 'copilot', element: lazyViewWithErrorBoundary(AccountCopilotView) },
      { path: 'admin/system', element: lazyViewWithErrorBoundary(AdminSystemView) },
      { path: 'admin/llm', element: lazyViewWithErrorBoundary(AdminLlmView) },
      { path: 'admin/ibkr', element: lazyViewWithErrorBoundary(AdminIbkrView) },
      { path: 'admin/email', element: lazyViewWithErrorBoundary(AdminEmailView) },
      { path: 'admin/longbridge-mcp', element: lazyViewWithErrorBoundary(AdminLongbridgeMcpView) },
      { path: 'admin/harness', element: lazyViewWithErrorBoundary(AdminHarnessView) },
      { path: 'admin/prompts', element: lazyViewWithErrorBoundary(AdminPromptsView) },
      { path: 'admin/agent-monitoring', element: lazyViewWithErrorBoundary(AdminAgentMonitoringView) },
      { path: 'bootstrap', element: lazyViewWithErrorBoundary(BootstrapView) },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
])
