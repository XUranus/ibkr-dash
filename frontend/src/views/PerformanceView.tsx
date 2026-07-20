/** Performance page -- account performance with TWR calculation. */

import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { request } from '@/api/http'
import { formatNumber, formatSignedNumber, formatPercent, formatSignedPercent, pnlClass } from '@/utils/format'
import StatCard from '@/components/StatCard'
import type { PerformanceSeriesResponse, AccountPerformancePoint } from '@/types/performance'

function formatMoney(value: number | null | undefined): string {
  if (value == null) return '--'
  return `$${formatNumber(value)}`
}

export default function PerformanceView() {
  const { t } = useTranslation()
  const [data, setData] = useState<PerformanceSeriesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const loadData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams()
      if (startDate) params.set('start_date', startDate)
      if (endDate) params.set('end_date', endDate)
      const qs = params.toString()
      const result = await request<PerformanceSeriesResponse>(`/api/performance/account/series${qs ? '?' + qs : ''}`)
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('performance.failedToLoad'))
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, t])

  useEffect(() => { void loadData() }, [loadData])

  const summary = data?.summary
  const series = data?.series || []

  return (
    <section className="page-section">
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease' }}>
        <div className="surface-panel__content">
          <div className="section-header">
            <div>
              <p className="eyebrow">{t('performance.eyebrow')}</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-bright)' }}>{t('performance.title')}</h2>
              <p className="panel-subtitle">{t('performance.subtitle')}</p>
            </div>
          </div>
        </div>
      </section>

      {error && (
        <div className="surface-panel" style={{ marginBottom: 'var(--space-4)', padding: '12px 16px', borderLeft: '3px solid var(--color-negative)' }}>
          <p style={{ color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>{error}</p>
        </div>
      )}

      {/* Date filters */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 'var(--space-4)', alignItems: 'center' }}>
        <label style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)' }}>
          {t('performance.startDate')}
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="input" style={{ marginLeft: 8, width: 140 }} />
        </label>
        <label style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)' }}>
          {t('performance.endDate')}
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="input" style={{ marginLeft: 8, width: 140 }} />
        </label>
        <button className="btn btn--ghost btn--sm" onClick={loadData} disabled={loading}>
          {t('performance.refresh')}
        </button>
      </div>

      {loading ? (
        <p style={{ color: 'var(--color-text-muted)' }}>{t('performance.loading')}</p>
      ) : !summary ? (
        <p style={{ color: 'var(--color-text-muted)' }}>{t('performance.noData')}</p>
      ) : (
        <>
          {/* Summary cards */}
          <section className="stats-grid stats-grid--summary" style={{ marginBottom: 'var(--space-4)' }}>
            <StatCard title={t('performance.startNav')} value={formatMoney(summary.start_nav)} tone="neutral" />
            <StatCard title={t('performance.endNav')} value={formatMoney(summary.end_nav)} tone="neutral" />
            <StatCard title={t('performance.twrReturn')} value={formatPercent(summary.twr_total_return != null ? summary.twr_total_return * 100 : null)} tone={summary.twr_total_return == null ? 'neutral' : summary.twr_total_return >= 0 ? 'positive' : 'negative'} />
            <StatCard title={t('performance.annualized')} value={formatPercent(summary.annualized_return != null ? summary.annualized_return * 100 : null)} tone="accent" />
            <StatCard title={t('performance.maxDrawdown')} value={formatPercent(summary.max_drawdown != null ? summary.max_drawdown * 100 : null)} tone="negative" />
            <StatCard title={t('performance.volatility')} value={formatPercent(summary.volatility != null ? summary.volatility * 100 : null)} tone="neutral" />
            <StatCard title={t('performance.sharpe')} value={summary.sharpe_ratio != null ? summary.sharpe_ratio.toFixed(2) : '--'} tone="neutral" />
            <StatCard title={t('performance.cashFlows')} value={formatMoney(summary.total_net_cash_flow)} tone="neutral" />
          </section>

          {/* Data quality */}
          <div style={{ marginBottom: 'var(--space-4)', padding: 8, background: 'rgba(10,14,26,0.3)', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
            {t('performance.dataQuality')} {summary.data_quality}
            {summary.data_limitations.length > 0 && (
              <span> ({summary.data_limitations.join(', ')})</span>
            )}
          </div>

          {/* Series table */}
          <div className="surface-panel">
            <div className="surface-panel__content" style={{ padding: 0 }}>
              <div className="table-shell">
                <table className="data-table" style={{ minWidth: 700 }}>
                  <thead>
                    <tr>
                      <th style={{ width: '20%' }}>{t('performance.date')}</th>
                      <th style={{ width: '20%', textAlign: 'right' }}>{t('performance.nav')}</th>
                      <th style={{ width: '20%', textAlign: 'right' }}>{t('performance.cashFlow')}</th>
                      <th style={{ width: '20%', textAlign: 'right' }}>{t('performance.dailyReturn')}</th>
                      <th style={{ width: '20%', textAlign: 'right' }}>{t('performance.twrIndex')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {series.slice(-50).map((p: AccountPerformancePoint) => (
                      <tr key={p.date}>
                        <td><span className="terminal-muted">{p.date}</span></td>
                        <td className="table-number"><span className="cell-number">{formatMoney(p.nav)}</span></td>
                        <td className="table-number"><span className={`cell-number ${pnlClass(p.net_cash_flow)}`}>{p.net_cash_flow !== 0 ? formatSignedNumber(p.net_cash_flow) : '--'}</span></td>
                        <td className="table-number"><span className={`cell-number ${pnlClass(p.daily_return)}`}>{p.daily_return != null ? formatSignedPercent(p.daily_return * 100) : '--'}</span></td>
                        <td className="table-number"><span className="cell-number">{p.twr_index?.toFixed(4) || '--'}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {series.length > 50 && (
                <p style={{ textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '0.78rem', padding: '8px 0' }}>
                  {t('performance.showingLast', { total: series.length })}
                </p>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  )
}
