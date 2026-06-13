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
          <div style={{ display: 'grid', gap: 1 }}>
            {events.slice(0, 12).map((event) => {
              const { date, time } = formatEventDate(event.scheduled_at)
              const catColor = CATEGORY_COLORS[event.category] || '#8B949E'
              const impStyle = IMPORTANCE_STYLES[event.importance] || IMPORTANCE_STYLES.MEDIUM
              const title = isZh ? event.title : (event.title_en || event.title)

              return (
                <div key={event.id} style={{
                  display: 'grid',
                  gridTemplateColumns: '48px 1fr',
                  gap: 8,
                  padding: '5px 6px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'var(--color-bg-elevated)',
                  borderLeft: `2px solid ${catColor}`,
                }}>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', color: 'var(--color-text-secondary)' }}>{date}</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.62rem', color: 'var(--color-text-muted)' }}>{time}</div>
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--color-text-bright)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {title}
                      </span>
                      <span style={{
                        fontSize: '0.55rem',
                        fontWeight: 600,
                        padding: '1px 4px',
                        borderRadius: 2,
                        background: impStyle.bg,
                        color: impStyle.color,
                        flexShrink: 0,
                      }}>
                        {event.importance}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.62rem', color: 'var(--color-text-muted)', marginTop: 1 }}>
                      {event.category}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
