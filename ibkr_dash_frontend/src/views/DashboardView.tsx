import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchEquityCurve } from '@/api/charts'
import { fetchPositions } from '@/api/positions'
import { useAccountOverview } from '@/hooks/useAccountOverview'
import EquityCurveSimple from '@/components/EquityCurveSimple'
import ErrorBlock from '@/components/ErrorBlock'
import LoadingBlock from '@/components/LoadingBlock'
import PerformanceCalendar from '@/components/PerformanceCalendar'
import PieDistributionCard, { type PieSegmentItem } from '@/components/PieDistributionCard'
import StatCard from '@/components/StatCard'
import type { EquityCurvePoint } from '@/types/charts'
import type { PositionItem } from '@/types/positions'
import { formatNumber } from '@/utils/format'
import { buildDashboardStatCards } from '@/utils/dashboardMetrics'
import { buildEquityCurveRangeParams, EQUITY_CURVE_RANGE_OPTIONS, type EquityCurveRangeKey } from '@/utils/equityCurveRange'

const TOP_N = 10

export default function DashboardView() {
  const { t } = useTranslation()
  const { overview, ensureLoaded } = useAccountOverview()
  const [curveItems, setCurveItems] = useState<EquityCurvePoint[]>([])
  const [topPositions, setTopPositions] = useState<PositionItem[]>([])
  const [pageLoading, setPageLoading] = useState(true)
  const [pageError, setPageError] = useState('')
  const [curveLoading, setCurveLoading] = useState(false)
  const [curveError, setCurveError] = useState('')
  const [selectedRange, setSelectedRange] = useState<EquityCurveRangeKey>('ytd')
  const refreshTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  const statCards = overview ? buildDashboardStatCards(overview) : []

  const concentrationPie = PieDistributionCard
    ? (() => {
        const items: PieSegmentItem[] = topPositions.slice(0, TOP_N).map((p, i) => ({
          label: p.symbol ?? '--',
          value: p.position_value ?? 0,
          color: ['#56d5ff', '#6ee7b7', '#8b7cff', '#ffb454', '#ff7b98', '#7dd3fc', '#c084fc', '#fbbf24', '#34d399', '#f87171'][i % 10],
          members: [p.description ?? ''],
        }))
        return items.length > 0 ? items : null
      })()
    : null

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
        const posResponse = await fetchPositions({ sort_by: 'position_value', sort_order: 'desc', page: 1, page_size: TOP_N })
        setTopPositions(posResponse.items)
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
          {/* Stat cards */}
              <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease' }}>
                <div className="surface-panel__content">
                  <section className="stats-grid stagger-reveal">
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
                </div>
              </section>

              {/* Top 10 Concentration */}
              {topPositions.length > 0 && (
                <section className="summary-layout" style={{ animation: 'slideUp 0.45s ease 0.1s both' }}>
                  <section className="surface-panel">
                    <div className="surface-panel__content">
                      <p className="eyebrow">{t('dashboard.topNConcentration', { n: TOP_N })}</p>
                      <div className="summary-list" style={{ marginTop: 8 }}>
                        {topPositions.map((item, i) => (
                          <div key={item.symbol} className="summary-list__row">
                            <div className="summary-list__meta">
                              <strong style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text-bright)' }}>
                                {i + 1}. {item.symbol}
                              </strong>
                              <p>{item.description}</p>
                            </div>
                            <div className="summary-list__value">
                              <strong style={{ fontFamily: 'var(--font-mono)' }}>{formatNumber(item.position_value, 2)}</strong>
                              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>
                                {item.percent_of_nav != null ? `${formatNumber(item.percent_of_nav, 1)}%` : '--'}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </section>

                  {concentrationPie && (
                    <PieDistributionCard
                      title={t('dashboard.positionDistribution')}
                      subtitle={t('dashboard.topNHoldingsDesc', { n: TOP_N })}
                      items={concentrationPie}
                    />
                  )}
                </section>
              )}

              {/* Equity curve */}
              <div style={{ animation: 'slideUp 0.5s ease 0.2s both' }}>
                <EquityCurveSimple
                  items={curveItems}
                  loading={curveLoading}
                  errorMessage={curveError}
                  rangeOptions={EQUITY_CURVE_RANGE_OPTIONS.map((opt) => ({ ...opt, label: t(opt.label) }))}
                  selectedRange={selectedRange}
                  onSelectRange={setCurveRange}
                />
              </div>

          {/* Performance calendar */}
          <div style={{ animation: 'slideUp 0.5s ease 0.3s both' }}>
            <PerformanceCalendar latestReportDate={overview?.report_date ?? null} />
          </div>
        </>
      )}
    </section>
  )
}
