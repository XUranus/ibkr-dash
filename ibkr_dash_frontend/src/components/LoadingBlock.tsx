export default function LoadingBlock() {
  return (
    <section className="surface-panel">
      <div className="surface-panel__content" style={{ display: 'grid', gap: 'var(--space-4)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--space-3)' }}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} style={{
              height: '7rem',
              borderRadius: '18px',
              background: 'rgba(18, 31, 52, 0.8)',
              position: 'relative',
              overflow: 'hidden',
            }}>
              <div style={{
                position: 'absolute',
                inset: 0,
                transform: 'translateX(-100%)',
                background: 'linear-gradient(90deg, transparent, rgba(86, 213, 255, 0.15), transparent)',
                animation: 'skeleton-wave 1.5s linear infinite',
              }} />
            </div>
          ))}
        </div>
        <div style={{ display: 'grid', gap: 'var(--space-3)' }}>
          <div style={{ height: '3rem', borderRadius: '16px', background: 'rgba(18, 31, 52, 0.8)', overflow: 'hidden' }}>
            <div style={{ width: '100%', height: '100%', background: 'linear-gradient(90deg, transparent, rgba(86, 213, 255, 0.1), transparent)', animation: 'skeleton-wave 1.5s linear infinite' }} />
          </div>
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={`row-${i}`} style={{ height: '3.4rem', borderRadius: '14px', background: 'rgba(18, 31, 52, 0.8)', overflow: 'hidden' }}>
              <div style={{ width: '100%', height: '100%', background: 'linear-gradient(90deg, transparent, rgba(86, 213, 255, 0.08), transparent)', animation: 'skeleton-wave 1.5s linear infinite' }} />
            </div>
          ))}
        </div>
      </div>
      <style>{`
        @keyframes skeleton-wave {
          to { transform: translateX(100%); }
        }
      `}</style>
    </section>
  )
}
