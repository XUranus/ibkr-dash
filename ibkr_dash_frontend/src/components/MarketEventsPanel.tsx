import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchUpcomingEvents, type MarketEvent } from '@/api/marketEvents'

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

export default function MarketEventsPanel() {
  const { t, i18n } = useTranslation()
  const [events, setEvents] = useState<MarketEvent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchUpcomingEvents(30)
      .then((res) => { if (!cancelled) setEvents(res.items || []) })
      .catch(() => { /* no events available */ })
      .finally(() => { if (!cancelled) setLoading(false) })
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

  const isZh = i18n.language?.startsWith('zh')

  if (loading) return null

  return (
    <div className="surface-panel">
      <div className="surface-panel__content" style={{ padding: '10px 12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <p className="eyebrow" style={{ margin: 0 }}>{t('dashboard.keyEvents')}</p>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6rem', color: 'var(--color-text-muted)' }}>
            {events.length} {t('dashboard.events')}
          </span>
        </div>

        {events.length === 0 ? (
          <p style={{ color: 'var(--color-text-muted)', fontSize: '0.78rem', padding: '12px 0' }}>
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
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-text-secondary)' }}>
                      {date}
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }}>
                        <span style={{ width: 3, height: 3, borderRadius: '50%', background: catColor, flexShrink: 0 }} />
                        <span style={{ fontSize: '0.78rem', color: 'var(--color-text-bright)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {title}
                        </span>
                      </div>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <span style={{
                        fontSize: '0.6rem',
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
