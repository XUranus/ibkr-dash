import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchEquityCurve } from '@/api/charts'
import { useAccountOverview } from '@/hooks/useAccountOverview'
import EquityCurveSimple from '@/components/EquityCurveSimple'
import ErrorBlock from '@/components/ErrorBlock'
import LoadingBlock from '@/components/LoadingBlock'
import MarketEventsPanel from '@/components/MarketEventsPanel'
import PerformanceCalendar from '@/components/PerformanceCalendar'
import StatCard from '@/components/StatCard'
import type { EquityCurvePoint } from '@/types/charts'
import { buildDashboardStatCards } from '@/utils/dashboardMetrics'
import { buildEquityCurveRangeParams, EQUITY_CURVE_RANGE_OPTIONS, type EquityCurveRangeKey } from '@/utils/equityCurveRange'

export default function DashboardView() {
  const { t } = useTranslation()
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
      setCurveError(err instanceof Error ? err.message : t('dashboard.error'))
    } finally {
      if (showLoading) setCurveLoading(false)
    }
  }, [overview, selectedRange, ensureLoaded, t])

  useEffect(() => {
    const load = async () => {
      setPageLoading(true)
      setPageError('')
      try {
        await ensureLoaded()
        await loadCurveData(false)
      } catch (err) {
        setPageError(err instanceof Error ? err.message : t('dashboard.error'))
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
          {/* Account metrics — compact grid */}
          <section className="stats-grid">
            {statCards.map((card) => {
              const translatedHelper = card.helper
                ? (card.helper.startsWith('dashboard.') || card.helper.startsWith('common.')
                  ? t(card.helper, card.helperData)
                  : card.helper)
                : undefined
              return (
                <StatCard
                  key={card.title}
                  title={t(card.title)}
                  value={card.value}
                  helper={translatedHelper}
                  tone={card.tone}
                  deltaAmount={card.deltaAmount}
                  deltaPercent={card.deltaPercent}
                  deltaTone={card.deltaTone}
                />
              )
            })}
          </section>

          {/* Equity curve */}
          <EquityCurveSimple
            items={curveItems}
            loading={curveLoading}
            errorMessage={curveError}
            rangeOptions={EQUITY_CURVE_RANGE_OPTIONS.map((opt) => ({ ...opt, label: t(opt.label) }))}
            selectedRange={selectedRange}
            onSelectRange={setCurveRange}
          />

          {/* Performance calendar + Market events */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 'var(--space-3)' }}>
            <PerformanceCalendar latestReportDate={overview?.report_date ?? null} />
            <MarketEventsPanel />
          </div>
        </>
      )}
    </section>
  )
}
