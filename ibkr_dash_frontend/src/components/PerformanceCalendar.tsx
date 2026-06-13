import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchPerformanceCalendar } from '@/api/charts'
import type { PerformanceCalendarItem, PerformanceCalendarResponse, PerformanceCalendarView } from '@/types/charts'
import { formatNumber } from '@/utils/format'

interface Props {
  latestReportDate: string | null
}

type CalendarCell = {
  key: string
  label: string | null
  item: PerformanceCalendarItem | null
  isCurrentMonth: boolean
}

const weekdayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
const weekdayKeys = ['dashboard.mon', 'dashboard.tue', 'dashboard.wed', 'dashboard.thu', 'dashboard.fri']

function normalizeNumericValue(value: number | null): number | null {
  if (value === null || !Number.isFinite(value)) return null
  return value
}

function toneByValue(value: number | null): 'positive' | 'negative' | 'neutral' {
  value = normalizeNumericValue(value)
  if (value === null || value === 0) return 'neutral'
  return value > 0 ? 'positive' : 'negative'
}

function formatSignedInteger(value: number | null, t: (key: string) => string): string {
  value = normalizeNumericValue(value)
  if (value === null) return '--'
  if (value === 0) return t('common.noChange')
  const rounded = Math.round(value)
  return `${rounded > 0 ? '+' : ''}${new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(rounded)}`
}

function formatSignedPercent(value: number | null): string {
  value = normalizeNumericValue(value)
  if (value === null || value === 0) return ''
  return `${value > 0 ? '+' : ''}${new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value)}%`
}

function buildDefaultAnchor(view: PerformanceCalendarView, latestReportDate: string | null): string | undefined {
  if (!latestReportDate || view === 'all-years') return undefined
  return view === 'month' ? latestReportDate.slice(0, 7) : latestReportDate.slice(0, 4)
}

export default function PerformanceCalendar({ latestReportDate }: Props) {
  const { t } = useTranslation()
  const viewOptions: Array<{ key: PerformanceCalendarView; label: string }> = [
    { key: 'month', label: t('dashboard.monthView') },
    { key: 'year', label: t('dashboard.yearView') },
    { key: 'all-years', label: t('dashboard.allYears') },
  ]
  const [activeView, setActiveView] = useState<PerformanceCalendarView>('month')
  const [response, setResponse] = useState<PerformanceCalendarResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  const loadCalendar = useCallback(async (showLoading = true, nextAnchor?: string) => {
    if (!latestReportDate) { setResponse(null); return }
    if (showLoading) setLoading(true)
    setErrorMessage('')
    try {
      const data = await fetchPerformanceCalendar({
        view: activeView,
        anchor: nextAnchor ?? response?.anchor ?? buildDefaultAnchor(activeView, latestReportDate),
      })
      setResponse(data)
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('dashboard.failedToLoadCalendar'))
    } finally {
      if (showLoading) setLoading(false)
    }
  }, [activeView, latestReportDate, response?.anchor])

  useEffect(() => {
    if (!latestReportDate) { setResponse(null); return }
    void loadCalendar(response === null, response?.anchor ?? buildDefaultAnchor(activeView, latestReportDate))
  }, [latestReportDate, activeView])

  function switchView(nextView: PerformanceCalendarView) {
    if (activeView === nextView) return
    setResponse(null)
    setActiveView(nextView)
  }

  function jumpAnchor(direction: 'previous' | 'next') {
    if (!response) return
    const nextAnchor = direction === 'previous' ? response.previous_anchor : response.next_anchor
    if (nextAnchor) void loadCalendar(true, nextAnchor)
  }

  const summary = response?.summary ?? { positive_periods: 0, negative_periods: 0, total_pnl: null, periods_with_data: 0 }

  const monthCells = useMemo<CalendarCell[]>(() => {
    if (!response || response.view !== 'month') return []
    // Filter to weekdays only (Mon-Fri), skip weekends
    const cells: CalendarCell[] = []
    for (const item of response.items) {
      const d = new Date(item.period_key + 'T00:00:00Z')
      const dow = d.getUTCDay() // 0=Sun, 1=Mon, ..., 6=Sat
      if (dow === 0 || dow === 6) continue // skip weekends
      cells.push({ key: item.period_key, label: item.label, item, isCurrentMonth: true })
    }
    return cells
  }, [response])

  const anchorLabel = response
    ? response.view === 'month' ? `${response.anchor.slice(0, 4)}/${Number(response.anchor.slice(5, 7))}`
      : response.view === 'year' ? response.anchor
      : t('dashboard.allYears')
    : '--'

  return (
    <div className="surface-panel">
      <div className="surface-panel__content">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
          <div>
            <p className="eyebrow">{t('dashboard.calendar')}</p>
            <h2 className="panel-title">{t('dashboard.pnlCalendar')}</h2>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-end', gap: 6 }}>
            <span className="tag tag--accent">{anchorLabel}</span>
            <span className="tag">{t('dashboard.validPeriods', { count: summary.periods_with_data, period: t(`dashboard.${activeView === 'month' ? 'tradingDays' : activeView === 'year' ? 'months' : 'years'}`) })}</span>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: 'var(--space-3)', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
            {viewOptions.map((opt) => (
              <button key={opt.key} className={`btn btn--sm ${activeView === opt.key ? 'btn--accent' : ''}`} onClick={() => switchView(opt.key)}>{opt.label}</button>
            ))}
            {/* Month picker — only shown in month view */}
            {activeView === 'month' && response && (
              <input
                type="month"
                className="input"
                style={{
                  width: 140, minHeight: 26, padding: '2px 6px',
                  fontSize: '0.75rem', fontFamily: 'var(--font-mono)',
                }}
                value={response.anchor}
                min={response.earliest_anchor || undefined}
                max={response.latest_anchor || undefined}
                onChange={(e) => {
                  if (e.target.value) {
                    void loadCalendar(true, e.target.value)
                  }
                }}
              />
            )}
            {/* Year picker — only shown in year view */}
            {activeView === 'year' && response && (
              <input
                type="number"
                className="input"
                style={{
                  width: 80, minHeight: 26, padding: '2px 6px',
                  fontSize: '0.75rem', fontFamily: 'var(--font-mono)',
                }}
                value={response.anchor}
                min={response.earliest_anchor ? Number(response.earliest_anchor) : undefined}
                max={response.latest_anchor ? Number(response.latest_anchor) : undefined}
                onChange={(e) => {
                  if (e.target.value && e.target.value.length === 4) {
                    void loadCalendar(true, e.target.value)
                  }
                }}
              />
            )}
          </div>
          {response && activeView !== 'all-years' && (
            <div style={{ display: 'flex', gap: 4 }}>
              <button className="btn btn--sm" disabled={!response.previous_anchor || loading} onClick={() => jumpAnchor('previous')}>
                ← {t('dashboard.previousPeriod', { period: t(activeView === 'month' ? 'dashboard.month' : 'dashboard.year') })}
              </button>
              <button className="btn btn--sm" disabled={!response.next_anchor || loading} onClick={() => jumpAnchor('next')}>
                {t('dashboard.nextPeriod', { period: t(activeView === 'month' ? 'dashboard.month' : 'dashboard.year') })} →
              </button>
            </div>
          )}
        </div>

        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 120, borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)', background: 'var(--color-bg-elevated)', color: 'var(--color-text-secondary)', fontSize: '0.82rem' }}>
            {t('dashboard.updatingCalendar')}
          </div>
        ) : errorMessage ? (
          <div className="empty-state">{errorMessage}</div>
        ) : !response ? (
          <div className="empty-state">{t('dashboard.noCalendarData')}</div>
        ) : (
          <div style={{ display: 'grid', gap: 'var(--space-3)' }}>
            {/* Summary metrics */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 8 }}>
              {[
                { label: t('dashboard.positivePeriods', { period: t(`dashboard.${activeView === 'month' ? 'tradingDays' : activeView === 'year' ? 'months' : 'years'}`) }), value: summary.positive_periods, className: 'metric-positive' },
                { label: t('dashboard.negativePeriods', { period: t(`dashboard.${activeView === 'month' ? 'tradingDays' : activeView === 'year' ? 'months' : 'years'}`) }), value: summary.negative_periods, className: 'metric-negative' },
                { label: t('dashboard.netChange'), value: formatNumber(summary.total_pnl), className: toneByValue(summary.total_pnl) === 'positive' ? 'metric-positive' : toneByValue(summary.total_pnl) === 'negative' ? 'metric-negative' : '' },
              ].map((m) => (
                <div key={m.label} style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', padding: '6px 10px', borderRadius: 'var(--radius-sm)', background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border-subtle)' }}>
                  <span style={{ color: 'var(--color-text-muted)', fontSize: '0.72rem' }}>{m.label}</span>
                  <strong className={m.className} style={{ fontSize: '0.88rem', fontFamily: 'var(--font-mono)', fontVariantNumeric: 'tabular-nums' }}>{m.value}</strong>
                </div>
              ))}
            </div>

            {/* Month view calendar grid */}
            {activeView === 'month' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0, 1fr))', gap: 4 }}>
                {weekdayLabels.map((label, i) => (
                  <div key={label} style={{ padding: '0 4px 3px', color: 'var(--color-text-muted)', fontSize: '0.65rem', fontWeight: 600, textAlign: 'center', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{t(weekdayKeys[i])}</div>
                ))}
                {monthCells.map((cell) => {
                  const tone = toneByValue(cell.item?.pnl ?? null)
                  const borderColor = tone === 'positive' ? 'rgba(63,185,80,0.2)' : tone === 'negative' ? 'rgba(248,81,73,0.2)' : 'var(--color-border-subtle)'
                  const bgColor = tone === 'positive' ? 'rgba(63,185,80,0.04)' : tone === 'negative' ? 'rgba(248,81,73,0.04)' : 'var(--color-bg-elevated)'
                  return (
                    <div key={cell.key} style={{
                      minHeight: 72, padding: '6px 8px', borderRadius: 'var(--radius-sm)',
                      border: `1px solid ${borderColor}`,
                      background: bgColor,
                      display: 'grid', alignContent: 'space-between', gap: 4,
                      opacity: cell.isCurrentMonth ? 1 : 0.25,
                    }}>
                      {cell.isCurrentMonth && cell.item && (
                        <>
                          <div style={{ color: 'var(--color-text-muted)', fontSize: '0.7rem', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{cell.label}</div>
                          <div style={{
                            color: tone === 'positive' ? 'var(--color-positive)' : tone === 'negative' ? 'var(--color-negative)' : 'var(--color-text-primary)',
                            fontSize: '0.92rem', fontWeight: 700, fontFamily: 'var(--font-mono)', fontVariantNumeric: 'tabular-nums',
                          }}>
                            {formatSignedInteger(cell.item.pnl, t)}
                          </div>
                          <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.68rem', fontFamily: 'var(--font-mono)' }}>
                            {formatSignedPercent(cell.item.twr)}
                          </div>
                        </>
                      )}
                    </div>
                  )
                })}
              </div>
            )}

            {/* Year / All-years view */}
            {activeView !== 'month' && (
              <div style={{ display: 'grid', gridTemplateColumns: activeView === 'all-years' ? 'repeat(auto-fit, minmax(140px, 1fr))' : 'repeat(6, minmax(0, 1fr))', gap: 4 }}>
                {response.items.map((item) => {
                  const tone = toneByValue(item.pnl)
                  const borderColor = tone === 'positive' ? 'rgba(63,185,80,0.2)' : tone === 'negative' ? 'rgba(248,81,73,0.2)' : 'var(--color-border-subtle)'
                  const bgColor = tone === 'positive' ? 'rgba(63,185,80,0.04)' : tone === 'negative' ? 'rgba(248,81,73,0.04)' : 'var(--color-bg-elevated)'
                  return (
                    <div key={item.period_key} style={{
                      padding: '8px 10px', borderRadius: 'var(--radius-sm)',
                      border: `1px solid ${borderColor}`,
                      background: bgColor,
                      display: 'grid', alignContent: 'space-between', gap: 4,
                    }}>
                      <div style={{ color: 'var(--color-text-muted)', fontSize: '0.72rem', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{item.label}</div>
                      <div style={{
                        color: tone === 'positive' ? 'var(--color-positive)' : tone === 'negative' ? 'var(--color-negative)' : 'var(--color-text-primary)',
                        fontSize: '0.92rem', fontWeight: 700, fontFamily: 'var(--font-mono)', fontVariantNumeric: 'tabular-nums',
                      }}>
                        {formatSignedInteger(item.pnl, t)}
                      </div>
                      <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.68rem', fontFamily: 'var(--font-mono)' }}>
                        {formatSignedPercent(item.twr) || t('common.noData')}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
