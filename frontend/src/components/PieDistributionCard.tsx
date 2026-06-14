import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { formatNumber } from '@/utils/format'

export interface PieSegmentItem {
  label: string
  value: number
  color: string
  note?: string
  members?: string[]
}

interface Props {
  title: string
  subtitle: string
  items: PieSegmentItem[]
}

export default function PieDistributionCard({ title, subtitle, items }: Props) {
  const { t } = useTranslation()
  const [hoveredItem, setHoveredItem] = useState<PieSegmentItem | null>(null)
  const chartSize = 160
  const strokeWidth = 22
  const radius = (chartSize - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius

  const total = useMemo(() => items.reduce((sum, item) => sum + item.value, 0), [items])

  const chartSegments = useMemo(() => {
    if (total <= 0) return []
    let currentOffset = 0
    return items.filter((item) => item.value > 0).map((item) => {
      const ratio = item.value / total
      const length = ratio * circumference
      const segment = {
        ...item, ratio,
        dashArray: `${length} ${circumference - length}`,
        dashOffset: -currentOffset,
      }
      currentOffset += length
      return segment
    })
  }, [items, total, circumference])

  function pct(value: number): string {
    if (total <= 0) return '0.0%'
    return `${((value / total) * 100).toFixed(1)}%`
  }

  function membersText(item: PieSegmentItem): string {
    if (!item.members || item.members.length === 0) return t('common.noDetails')
    return item.members.join(', ')
  }

  return (
    <div className="surface-panel" style={{ height: '100%', overflow: 'visible' }}>
      <div className="surface-panel__content" style={{ display: 'grid', gap: 'var(--space-4)', height: '100%' }}>
        <div>
          <h4 style={{ margin: 0, fontSize: '1rem' }}>{title}</h4>
          <p style={{ margin: '0.45rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.92rem' }}>{subtitle}</p>
        </div>

        {chartSegments.length === 0 ? (
          <div className="empty-state" style={{ minHeight: 280 }}>{t('common.noData')}</div>
        ) : (
          <div style={{ display: 'grid', gap: 'var(--space-4)' }}>
            <div style={{ position: 'relative', width: 180, height: 180, justifySelf: 'center' }}>
              {/* Floating tooltip on hover */}
              {hoveredItem && hoveredItem.members && hoveredItem.members.length > 0 && (
                <div style={{
                  position: 'absolute', bottom: '100%', left: '50%', transform: 'translateX(-50%)',
                  marginBottom: 8, padding: '8px 12px', borderRadius: 'var(--radius-md)',
                  background: 'var(--color-bg-panel-strong)', border: '1px solid var(--color-border-strong)',
                  boxShadow: 'var(--shadow-elevated)', zIndex: 10, minWidth: 160, maxWidth: 280,
                  pointerEvents: 'none',
                }}>
                  <div style={{ fontSize: '0.72rem', color: hoveredItem.color, fontWeight: 600, marginBottom: 4 }}>
                    {hoveredItem.label} · {pct(hoveredItem.value)}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                    {hoveredItem.members.slice(0, 10).join(', ')}
                    {hoveredItem.members.length > 10 && ` +${hoveredItem.members.length - 10} more`}
                  </div>
                </div>
              )}
              <svg viewBox={`0 0 ${chartSize} ${chartSize}`} style={{ width: '100%', height: '100%', transform: 'rotate(-90deg)' }}>
                <circle cx={chartSize / 2} cy={chartSize / 2} r={radius} fill="none" stroke="rgba(129, 160, 207, 0.12)" strokeWidth={strokeWidth} />
                {chartSegments.map((seg) => (
                  <circle
                    key={seg.label}
                    cx={chartSize / 2}
                    cy={chartSize / 2}
                    r={radius}
                    fill="none"
                    stroke={seg.color}
                    strokeWidth={strokeWidth}
                    strokeDasharray={seg.dashArray}
                    strokeDashoffset={seg.dashOffset}
                    strokeLinecap="butt"
                    onMouseEnter={() => setHoveredItem(seg)}
                    onMouseLeave={() => setHoveredItem(null)}
                    style={{ cursor: 'pointer' }}
                  />
                ))}
              </svg>
              <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', display: 'grid', gap: 4, textAlign: 'center' }}>
                {hoveredItem ? (
                  <>
                    <span style={{ color: hoveredItem.color, fontSize: '0.82rem', fontWeight: 600 }}>{hoveredItem.label}</span>
                    <strong style={{ fontSize: '1.05rem' }}>{formatNumber(hoveredItem.value, 2)}</strong>
                    <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.78rem' }}>{pct(hoveredItem.value)}</span>
                  </>
                ) : (
                  <>
                    <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.82rem' }}>{t('common.total')}</span>
                    <strong style={{ fontSize: '1.05rem' }}>{formatNumber(total, 2)}</strong>
                  </>
                )}
              </div>
            </div>

            <div style={{ display: 'grid', gap: 12 }}>
              {chartSegments.map((seg) => (
                <div key={seg.label} style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 'var(--space-4)', alignItems: 'start', padding: '14px 16px', borderRadius: 14, border: '1px solid rgba(129, 160, 207, 0.1)', background: 'rgba(15, 26, 45, 0.72)' }}>
                  <div style={{ display: 'flex', gap: 12, minWidth: 0, alignItems: 'flex-start' }}>
                    <span style={{ width: 12, height: 12, borderRadius: 999, marginTop: '0.35rem', flexShrink: 0, backgroundColor: seg.color }} />
                    <div>
                      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12 }}>
                        <strong>{seg.label}</strong>
                        <em style={{ color: 'var(--color-accent-strong)', fontStyle: 'normal', fontSize: '0.86rem' }}>{pct(seg.value)}</em>
                      </div>
                      <p style={{ margin: '0.2rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.86rem' }}>{seg.note || t('common.category')}</p>
                      <small style={{ display: 'block', marginTop: '0.35rem', color: 'rgba(194, 207, 232, 0.9)', fontSize: '0.82rem' }}>
                        {t('common.includes')} {membersText(seg)}
                      </small>
                    </div>
                  </div>
                  <strong style={{ fontSize: '1rem' }}>{formatNumber(seg.value, 2)}</strong>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
