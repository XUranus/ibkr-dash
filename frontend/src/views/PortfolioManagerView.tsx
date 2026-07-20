/** Portfolio manager page -- portfolio allocation and rebalancing. */

import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { request } from '@/api/http'
import { formatNumber, formatSignedNumber, pnlClass } from '@/utils/format'
import type { PositionItem } from '@/types/positions'

export default function PortfolioManagerView() {
  const { t } = useTranslation()
  const [positions, setPositions] = useState<PositionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await request<{ items: PositionItem[] }>('/api/positions?limit=100')
      setPositions(data.items || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : t('portfolio.failedToLoad'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => { void loadData() }, [loadData])

  const totalValue = useMemo(() => positions.reduce((sum, p) => sum + (p.position_value || 0), 0), [positions])

  return (
    <section className="page-section">
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease' }}>
        <div className="surface-panel__content">
          <div className="section-header">
            <div>
              <p className="eyebrow">{t('portfolio.eyebrow')}</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-bright)' }}>{t('portfolio.title')}</h2>
              <p className="panel-subtitle">{t('portfolio.subtitle')}</p>
            </div>
          </div>
        </div>
      </section>

      {error && (
        <div className="surface-panel" style={{ marginBottom: 'var(--space-4)', padding: '12px 16px', borderLeft: '3px solid var(--color-negative)' }}>
          <p style={{ color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>{error}</p>
        </div>
      )}

      {loading ? (
        <p style={{ color: 'var(--color-text-muted)' }}>{t('portfolio.loading')}</p>
      ) : (
        <div className="surface-panel">
          <div className="surface-panel__content" style={{ padding: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 16 }}>
              <div style={{ padding: 12, background: 'rgba(10,14,26,0.5)', borderRadius: 'var(--radius-sm)' }}>
                <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', color: 'var(--color-text-muted)', marginBottom: 4 }}>{t('portfolio.totalValue')}</p>
                <p style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--color-accent-strong)', margin: 0 }}>
                  ${totalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
              </div>
              <div style={{ padding: 12, background: 'rgba(10,14,26,0.5)', borderRadius: 'var(--radius-sm)' }}>
                <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', color: 'var(--color-text-muted)', marginBottom: 4 }}>{t('portfolio.positions')}</p>
                <p style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--color-text-primary)', margin: 0 }}>{positions.length}</p>
              </div>
            </div>

            <div className="table-shell">
              <table className="data-table" style={{ minWidth: 700 }}>
                <thead>
                  <tr>
                    <th style={{ width: '30%' }}>{t('portfolio.symbol')}</th>
                    <th style={{ width: '25%', textAlign: 'right' }}>{t('portfolio.value')}</th>
                    <th style={{ width: '20%', textAlign: 'right' }}>{t('portfolio.pctNav')}</th>
                    <th style={{ width: '25%', textAlign: 'right' }}>{t('portfolio.unrealizedPnl')}</th>
                  </tr>
                </thead>
                <tbody>
                  {positions
                    .sort((a, b) => (b.position_value || 0) - (a.position_value || 0))
                    .map((p) => {
                      const pct = totalValue > 0 ? ((p.position_value || 0) / totalValue) * 100 : 0
                      const pnl = p.total_unrealized_pnl || 0
                      return (
                        <tr key={p.symbol}>
                          <td>
                            <div className="table-symbol">
                              <span className="table-symbol__code">{p.symbol}</span>
                              <span className="table-symbol__desc">{p.description || '--'}</span>
                            </div>
                          </td>
                          <td className="table-number"><span className="cell-number">${formatNumber(p.position_value || 0)}</span></td>
                          <td className="table-number"><span className="cell-number">{pct.toFixed(1)}%</span></td>
                          <td className="table-number"><span className={`cell-number ${pnlClass(pnl)}`}>{formatSignedNumber(pnl)}</span></td>
                        </tr>
                      )
                    })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
