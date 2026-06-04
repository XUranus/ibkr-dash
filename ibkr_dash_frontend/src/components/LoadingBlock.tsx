export default function LoadingBlock() {
  const shimmerStyle = (delay = 0): React.CSSProperties => ({
    position: 'relative' as const,
    overflow: 'hidden' as const,
    borderRadius: 'var(--radius-lg)',
    background: 'rgba(14, 18, 32, 0.7)',
    border: '1px solid var(--color-border-subtle)',
  })

  return (
    <section className="surface-panel">
      <div className="surface-panel__content" style={{ display: 'grid', gap: 'var(--space-4)' }}>
        {/* Stat card skeletons */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--space-4)' }}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} style={{ ...shimmerStyle(), height: '7.5rem', animationDelay: `${i * 0.08}s` }}>
              <div style={{
                position: 'absolute',
                inset: 0,
                background: 'linear-gradient(90deg, transparent 0%, rgba(212,168,67,0.04) 50%, transparent 100%)',
                backgroundSize: '200% 100%',
                animation: 'shimmer 2s ease infinite',
                animationDelay: `${i * 0.15}s`,
              }} />
            </div>
          ))}
        </div>
        {/* Chart skeleton */}
        <div style={{ ...shimmerStyle(), height: '16rem' }}>
          <div style={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(90deg, transparent 0%, rgba(212,168,67,0.03) 50%, transparent 100%)',
            backgroundSize: '200% 100%',
            animation: 'shimmer 2s ease infinite',
            animationDelay: '0.5s',
          }} />
        </div>
        {/* Table skeleton */}
        <div style={{ display: 'grid', gap: 'var(--space-3)' }}>
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={`row-${i}`} style={{ ...shimmerStyle(), height: '3.2rem', borderRadius: 'var(--radius-md)' }}>
              <div style={{
                position: 'absolute',
                inset: 0,
                background: 'linear-gradient(90deg, transparent 0%, rgba(212,168,67,0.025) 50%, transparent 100%)',
                backgroundSize: '200% 100%',
                animation: 'shimmer 2s ease infinite',
                animationDelay: `${0.8 + i * 0.1}s`,
              }} />
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
