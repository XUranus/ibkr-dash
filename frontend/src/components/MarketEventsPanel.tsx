import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { fetchUpcomingEvents, fetchMarketEventAnalysis, type MarketEvent, type MarketEventAnalysis } from '@/api/marketEvents'

const CATEGORY_COLORS: Record<string, string> = {
  FED: '#D29922',
  MACRO: '#58A6FF',
  MARKET: '#8B949E',
  COMPANY: '#3FB950',
}

const IMPORTANCE_STYLES: Record<string, { bg: string; color: string }> = {
  CRITICAL: { bg: 'rgba(248,81,73,0.1)', color: '#F85149' },
  HIGH: { bg: 'rgba(210,153,34,0.1)', color: '#D29922' },
  MEDIUM: { bg: 'rgba(88,166,255,0.06)', color: '#58A6FF' },
  LOW: { bg: 'rgba(110,118,129,0.1)', color: '#8B949E' },
}

function formatEventDate(iso: string): { date: string; time: string } {
  const d = new Date(iso)
  const month = (d.getMonth() + 1).toString().padStart(2, '0')
  const day = d.getDate().toString().padStart(2, '0')
  const hours = d.getHours().toString().padStart(2, '0')
  const minutes = d.getMinutes().toString().padStart(2, '0')
  return { date: `${month}-${day}`, time: `${hours}:${minutes}` }
}

function formatRelativeTime(iso: string, locale?: string): string {
  const now = Date.now()
  const then = new Date(iso).getTime()
  const diffSec = Math.floor((now - then) / 1000)
  const rtf = new Intl.RelativeTimeFormat(locale || 'en', { numeric: 'auto' })
  if (diffSec < 60) return rtf.format(-diffSec, 'second')
  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return rtf.format(-diffMin, 'minute')
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return rtf.format(-diffHr, 'hour')
  const diffDay = Math.floor(diffHr / 24)
  return rtf.format(-diffDay, 'day')
}

export default function MarketEventsPanel() {
  const { t, i18n } = useTranslation()
  const [events, setEvents] = useState<MarketEvent[]>([])
  const [analysis, setAnalysis] = useState<MarketEventAnalysis | null>(null)
  const [loading, setLoading] = useState(true)

  const isZh = i18n.language?.startsWith('zh')

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    Promise.all([
      fetchUpcomingEvents(30).catch(() => ({ items: [], total: 0 })),
      fetchMarketEventAnalysis().catch(() => ({ analysis: null })),
    ]).then(([eventsRes, analysisRes]) => {
      if (cancelled) return
      setEvents(eventsRes.items || [])
      setAnalysis(analysisRes.analysis)
    }).finally(() => {
      if (!cancelled) setLoading(false)
    })

    return () => { cancelled = true }
  }, [])

  // i18n importance labels
  const importanceLabel = (imp: string) => {
    const map: Record<string, string> = {
      CRITICAL: t('dashboard.importanceCritical'),
      HIGH: t('dashboard.importanceHigh'),
      MEDIUM: t('dashboard.importanceMedium'),
      LOW: t('dashboard.importanceLow'),
    }
    return map[imp] || imp
  }

  if (loading) return null

  const analysisContent = analysis ? (isZh ? analysis.content_zh : analysis.content_en) : null

  return (
    <div className="surface-panel">
      <div className="surface-panel__content" style={{ padding: '10px 12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <p className="eyebrow" style={{ margin: 0 }}>{t('dashboard.keyEvents')}</p>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
            {events.length} {t('dashboard.events')}
          </span>
        </div>

        {/* AI Risk Analysis */}
        {analysisContent && (
          <div style={{
            marginBottom: 10,
            padding: '8px 10px',
            borderRadius: 6,
            border: '1px solid rgba(88,166,255,0.15)',
            background: 'rgba(88,166,255,0.04)',
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              marginBottom: 6,
            }}>
              <span style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                padding: '1px 5px',
                borderRadius: 3,
                background: 'rgba(88,166,255,0.15)',
                color: '#58A6FF',
                letterSpacing: '0.05em',
              }}>
                AI
              </span>
              <span style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                color: 'var(--color-text-secondary)',
              }}>
                {t('dashboard.marketRiskAnalysis')}
              </span>
              {analysis?.created_at && (
                <span style={{
                  fontSize: '0.65rem',
                  color: 'var(--color-text-muted)',
                  marginLeft: 'auto',
                }}>
                  {formatRelativeTime(analysis.created_at, i18n.language)}
                </span>
              )}
            </div>
            <div className="copilot-markdown" style={{ fontSize: '0.82rem', lineHeight: 1.6 }}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {analysisContent}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {events.length === 0 ? (
          <p style={{ color: 'var(--color-text-muted)', fontSize: '0.88rem', padding: '12px 0' }}>
            {t('dashboard.noEvents')}
          </p>
        ) : (
          <table className="data-table" style={{ minWidth: 'auto' }}>
            <thead>
              <tr>
                <th style={{ width: '50px' }}>{t('dashboard.date')}</th>
                <th>{t('dashboard.event')}</th>
                <th style={{ width: '50px', textAlign: 'right' }}>{t('dashboard.level')}</th>
              </tr>
            </thead>
            <tbody>
              {events.slice(0, 12).map((event) => {
                const { date } = formatEventDate(event.scheduled_at)
                const catColor = CATEGORY_COLORS[event.category] || '#8B949E'
                const impStyle = IMPORTANCE_STYLES[event.importance] || IMPORTANCE_STYLES.MEDIUM
                const title = isZh ? event.title : (event.title_en || event.title)

                return (
                  <tr key={event.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--color-text-secondary)' }}>
                      {date}
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }}>
                        <span style={{ width: 3, height: 3, borderRadius: '50%', background: catColor, flexShrink: 0 }} />
                        <span style={{ fontSize: '0.88rem', color: 'var(--color-text-bright)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {title}
                        </span>
                      </div>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <span style={{
                        fontSize: '0.72rem',
                        fontWeight: 600,
                        padding: '1px 5px',
                        borderRadius: 2,
                        background: impStyle.bg,
                        color: impStyle.color,
                        whiteSpace: 'nowrap',
                      }}>
                        {importanceLabel(event.importance)}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
