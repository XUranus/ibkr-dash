import AdminTabs from '@/components/AdminTabs'

export default function AdminLongbridgeMcpView() {
  return (
    <section className="page-section">
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease' }}>
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">ADMIN</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-bright)' }}>Longbridge MCP</h2>
              <p className="panel-subtitle">Configure Longbridge market data integration.</p>
            </div>
          </div>
          <AdminTabs />
        </div>
      </section>

      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.1s both' }}>
        <div className="surface-panel__content">
          <p className="eyebrow">STATUS</p>
          <div style={{ marginTop: 12 }}>
            <span className="tag tag--warning">NOT CONFIGURED</span>
            <p style={{ marginTop: 12, color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
              Longbridge integration is not configured. To enable public market data for AI agents,
              set the following environment variables in the backend:
            </p>
            <pre style={{ marginTop: 12, padding: '12px 16px', borderRadius: 'var(--radius-md)', background: 'rgba(10,14,26,0.6)', border: '1px solid var(--color-border-subtle)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--color-text-secondary)', overflow: 'auto' }}>
{`LONGBRIDGE_APP_KEY=your-app-key
LONGBRIDGE_APP_SECRET=your-app-secret
LONGBRIDGE_ACCESS_TOKEN=your-access-token`}
            </pre>
          </div>
        </div>
      </section>
    </section>
  )
}
