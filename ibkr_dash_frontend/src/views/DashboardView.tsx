import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchEquityCurve } from '@/api/charts'
import { fetchPositions, fetchRealtimePositions, type RealtimePosition } from '@/api/positions'
import { useAccountOverview } from '@/hooks/useAccountOverview'
import EquityCurveSimple from '@/components/EquityCurveSimple'
import ErrorBlock from '@/components/ErrorBlock'
import LoadingBlock from '@/components/LoadingBlock'
import PerformanceCalendar from '@/components/PerformanceCalendar'
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
  const [realtimeData, setRealtimeData] = useState<Map<string, number>>(new Map())
  const [pageLoading, setPageLoading] = useState(true)
  const [pageError, setPageError] = useState('')
  const [curveLoading, setCurveLoading] = useState(false)
  const [curveError, setCurveError] = useState('')
  const [selectedRange, setSelectedRange] = useState<EquityCurveRangeKey>('ytd')
  const refreshTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  const statCards = overview ? buildDashboardStatCards(overview) : []
  const totalValue = topPositions.reduce((sum, p) => sum + (p.position_value ?? 0), 0)

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
        const [posResponse, rtResponse] = await Promise.all([
          fetchPositions({ sort_by: 'position_value', sort_order: 'desc', page: 1, page_size: TOP_N }),
          fetchRealtimePositions().catch(() => ({ items: [], count: 0 })),
        ])
        setTopPositions(posResponse.items)
        const rtMap = new Map<string, number>()
        for (const rt of (rtResponse.items ?? [])) {
          rtMap.set(rt.symbol, rt.change_pct ?? 0)
        }
        setRealtimeData(rtMap)
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

          {/* Top 10 Concentration — compact bar layout */}
          {topPositions.length > 0 && (
            <section className="surface-panel" style={{ animation: 'slideUp 0.45s ease 0.1s both' }}>
              <div className="surface-panel__content">
                <p className="eyebrow" style={{ marginBottom: 12 }}>{t('dashboard.topNConcentration', { n: TOP_N })}</p>
                <div style={{ display: 'grid', gap: 4 }}>
                  {topPositions.map((item, i) => {
                    const pct = totalValue > 0 ? ((item.position_value ?? 0) / totalValue) * 100 : 0
                    const changePct = realtimeData.get(item.symbol ?? '') ?? 0
                    const isPositive = changePct >= 0
                    return (
                      <div key={item.symbol} style={{
                        display: 'grid',
                        gridTemplateColumns: '24px 1fr 80px 60px',
                        alignItems: 'center',
                        gap: 8,
                        padding: '6px 10px',
                        borderRadius: 'var(--radius-sm)',
                        background: 'rgba(10,14,26,0.4)',
                      }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--color-text-muted)', textAlign: 'center' }}>
                          {i + 1}
                        </span>
                        <div style={{ minWidth: 0 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <strong style={{ fontFamily: 'var(--font-mono)', fontSize: '0.88rem', color: 'var(--color-text-bright)' }}>
                              {item.symbol}
                            </strong>
                            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {item.description}
                            </span>
                          </div>
                          <div style={{ marginTop: 4, height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
                            <div style={{
                              width: `${Math.min(pct, 100)}%`,
                              height: '100%',
                              borderRadius: 2,
                              background: isPositive ? 'var(--color-positive)' : 'var(--color-negative)',
                              opacity: 0.7,
                              transition: 'width 0.3s ease',
                            }} />
                          </div>
                        </div>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', textAlign: 'right', color: 'var(--color-text-bright)' }}>
                          {formatNumber(item.position_value, 0)}
                        </span>
                        <span style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '0.82rem',
                          textAlign: 'right',
                          color: isPositive ? 'var(--color-positive)' : 'var(--color-negative)',
                        }}>
                          {pct.toFixed(1)}%
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
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
