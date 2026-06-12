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
    neutral: 'var(--color-text-bright)',
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: 4,
      padding: '8px 12px',
      borderRadius: 'var(--radius-sm)',
      background: 'var(--color-bg-elevated)',
      border: '1px solid var(--color-border-subtle)',
      minHeight: 0,
    }}>
      {/* Label */}
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '0.6rem',
        fontWeight: 500,
        color: 'var(--color-text-muted)',
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
      }}>
        {title}
      </span>

      {/* Value + delta */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '1.1rem',
          fontWeight: 700,
          letterSpacing: '-0.02em',
          lineHeight: 1.2,
          color: toneColorMap[tone] || 'var(--color-text-bright)',
          fontVariantNumeric: 'tabular-nums',
        }}>
          {value}
        </span>
        {deltaPercent && (
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.68rem',
            fontWeight: 600,
            color: deltaTone === 'positive' ? 'var(--color-positive)' : deltaTone === 'negative' ? 'var(--color-negative)' : 'var(--color-text-muted)',
          }}>
            {deltaPercent}
          </span>
        )}
      </div>

      {/* Helper */}
      {helper && (
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '0.65rem',
          color: 'var(--color-text-muted)',
        }}>
          {helper}
        </span>
      )}
    </div>
  )
}
