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

const weekdayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const weekdayKeys = ['dashboard.mon', 'dashboard.tue', 'dashboard.wed', 'dashboard.thu', 'dashboard.fri', 'dashboard.sat', 'dashboard.sun']

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
    const [yearText, monthText] = response.anchor.split('-')
    const year = Number(yearText)
    const month = Number(monthText)
    const firstDay = new Date(Date.UTC(year, month - 1, 1))
    const leadingPadding = (firstDay.getUTCDay() + 6) % 7
    const cells: CalendarCell[] = []
    for (let i = 0; i < leadingPadding; i++) cells.push({ key: `leading-${i}`, label: null, item: null, isCurrentMonth: false })
    for (const item of response.items) cells.push({ key: item.period_key, label: item.label, item, isCurrentMonth: true })
    const trailing = (7 - (cells.length % 7)) % 7
    for (let i = 0; i < trailing; i++) cells.push({ key: `trailing-${i}`, label: null, item: null, isCurrentMonth: false })
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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 'var(--space-4)', marginBottom: 'var(--space-4)' }}>
          <div>
            <p className="eyebrow">{t('dashboard.calendar')}</p>
            <h2 className="panel-title" style={{ fontSize: '1.4rem' }}>{t('dashboard.pnlCalendar')}</h2>
            <p className="panel-subtitle" style={{ maxWidth: '48rem' }}>
              {t('dashboard.calendarHint')}
            </p>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-end', gap: 10 }}>
            <span className="tag tag--accent">{anchorLabel}</span>
            <span className="tag">{t('dashboard.validPeriods', { count: summary.periods_with_data, period: t(`dashboard.${activeView === 'month' ? 'tradingDays' : activeView === 'year' ? 'months' : 'years'}`) })}</span>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, marginBottom: 'var(--space-4)', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', gap: 10 }}>
            {viewOptions.map((opt) => (
              <button key={opt.key} className="btn" style={{
                borderRadius: 999, padding: '8px 14px',
                background: activeView === opt.key ? 'rgba(26, 66, 122, 0.88)' : 'rgba(15, 26, 45, 0.72)',
                borderColor: activeView === opt.key ? 'rgba(86, 213, 255, 0.28)' : 'rgba(129, 160, 207, 0.12)',
                color: activeView === opt.key ? '#eaf5ff' : 'var(--color-text-secondary)',
              }} onClick={() => switchView(opt.key)}>{opt.label}</button>
            ))}
          </div>
          {response && activeView !== 'all-years' && (
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn" disabled={!response.previous_anchor || loading} onClick={() => jumpAnchor('previous')}>
                {t('dashboard.previousPeriod', { period: t(activeView === 'month' ? 'dashboard.month' : 'dashboard.year') })}
              </button>
              <button className="btn" disabled={!response.next_anchor || loading} onClick={() => jumpAnchor('next')}>
                {t('dashboard.nextPeriod', { period: t(activeView === 'month' ? 'dashboard.month' : 'dashboard.year') })}
              </button>
            </div>
          )}
        </div>

        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 180, borderRadius: 22, border: '1px solid rgba(86, 213, 255, 0.14)', background: 'rgba(8, 15, 28, 0.5)', color: 'var(--color-text-primary)', fontWeight: 600 }}>
            {t('dashboard.updatingCalendar')}
          </div>
        ) : errorMessage ? (
          <div className="empty-state">{errorMessage}</div>
        ) : !response ? (
          <div className="empty-state">{t('dashboard.noCalendarData')}</div>
        ) : (
          <div style={{ display: 'grid', gap: 'var(--space-4)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12 }}>
              <div style={{ display: 'grid', gap: 6, padding: '14px 16px', borderRadius: 18, border: '1px solid rgba(129, 160, 207, 0.12)', background: 'rgba(15, 26, 45, 0.66)' }}>
                <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.84rem' }}>{t('dashboard.positivePeriods', { period: t(`dashboard.${activeView === 'month' ? 'tradingDays' : activeView === 'year' ? 'months' : 'years'}`) })}</span>
                <strong className="metric-positive" style={{ fontSize: '1.12rem' }}>{summary.positive_periods}</strong>
              </div>
              <div style={{ display: 'grid', gap: 6, padding: '14px 16px', borderRadius: 18, border: '1px solid rgba(129, 160, 207, 0.12)', background: 'rgba(15, 26, 45, 0.66)' }}>
                <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.84rem' }}>{t('dashboard.negativePeriods', { period: t(`dashboard.${activeView === 'month' ? 'tradingDays' : activeView === 'year' ? 'months' : 'years'}`) })}</span>
                <strong className="metric-negative" style={{ fontSize: '1.12rem' }}>{summary.negative_periods}</strong>
              </div>
              <div style={{ display: 'grid', gap: 6, padding: '14px 16px', borderRadius: 18, border: '1px solid rgba(129, 160, 207, 0.12)', background: 'rgba(15, 26, 45, 0.66)' }}>
                <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.84rem' }}>{t('dashboard.netChange')}</span>
                <strong className={toneByValue(summary.total_pnl) === 'positive' ? 'metric-positive' : toneByValue(summary.total_pnl) === 'negative' ? 'metric-negative' : ''} style={{ fontSize: '1.12rem' }}>
                  {formatNumber(summary.total_pnl)}
                </strong>
              </div>
            </div>

            {activeView === 'month' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, minmax(0, 1fr))', gap: 10 }}>
                {weekdayLabels.map((label, i) => (
                  <div key={label} style={{ padding: '0 6px 4px', color: 'var(--color-text-secondary)', fontSize: '0.8rem', fontWeight: 600, textAlign: 'center' }}>{t(weekdayKeys[i])}</div>
                ))}
                {monthCells.map((cell) => {
                  const tone = toneByValue(cell.item?.pnl ?? null)
                  return (
                    <div key={cell.key} style={{
                      minHeight: 136, padding: 16, borderRadius: 22,
                      border: `1px solid ${tone === 'positive' ? 'rgba(54, 208, 165, 0.4)' : tone === 'negative' ? 'rgba(255, 104, 135, 0.38)' : 'rgba(129, 160, 207, 0.1)'}`,
                      background: tone === 'positive' ? 'linear-gradient(180deg, rgba(8, 43, 40, 0.88), rgba(6, 20, 26, 0.92))'
                        : tone === 'negative' ? 'linear-gradient(180deg, rgba(56, 16, 28, 0.86), rgba(23, 10, 18, 0.94))'
                        : 'linear-gradient(180deg, rgba(11, 20, 37, 0.94), rgba(8, 14, 28, 0.94))',
                      display: 'grid', alignContent: 'space-between', gap: 10,
                      opacity: cell.isCurrentMonth ? 1 : 0.3,
                    }}>
                      {cell.isCurrentMonth && cell.item && (
                        <>
                          <div style={{ color: '#b9c8e7', fontSize: '1.08rem', fontWeight: 700 }}>{cell.label}</div>
                          <div style={{ color: '#ebf5ff', fontSize: '1.95rem', fontWeight: 700, letterSpacing: '-0.06em' }}>
                            {formatSignedInteger(cell.item.pnl, t)}
                          </div>
                          <div style={{ color: '#c6d7f2', fontSize: '0.96rem' }}>
                            {formatSignedPercent(cell.item.twr) || t('common.noData')}
                          </div>
                        </>
                      )}
                    </div>
                  )
                })}
              </div>
            )}

            {activeView !== 'month' && (
              <div style={{ display: 'grid', gridTemplateColumns: activeView === 'all-years' ? 'repeat(auto-fit, minmax(180px, 1fr))' : 'repeat(4, minmax(0, 1fr))', gap: 12 }}>
                {response.items.map((item) => {
                  const tone = toneByValue(item.pnl)
                  return (
                    <div key={item.period_key} style={{
                      minHeight: 136, padding: 16, borderRadius: 22,
                      border: `1px solid ${tone === 'positive' ? 'rgba(54, 208, 165, 0.4)' : tone === 'negative' ? 'rgba(255, 104, 135, 0.38)' : 'rgba(129, 160, 207, 0.1)'}`,
                      background: tone === 'positive' ? 'linear-gradient(180deg, rgba(8, 43, 40, 0.88), rgba(6, 20, 26, 0.92))'
                        : tone === 'negative' ? 'linear-gradient(180deg, rgba(56, 16, 28, 0.86), rgba(23, 10, 18, 0.94))'
                        : 'linear-gradient(180deg, rgba(11, 20, 37, 0.94), rgba(8, 14, 28, 0.94))',
                      display: 'grid', alignContent: 'space-between', gap: 10,
                    }}>
                      <div style={{ color: '#b9c8e7', fontSize: '1.08rem', fontWeight: 700 }}>{item.label}</div>
                      <div style={{ color: '#ebf5ff', fontSize: '1.95rem', fontWeight: 700, letterSpacing: '-0.06em' }}>
                        {formatSignedInteger(item.pnl, t)}
                      </div>
                      <div style={{ color: '#c6d7f2', fontSize: '0.96rem' }}>
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
