import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchSystemStatus } from '@/api/adminSystem'
import AdminTabs from '@/components/AdminTabs'
import type { AdminSystemStatus, SystemComponentStatusLevel } from '@/types/adminSystem'

function statusTagClass(level: SystemComponentStatusLevel): string {
  switch (level) {
    case 'ok': return 'tag-positive'
    case 'error': return 'tag-negative'
    default: return 'tag-warning'
  }
}

function statusLabel(level: SystemComponentStatusLevel): string {
  switch (level) {
    case 'ok': return 'OK'
    case 'warning': return 'Warning'
    case 'error': return 'Error'
    case 'disabled': return 'Disabled'
    case 'unknown': return 'Unknown'
    default: return level
  }
}

function overallTagClass(level: string): string {
  switch (level) {
    case 'ok': return 'tag-positive'
    case 'error': return 'tag-negative'
    default: return 'tag-warning'
  }
}

function overallLabel(level: string): string {
  switch (level) {
    case 'ok': return 'System OK'
    case 'warning': return 'Partial Issues'
    case 'error': return 'System Error'
    default: return level
  }
}

export default function AdminSystemView() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
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

  async function refresh(): Promise<void> {
    setRefreshing(true)
    setErrorMessage('')
    try {
      setStatus(await fetchSystemStatus())
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to refresh')
    } finally {
      setRefreshing(false)
    }
  }

  useEffect(() => { void loadData() }, [loadData])

  return (
    <section className="page-section">
      <section className="surface-panel">
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">ADMIN</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem' }}>System Status</h2>
              <p className="panel-subtitle">Aggregate configuration and connection status for all components.</p>
            </div>
            {status && (
              <span style={{ padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: '0.82rem', fontWeight: 600 }}>{overallLabel(status.overall_status)}</span>
            )}
          </div>
          <AdminTabs />
        </div>
      </section>

      {loading ? (
        <section className="surface-panel"><div className="surface-panel__content"><div className="empty-state">Loading...</div></div></section>
      ) : errorMessage ? (
        <section className="surface-panel"><div className="surface-panel__content"><div className="empty-state" style={{ color: 'var(--color-negative)' }}>{errorMessage}</div></div></section>
      ) : status && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button className="btn btn--ghost" disabled={refreshing} onClick={() => void refresh()}>{refreshing ? 'Refreshing...' : 'Refresh'}</button>
            <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.82rem' }}>Generated: {status.generated_at}</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 'var(--space-4)' }}>
            {status.components.map((comp) => (
              <section key={comp.name} className="surface-panel">
                <div className="surface-panel__content">
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                    <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{comp.label}</h3>
                    <span style={{ padding: '2px 10px', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', fontWeight: 600 }}>{statusLabel(comp.status)}</span>
                  </div>
                  <p style={{ margin: '8px 0 0', color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>{comp.message}</p>
                  {Object.keys(comp.details).length > 0 && (
                    <dl style={{ display: 'grid', gap: 6, margin: '12px 0 0', padding: 12, borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.52)', border: '1px solid rgba(129, 160, 207, 0.12)' }}>
                      {Object.entries(comp.details).map(([key, value]) => (
                        <div key={key}>
                          <dt style={{ color: 'var(--color-text-secondary)', fontSize: '0.75rem', letterSpacing: '0.05em' }}>{key}</dt>
                          <dd style={{ margin: '2px 0 0', fontSize: '0.85rem', fontWeight: 600, overflowWrap: 'anywhere' }}>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</dd>
                        </div>
                      ))}
                    </dl>
                  )}
                </div>
              </section>
            ))}
          </div>
        </>
      )}
    </section>
  )
}
