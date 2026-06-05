import { useState, useEffect, useCallback } from 'react'
import AdminTabs from '@/components/AdminTabs'
import { request } from '@/api/http'

interface AgentTask {
  id: string
  agent_name: string
  status: string
  progress: Record<string, unknown> | null
  result: Record<string, unknown> | null
  error: string | null
  created_at: string | null
  started_at: string | null
  finished_at: string | null
}

export default function AdminHarnessView() {
  const [loading, setLoading] = useState(true)
  const [tasks, setTasks] = useState<AgentTask[]>([])
  const [errorMessage, setErrorMessage] = useState('')

  const loadData = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      const data = await request<AgentTask[] | { items: AgentTask[] }>('/api/agent/tasks?limit=50')
      setTasks(Array.isArray(data) ? data : (data.items ?? []))
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to load tasks')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadData() }, [loadData])

  function statusTag(status: string) {
    const cls = status === 'completed' ? 'tag--positive' : status === 'failed' ? 'tag--negative' : status === 'running' ? 'tag--accent' : ''
    return <span className={`tag ${cls}`}>{status}</span>
  }

  return (
    <section className="page-section">
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease' }}>
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">ADMIN</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-bright)' }}>Harness Console</h2>
              <p className="panel-subtitle">Agent task history and execution logs.</p>
            </div>
            <button className="btn btn--ghost btn--sm" onClick={() => void loadData()}>Refresh</button>
          </div>
          <AdminTabs />
        </div>
      </section>

      {errorMessage && (
        <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(242,92,92,0.2)', background: 'rgba(242,92,92,0.05)', color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
          {errorMessage}
        </div>
      )}

      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.1s both' }}>
        <div className="surface-panel__content">
          <p className="eyebrow">AGENT TASKS ({tasks.length})</p>
          {loading ? (
            <p style={{ color: 'var(--color-text-muted)', marginTop: 12 }}>Loading...</p>
          ) : tasks.length === 0 ? (
            <p style={{ color: 'var(--color-text-muted)', marginTop: 12 }}>No agent tasks found. Run an agent from the AI Decision, AI Review, or Risk Assessment pages.</p>
          ) : (
            <div className="table-shell" style={{ marginTop: 12 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Agent</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Finished</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.map((t) => (
                    <tr key={t.id}>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>{t.id.slice(0, 8)}...</td>
                      <td style={{ fontWeight: 600 }}>{t.agent_name}</td>
                      <td>{statusTag(t.status)}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--color-text-secondary)' }}>{t.created_at ? new Date(t.created_at).toLocaleString() : '--'}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--color-text-secondary)' }}>{t.finished_at ? new Date(t.finished_at).toLocaleString() : '--'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </section>
  )
}
