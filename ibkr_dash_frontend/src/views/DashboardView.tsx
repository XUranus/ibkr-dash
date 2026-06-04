import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchEquityCurve } from '@/api/charts'
import { useAccountOverview } from '@/hooks/useAccountOverview'
import EquityCurveSimple from '@/components/EquityCurveSimple'
import ErrorBlock from '@/components/ErrorBlock'
import LoadingBlock from '@/components/LoadingBlock'
import PerformanceCalendar from '@/components/PerformanceCalendar'
import StatCard from '@/components/StatCard'
import type { EquityCurvePoint } from '@/types/charts'
import { buildDashboardStatCards } from '@/utils/dashboardMetrics'
import { buildEquityCurveRangeParams, EQUITY_CURVE_RANGE_OPTIONS, type EquityCurveRangeKey } from '@/utils/equityCurveRange'

export default function DashboardView() {
  const { overview, ensureLoaded } = useAccountOverview()
  const [curveItems, setCurveItems] = useState<EquityCurvePoint[]>([])
  const [pageLoading, setPageLoading] = useState(true)
  const [pageError, setPageError] = useState('')
  const [curveLoading, setCurveLoading] = useState(false)
  const [curveError, setCurveError] = useState('')
  const [selectedRange, setSelectedRange] = useState<EquityCurveRangeKey>('ytd')
  const refreshTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  const statCards = overview ? buildDashboardStatCards(overview) : []

  const loadCurveData = useCallback(async (showLoading: boolean, forceOverviewRefresh = false) => {
    if (showLoading) setCurveLoading(true)
    setCurveError('')
    try {
      if (forceOverviewRefresh) await ensureLoaded(true)
      else if (!overview) await ensureLoaded()
      const curveResponse = await fetchEquityCurve(
        buildEquityCurveRangeParams(overview?.report_date, selectedRange),
      )
      setCurveItems(curveResponse.items)
    } catch (err) {
      setCurveError(err instanceof Error ? err.message : 'Failed to load equity curve')
    } finally {
      if (showLoading) setCurveLoading(false)
    }
  }, [overview, selectedRange, ensureLoaded])

  useEffect(() => {
    const load = async () => {
      setPageLoading(true)
      setPageError('')
      try {
        await ensureLoaded()
        await loadCurveData(false)
      } catch (err) {
        setPageError(err instanceof Error ? err.message : 'Failed to load dashboard')
      } finally {
        setPageLoading(false)
      }
    }
    void load()

    refreshTimer.current = setInterval(() => {
      void loadCurveData(false, true)
    }, 30000)

    return () => {
      if (refreshTimer.current) clearInterval(refreshTimer.current)
    }
  }, [])

  function setCurveRange(nextRange: EquityCurveRangeKey) {
    if (selectedRange === nextRange) return
    setSelectedRange(nextRange)
  }

  useEffect(() => {
    if (!pageLoading) void loadCurveData(true)
  }, [selectedRange])

  return (
    <section className="page-section">
      {pageLoading ? (
        <LoadingBlock />
      ) : pageError ? (
        <ErrorBlock message={pageError} />
      ) : (
        <>
          <section className="surface-panel" style={{ marginBottom: 'var(--space-5)' }}>
            <div className="surface-panel__content">
              <section className="stats-grid">
                {statCards.map((card) => (
                  <StatCard
                    key={card.title}
                    title={card.title}
                    value={card.value}
                    helper={card.helper}
                    tone={card.tone}
                    deltaAmount={card.deltaAmount}
                    deltaPercent={card.deltaPercent}
                    deltaTone={card.deltaTone}
                  />
                ))}
              </section>
            </div>
          </section>

          <EquityCurveSimple
            items={curveItems}
            loading={curveLoading}
            errorMessage={curveError}
            rangeOptions={EQUITY_CURVE_RANGE_OPTIONS}
            selectedRange={selectedRange}
            onSelectRange={setCurveRange}
          />
          <PerformanceCalendar latestReportDate={overview?.report_date ?? null} />
        </>
      )}
    </section>
  )
}
