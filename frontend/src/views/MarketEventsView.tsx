/** Market events page -- view upcoming and today's market events. */

import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { request } from '@/api/http'
import type { MarketEvent, MarketEventAnalysis } from '@/types/marketEvent'

function importanceTagClass(importance: string): string {
  if (importance === 'CRITICAL') return 'tag--negative'
  if (importance === 'HIGH') return 'tag--warning'
  if (importance === 'MEDIUM') return 'tag--accent'
  return 'tag--neutral'
}

export default function MarketEventsView() {
  const { t, i18n } = useTranslation()
  const [upcoming, setUpcoming] = useState<MarketEvent[]>([])
  const [today, setToday] = useState<MarketEvent[]>([])
  const [analysis, setAnalysis] = useState<MarketEventAnalysis | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [tab, setTab] = useState<'upcoming' | 'today' | 'analysis'>('upcoming')

  const isZh = i18n.language?.startsWith('zh')

  const loadData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [upcomingData, todayData, analysisData] = await Promise.all([
        request<{ items: MarketEvent[] }>('/api/market-events/upcoming?days=30&limit=50'),
        request<{ items: MarketEvent[] }>('/api/market-events/today'),
        request<{ analysis: MarketEventAnalysis | null }>('/api/market-events/analysis'),
      ])
      setUpcoming(upcomingData.items || [])
      setToday(todayData.items || [])
      setAnalysis(analysisData.analysis)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('marketEvents.failedToLoad'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => { void loadData() }, [loadData])

  function formatDate(iso: string): string {
    try {
      const locale = isZh ? 'zh-CN' : 'en-US'
      return new Date(iso).toLocaleDateString(locale, { month: 'short', day: 'numeric', year: 'numeric' })
    } catch {
      return iso.slice(0, 10)
    }
  }

  const events = tab === 'today' ? today : upcoming

  return (
    <section className="page-section" style={{ animation: 'slideUp 0.4s ease' }}>
      <header style={{ marginBottom: 'var(--space-6)' }}>
        <p className="eyebrow">{t('marketEvents.eyebrow')}</p>
        <h1 className="page-title">{t('marketEvents.title')}</h1>
        <p className="page-subtitle">{t('marketEvents.subtitle')}</p>
      </header>

      {error && (
        <div className="surface-panel" style={{ marginBottom: 'var(--space-4)', padding: '12px 16px', borderLeft: '3px solid var(--color-negative)' }}>
          <p style={{ color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>{error}</p>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 'var(--space-4)' }}>
        {(['upcoming', 'today', 'analysis'] as const).map((tabKey) => (
          <button
            key={tabKey}
            className={`btn btn--sm ${tab === tabKey ? 'btn--accent' : 'btn--ghost'}`}
            onClick={() => setTab(tabKey)}
          >
            {tabKey === 'upcoming' ? t('marketEvents.upcoming') : tabKey === 'today' ? t('marketEvents.today') : t('marketEvents.aiAnalysis')}
          </button>
        ))}
        <button className="btn btn--ghost btn--sm" onClick={loadData} disabled={loading}>
          {t('marketEvents.refresh')}
        </button>
      </div>

      {loading ? (
        <p style={{ color: 'var(--color-text-muted)' }}>{t('marketEvents.loading')}</p>
      ) : tab === 'analysis' ? (
        /* Analysis tab */
        <div className="surface-panel">
          <div className="surface-panel__content" style={{ padding: 16 }}>
            {!analysis ? (
              <p style={{ color: 'var(--color-text-muted)' }}>{t('marketEvents.noAnalysis')}</p>
            ) : (
              <div>
                <h3 style={{ marginBottom: 12 }}>{t('marketEvents.aiMarketRiskAnalysis')}</h3>
                <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-text-muted)', marginBottom: 12 }}>
                  {t('marketEvents.generated')} {formatDate(analysis.created_at)}
                </p>
                <div style={{ marginBottom: 16 }}>
                  <h4 style={{ color: 'var(--color-accent-strong)', marginBottom: 8 }}>{t('marketEvents.chinese')}</h4>
                  <div style={{ padding: 12, background: 'rgba(10,14,26,0.5)', borderRadius: 'var(--radius-sm)', whiteSpace: 'pre-wrap', fontSize: '0.85rem', lineHeight: 1.7 }}>
                    {analysis.content_zh}
                  </div>
                </div>
                <div>
                  <h4 style={{ color: 'var(--color-accent-strong)', marginBottom: 8 }}>{t('marketEvents.english')}</h4>
                  <div style={{ padding: 12, background: 'rgba(10,14,26,0.5)', borderRadius: 'var(--radius-sm)', whiteSpace: 'pre-wrap', fontSize: '0.85rem', lineHeight: 1.7 }}>
                    {analysis.content_en}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Events list */
        <div className="surface-panel">
          <div className="surface-panel__content" style={{ padding: 0 }}>
            {events.length === 0 ? (
              <div className="empty-state">{tab === 'today' ? t('marketEvents.noTodayEvents') : t('marketEvents.noUpcomingEvents')}</div>
            ) : (
              <div className="table-shell">
                <table className="data-table" style={{ minWidth: 800 }}>
                  <thead>
                    <tr>
                      <th style={{ width: '15%' }}>{t('marketEvents.date')}</th>
                      <th style={{ width: '35%' }}>{t('marketEvents.event')}</th>
                      <th style={{ width: '15%' }}>{t('marketEvents.category')}</th>
                      <th style={{ width: '15%' }}>{t('marketEvents.importance')}</th>
                      <th style={{ width: '20%' }}>{t('marketEvents.source')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.map((e) => (
                      <tr key={e.id}>
                        <td><span className="terminal-muted">{formatDate(e.scheduled_at)}</span></td>
                        <td>
                          <div className="table-symbol">
                            <span className="table-symbol__code">{e.title}</span>
                            {e.description && <span className="table-symbol__desc">{e.description}</span>}
                          </div>
                        </td>
                        <td><span className="tag tag--accent">{e.category}</span></td>
                        <td><span className={`tag ${importanceTagClass(e.importance)}`}>{e.importance}</span></td>
                        <td><span className="terminal-muted">{e.source}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
