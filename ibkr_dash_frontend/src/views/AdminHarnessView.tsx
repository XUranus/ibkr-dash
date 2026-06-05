import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
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
  const { t } = useTranslation()
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
      setErrorMessage(err instanceof Error ? err.message : t('adminHarness.failedToLoad'))
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
              <p className="eyebrow">{t('adminHarness.adminLabel')}</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-bright)' }}>{t('adminHarness.title')}</h2>
              <p className="panel-subtitle">{t('adminHarness.subtitle')}</p>
            </div>
            <button className="btn btn--ghost btn--sm" onClick={() => void loadData()}>{t('adminHarness.refresh')}</button>
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
          <p className="eyebrow">{t('adminHarness.agentTasks')} ({tasks.length})</p>
          {loading ? (
            <p style={{ color: 'var(--color-text-muted)', marginTop: 12 }}>{t('common.loading')}</p>
          ) : tasks.length === 0 ? (
            <p style={{ color: 'var(--color-text-muted)', marginTop: 12 }}>{t('adminHarness.noTasks')}</p>
          ) : (
            <div className="table-shell" style={{ marginTop: 12 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>{t('adminHarness.id')}</th>
                    <th>{t('adminHarness.agent')}</th>
                    <th>{t('adminHarness.status')}</th>
                    <th>{t('adminHarness.created')}</th>
                    <th>{t('adminHarness.finished')}</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.map((task) => (
                    <tr key={task.id}>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>{task.id.slice(0, 8)}...</td>
                      <td style={{ fontWeight: 600 }}>{task.agent_name}</td>
                      <td>{statusTag(task.status)}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--color-text-secondary)' }}>{task.created_at ? new Date(task.created_at).toLocaleString() : '--'}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--color-text-secondary)' }}>{task.finished_at ? new Date(task.finished_at).toLocaleString() : '--'}</td>
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
