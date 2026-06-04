interface Props {
  title: string
  value: string
  helper?: string
  tone?: 'neutral' | 'positive' | 'negative' | 'accent'
  deltaAmount?: string
  deltaPercent?: string
  deltaTone?: 'neutral' | 'positive' | 'negative' | 'accent'
}

export default function StatCard({ title, value, helper, tone = 'neutral', deltaAmount, deltaPercent, deltaTone }: Props) {
  const toneColorMap: Record<string, string> = {
    positive: 'var(--color-positive)',
    negative: 'var(--color-negative)',
    accent: 'var(--color-accent-strong)',
    neutral: 'var(--color-text-primary)',
  }

  return (
    <div style={{
      position: 'relative',
      overflow: 'hidden',
      borderRadius: 'var(--radius-lg)',
      border: '1px solid rgba(129, 160, 207, 0.12)',
      background: 'linear-gradient(180deg, rgba(16, 28, 50, 0.92), rgba(10, 17, 29, 0.9))',
      minHeight: '118px',
      padding: '18px',
    }}>
      <div style={{ position: 'relative', display: 'grid', gridTemplateColumns: '40px minmax(0, 1fr)', gap: '12px', alignItems: 'start' }}>
        {(deltaAmount || deltaPercent) && (
          <div style={{
            position: 'absolute', top: 0, right: 0,
            display: 'grid', justifyItems: 'end', gap: '2px',
            fontSize: '0.8rem', lineHeight: 1.05,
            color: deltaTone === 'positive' ? 'var(--color-positive)' : deltaTone === 'negative' ? 'var(--color-negative)' : 'var(--color-text-secondary)',
          }}>
            {deltaPercent && <span style={{ whiteSpace: 'nowrap' }}>{deltaPercent}</span>}
            {deltaAmount && <span style={{ whiteSpace: 'nowrap' }}>{deltaAmount}</span>}
          </div>
        )}
        <div style={{
          width: 40, height: 40, display: 'grid', placeItems: 'center',
          borderRadius: 12, border: '1px solid rgba(86, 213, 255, 0.16)',
          background: 'rgba(10, 38, 57, 0.36)',
        }}>
          <span style={{ color: toneColorMap[tone] || 'var(--color-accent-strong)', fontSize: '1.1rem' }}>●</span>
        </div>
        <div style={{ display: 'grid', alignContent: 'start', minWidth: 0 }}>
          <p style={{ margin: 0, color: 'var(--color-text-secondary)', fontSize: '0.92rem' }}>{title}</p>
          <p style={{
            margin: '0.35rem 0 0',
            fontSize: 'clamp(1.45rem, 2.8vw, 1.95rem)',
            fontWeight: 700, letterSpacing: '-0.03em', lineHeight: 1.05,
            whiteSpace: 'nowrap', color: toneColorMap[tone] || 'inherit',
          }}>{value}</p>
          <p style={{ marginTop: '0.35rem', fontSize: '0.92rem', color: 'var(--color-text-secondary)', minHeight: '1rem' }}>
            {helper || ' '}
          </p>
        </div>
      </div>
    </div>
  )
}
