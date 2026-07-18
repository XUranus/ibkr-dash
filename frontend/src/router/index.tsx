import React, { lazy, Suspense, useEffect } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import i18n from '@/i18n'
import App from '@/App'
import ErrorBoundary from '@/components/ErrorBoundary'
import { useAuth } from '@/hooks/useAuth'

const LoadingFallback = () => (
  <div style={{ display: 'grid', placeItems: 'center', minHeight: '40vh', color: '#adc0df' }}>
    {i18n.t('common.loading')}
  </div>
)

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { authenticated, initialized, ensureAuth } = useAuth()

  // Ensure auth is checked on mount (don't wait for AppHeader)
  useEffect(() => {
    if (!initialized) {
      void ensureAuth()
    }
  }, [initialized, ensureAuth])

  if (!initialized) return <LoadingFallback />
  if (!authenticated) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 20px' }}>
        <p style={{ color: 'var(--color-text-muted)', marginBottom: 16 }}>
          {i18n.t('errors.pleaseLogin')}
        </p>
        <button className="btn btn--accent" onClick={() => window.location.href = '/'}>
          {i18n.t('auth.goToLogin')}
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
const TradeDecisionAgentView = lazy(() => import('@/views/TradeDecisionAgentView'))
const AccountCopilotView = lazy(() => import('@/views/AccountCopilotView'))
const AdminSystemView = lazy(() => import('@/views/AdminSystemView'))
const AdminPromptsView = lazy(() => import('@/views/AdminPromptsView'))
const AdminAgentMonitoringView = lazy(() => import('@/views/AdminAgentMonitoringView'))
const AdminSettingsView = lazy(() => import('@/views/AdminSettingsView'))
const AdminSchedulerView = lazy(() => import('@/views/AdminSchedulerView'))
const BootstrapView = lazy(() => import('@/views/BootstrapView'))
// Phase 1-3 views
const InvestmentPolicyView = lazy(() => import('@/views/InvestmentPolicyView'))
const PerformanceView = lazy(() => import('@/views/PerformanceView'))
const DailyPositionReviewView = lazy(() => import('@/views/DailyPositionReviewView'))
const TradeReviewView = lazy(() => import('@/views/TradeReviewView'))
const MarketEventsView = lazy(() => import('@/views/MarketEventsView'))
const KnowledgeView = lazy(() => import('@/views/KnowledgeView'))
const PortfolioManagerView = lazy(() => import('@/views/PortfolioManagerView'))
const AdminMarketEventsView = lazy(() => import('@/views/AdminMarketEventsView'))
const AdminEvalHarnessView = lazy(() => import('@/views/AdminEvalHarnessView'))
const AdminAgentReplaysView = lazy(() => import('@/views/AdminAgentReplaysView'))
const AdminFlexReportsView = lazy(() => import('@/views/AdminFlexReportsView'))
const AdminApiAccessView = lazy(() => import('@/views/AdminApiAccessView'))

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

export const router = createBrowserRouter(
  [
    {
      path: '/',
      element: <App />,
    children: [
      { index: true, element: lazyViewWithErrorBoundary(DashboardView) },
      { path: 'positions', element: lazyViewWithErrorBoundary(PositionsView) },
      { path: 'trades', element: <ProtectedRoute>{lazyViewWithErrorBoundary(TradesView)}</ProtectedRoute> },
      { path: 'cash-flows', element: <ProtectedRoute>{lazyViewWithErrorBoundary(CashFlowsView)}</ProtectedRoute> },
      { path: 'dividends', element: <ProtectedRoute>{lazyViewWithErrorBoundary(DividendsView)}</ProtectedRoute> },
      { path: 'stock-research', element: <ProtectedRoute>{lazyViewWithErrorBoundary(StockResearchView)}</ProtectedRoute> },
      { path: 'trade-decision', element: <ProtectedRoute>{lazyViewWithErrorBoundary(TradeDecisionAgentView)}</ProtectedRoute> },
      { path: 'copilot', element: <ProtectedRoute>{lazyViewWithErrorBoundary(AccountCopilotView)}</ProtectedRoute> },
      { path: 'admin/system', element: <ProtectedRoute>{lazyViewWithErrorBoundary(AdminSystemView)}</ProtectedRoute> },
      { path: 'admin/llm', element: <Navigate to="/admin/settings" replace /> },
      { path: 'admin/ibkr', element: <Navigate to="/admin/settings" replace /> },
      { path: 'admin/email', element: <Navigate to="/admin/settings" replace /> },
      { path: 'admin/longbridge-mcp', element: <Navigate to="/admin/settings" replace /> },
      { path: 'admin/harness', element: <Navigate to="/admin/agent-monitoring" replace /> },
      { path: 'admin/prompts', element: <ProtectedRoute>{lazyViewWithErrorBoundary(AdminPromptsView)}</ProtectedRoute> },
      { path: 'admin/agent-monitoring', element: <ProtectedRoute>{lazyViewWithErrorBoundary(AdminAgentMonitoringView)}</ProtectedRoute> },
      { path: 'admin/settings', element: <ProtectedRoute>{lazyViewWithErrorBoundary(AdminSettingsView)}</ProtectedRoute> },
      { path: 'admin/scheduler', element: <ProtectedRoute>{lazyViewWithErrorBoundary(AdminSchedulerView)}</ProtectedRoute> },
      { path: 'bootstrap', element: lazyViewWithErrorBoundary(BootstrapView) },
      // Phase 1-3 routes
      { path: 'investment-policy', element: <ProtectedRoute>{lazyViewWithErrorBoundary(InvestmentPolicyView)}</ProtectedRoute> },
      { path: 'performance', element: <ProtectedRoute>{lazyViewWithErrorBoundary(PerformanceView)}</ProtectedRoute> },
      { path: 'daily-review', element: <ProtectedRoute>{lazyViewWithErrorBoundary(DailyPositionReviewView)}</ProtectedRoute> },
      { path: 'trade-review', element: <ProtectedRoute>{lazyViewWithErrorBoundary(TradeReviewView)}</ProtectedRoute> },
      { path: 'market-events', element: lazyViewWithErrorBoundary(MarketEventsView) },
      { path: 'knowledge', element: <ProtectedRoute>{lazyViewWithErrorBoundary(KnowledgeView)}</ProtectedRoute> },
      { path: 'portfolio-manager', element: <ProtectedRoute>{lazyViewWithErrorBoundary(PortfolioManagerView)}</ProtectedRoute> },
      { path: 'admin/market-events', element: <ProtectedRoute>{lazyViewWithErrorBoundary(AdminMarketEventsView)}</ProtectedRoute> },
      { path: 'admin/eval-harness', element: <ProtectedRoute>{lazyViewWithErrorBoundary(AdminEvalHarnessView)}</ProtectedRoute> },
      { path: 'admin/agent-replays', element: <ProtectedRoute>{lazyViewWithErrorBoundary(AdminAgentReplaysView)}</ProtectedRoute> },
      { path: 'admin/flex-reports', element: <ProtectedRoute>{lazyViewWithErrorBoundary(AdminFlexReportsView)}</ProtectedRoute> },
      { path: 'admin/api-access', element: <ProtectedRoute>{lazyViewWithErrorBoundary(AdminApiAccessView)}</ProtectedRoute> },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
  ],
  {
    future: {
      v7_relativeSplatPath: true,
    },
  },
)
