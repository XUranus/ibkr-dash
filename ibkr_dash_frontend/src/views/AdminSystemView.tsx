import { useState, useEffect, useCallback } from 'react'
import { fetchSystemStatus } from '@/api/adminSystem'
import AdminTabs from '@/components/AdminTabs'
import type { AdminSystemStatus } from '@/types/adminSystem'

export default function AdminSystemView() {
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [status, setStatus] = useState<AdminSystemStatus | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      setStatus(await fetchSystemStatus())
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to load system status')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadData() }, [loadData])

  if (loading) {
    return <section className="page-section"><div className="surface-panel"><div className="surface-panel__content">Loading...</div></div></section>
  }

  return (
    <section className="page-section">
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease' }}>
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">ADMIN</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-bright)' }}>System Status</h2>
            </div>
            {status && (
              <span className={`tag ${status.status === 'ok' ? 'tag--positive' : 'tag--negative'}`}>
                {status.status.toUpperCase()}
              </span>
            )}
          </div>
          <AdminTabs />
        </div>
      </section>

      {errorMessage && (
        <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(242,92,92,0.2)', background: 'rgba(242,92,92,0.05)', color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
          {errorMessage}
        </div>
      )}

      {status && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 'var(--space-4)' }}>
          {/* Database */}
          <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.1s both' }}>
            <div className="surface-panel__content">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--color-text-bright)' }}>Database</h3>
                <span className={`tag ${status.database.healthy ? 'tag--positive' : 'tag--negative'}`}>
                  {status.database.healthy ? 'Healthy' : 'Error'}
                </span>
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--color-text-secondary)', marginBottom: 8 }}>
                {status.database.path}
              </div>
              <div style={{ display: 'grid', gap: 6 }}>
                {Object.entries(status.database.record_counts).map(([table, count]) => (
                  <div key={table} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', borderRadius: 'var(--radius-sm)', background: 'rgba(10,14,26,0.4)' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>{table}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--color-text-bright)', fontWeight: 600 }}>{count.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* LLM */}
          <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.2s both' }}>
            <div className="surface-panel__content">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--color-text-bright)' }}>LLM</h3>
                <span className={`tag ${status.llm.configured ? 'tag--positive' : 'tag--warning'}`}>
                  {status.llm.configured ? 'Configured' : 'Not Set'}
                </span>
              </div>
              {[
                { label: 'Model', value: status.llm.model },
                { label: 'Base URL', value: status.llm.base_url },
              ].map((item) => (
                <div key={item.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', borderRadius: 'var(--radius-sm)', background: 'rgba(10,14,26,0.4)', marginBottom: 6 }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>{item.label}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--color-text-bright)' }}>{item.value}</span>
                </div>
              ))}
            </div>
          </section>

          {/* Longbridge */}
          <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.3s both' }}>
            <div className="surface-panel__content">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--color-text-bright)' }}>Longbridge</h3>
                <span className={`tag ${status.longbridge.configured ? 'tag--positive' : 'tag--warning'}`}>
                  {status.longbridge.configured ? 'Configured' : 'Not Set'}
                </span>
              </div>
              <p style={{ margin: 0, color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>
                {status.longbridge.configured ? 'Longbridge API is configured for public market data.' : 'Longbridge is not configured. AI agents will use IBKR data only.'}
              </p>
            </div>
          </section>

          {/* Runtime */}
          <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.4s both' }}>
            <div className="surface-panel__content">
              <h3 style={{ margin: '0 0 12px', fontSize: '1rem', color: 'var(--color-text-bright)' }}>Runtime</h3>
              {[
                { label: 'Environment', value: status.runtime.app_env },
                { label: 'Python', value: status.runtime.python_version.split(' ')[0] },
                { label: 'Platform', value: status.runtime.platform },
                { label: 'Timestamp', value: new Date(status.timestamp).toLocaleString() },
              ].map((item) => (
                <div key={item.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', borderRadius: 'var(--radius-sm)', background: 'rgba(10,14,26,0.4)', marginBottom: 6 }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>{item.label}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--color-text-bright)', maxWidth: '60%', textAlign: 'right', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.value}</span>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </section>
  )
}
