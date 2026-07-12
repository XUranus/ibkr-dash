/** Knowledge base page -- placeholder for future knowledge management. */

export default function KnowledgeView() {
  return (
    <section className="page-section" style={{ animation: 'slideUp 0.4s ease' }}>
      <header style={{ marginBottom: 'var(--space-6)' }}>
        <p className="eyebrow">Knowledge</p>
        <h1 className="page-title">Knowledge Base</h1>
        <p className="page-subtitle">Investment research articles and knowledge entries</p>
      </header>

      <div className="surface-panel">
        <div className="surface-panel__content" style={{ padding: 32, textAlign: 'center' }}>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', marginBottom: 12 }}>
            Knowledge base is under development.
          </p>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '0.82rem' }}>
            This feature will allow you to store and manage investment research articles,
            analysis notes, and knowledge entries linked to your portfolio symbols.
          </p>
        </div>
      </div>
    </section>
  )
}
