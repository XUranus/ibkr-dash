interface Props {
  title: string
  value: string
  helper?: string
  tone?: 'neutral' | 'positive' | 'negative' | 'accent'
  deltaAmount?: string
  deltaPercent?: string
  deltaTone?: 'neutral' | 'positive' | 'negative' | 'accent'
  icon?: string
}

export default function StatCard({ title, value, helper, tone = 'neutral', deltaAmount, deltaPercent, deltaTone, icon }: Props) {
  const toneColorMap: Record<string, string> = {
    positive: 'var(--color-positive)',
    negative: 'var(--color-negative)',
    accent: 'var(--color-accent-strong)',
    neutral: 'var(--color-text-bright)',
  }

  const accentLine = tone !== 'neutral' ? toneColorMap[tone] : 'var(--color-accent)'

  return (
    <div style={{
      position: 'relative',
      overflow: 'hidden',
      borderRadius: 'var(--radius-lg)',
      border: '1px solid var(--color-border-subtle)',
      background: 'linear-gradient(168deg, rgba(16, 22, 40, 0.9), rgba(10, 14, 26, 0.95))',
      minHeight: '120px',
      padding: '20px 22px',
      transition: 'border-color 0.3s ease, box-shadow 0.3s ease',
    }}
    onMouseEnter={e => {
      e.currentTarget.style.borderColor = 'var(--color-border)'
      e.currentTarget.style.boxShadow = '0 0 24px rgba(212,168,67,0.04)'
    }}
    onMouseLeave={e => {
      e.currentTarget.style.borderColor = 'var(--color-border-subtle)'
      e.currentTarget.style.boxShadow = 'none'
    }}
    >
      {/* Accent left bar */}
      <div style={{
        position: 'absolute',
        left: 0,
        top: '20%',
        bottom: '20%',
        width: 2,
        background: accentLine,
        borderRadius: 1,
        opacity: 0.6,
      }} />

      {/* Delta badges */}
      {(deltaAmount || deltaPercent) && (
        <div style={{
          position: 'absolute', top: 14, right: 16,
          display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2,
        }}>
          {deltaPercent && (
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.72rem',
              fontWeight: 600,
              color: deltaTone === 'positive' ? 'var(--color-positive)' : deltaTone === 'negative' ? 'var(--color-negative)' : 'var(--color-text-muted)',
              letterSpacing: '0.02em',
            }}>
              {deltaPercent}
            </span>
          )}
          {deltaAmount && (
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.68rem',
              color: 'var(--color-text-muted)',
            }}>
              {deltaAmount}
            </span>
          )}
        </div>
      )}

      <div style={{ display: 'grid', gap: '10px', alignContent: 'start', minHeight: '80px' }}>
        {/* Label */}
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '0.68rem',
          fontWeight: 500,
          color: 'var(--color-text-muted)',
          letterSpacing: '0.14em',
          textTransform: 'uppercase',
        }}>
          {icon && <span style={{ marginRight: 6, opacity: 0.6 }}>{icon}</span>}
          {title}
        </span>

        {/* Value */}
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 'clamp(1.5rem, 3vw, 2.1rem)',
          fontWeight: 700,
          letterSpacing: '-0.03em',
          lineHeight: 1,
          color: toneColorMap[tone] || 'var(--color-text-bright)',
          fontVariantNumeric: 'tabular-nums',
        }}>
          {value}
        </span>

        {/* Helper */}
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '0.75rem',
          color: 'var(--color-text-muted)',
          minHeight: '1rem',
        }}>
          {helper || ' '}
        </span>
      </div>
    </div>
  )
}
