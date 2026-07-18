import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import AdminTabs from '@/components/AdminTabs'
import { request } from '@/api/http'
import JsonBlock from '@/components/admin/JsonBlock'

interface EvalCase {
  case_id: string
  agent_name: string
  title: string
  description: string
  tags: string[]
  enabled: boolean
  severity: string
  category: string
  eval_scope: string
  source: string
  created_at: string
}

interface EvalRun {
  eval_run_id: string
  name: string
  agent_name: string
  status: string
  started_at: string
  finished_at: string
  summary: Record<string, unknown>
  results: unknown[]
}

export default function AdminEvalHarnessView() {
  const { t } = useTranslation()
  const [cases, setCases] = useState<EvalCase[]>([])
  const [runs, setRuns] = useState<EvalRun[]>([])
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [activeTab, setActiveTab] = useState<'cases' | 'runs'>('cases')
  const [selectedCase, setSelectedCase] = useState<EvalCase | null>(null)

  const loadCases = useCallback(async () => {
    try {
      const data = await request<{ items?: EvalCase[] } | EvalCase[]>('/api/admin/agent-eval/cases?limit=100')
      setCases(Array.isArray(data) ? data : (data.items ?? []))
    } catch (err) {
      console.error('Failed to load eval cases:', err)
    }
  }, [])

  const loadRuns = useCallback(async () => {
    try {
      const data = await request<{ items?: EvalRun[] } | EvalRun[]>('/api/admin/agent-eval/runs?limit=50')
      setRuns(Array.isArray(data) ? data : (data.items ?? []))
    } catch (err) {
      console.error('Failed to load eval runs:', err)
    }
  }, [])

  const loadData = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      await Promise.all([loadCases(), loadRuns()])
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [loadCases, loadRuns])

  useEffect(() => { void loadData() }, [loadData])

  function severityTag(severity: string) {
    if (severity === 'critical') return 'tag tag--negative'
    if (severity === 'high') return 'tag tag--warning'
    if (severity === 'medium') return 'tag tag--accent'
    return 'tag tag--neutral'
  }

  function statusTag(status: string) {
    if (status === 'success' || status === 'completed') return 'tag tag--positive'
    if (status === 'failed' || status === 'error') return 'tag tag--negative'
    if (status === 'running') return 'tag tag--accent'
    return 'tag tag--neutral'
  }

  return (
    <section className="page-section">
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease' }}>
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">{t('adminSystem.adminLabel')}</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-bright)' }}>Eval Harness</h2>
            </div>
          </div>
          <AdminTabs />
        </div>
      </section>

      {errorMessage && (
        <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(242,92,92,0.2)', background: 'rgba(242,92,92,0.05)', color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
          {errorMessage}
        </div>
      )}

      {/* Sub-tabs */}
      <div style={{ display: 'flex', gap: 4 }}>
        <button
          className={`btn ${activeTab === 'cases' ? 'btn--accent' : ''}`}
          onClick={() => setActiveTab('cases')}
        >
          Eval Cases ({cases.length})
        </button>
        <button
          className={`btn ${activeTab === 'runs' ? 'btn--accent' : ''}`}
          onClick={() => setActiveTab('runs')}
        >
          Eval Runs ({runs.length})
        </button>
      </div>

      {loading ? (
        <section className="surface-panel"><div className="surface-panel__content"><p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>{t('common.loading')}</p></div></section>
      ) : activeTab === 'cases' ? (
        <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.1s both' }}>
          <div className="surface-panel__content">
            <div className="section-header">
              <h3 style={{ margin: 0, fontSize: '0.95rem', color: 'var(--color-text-bright)' }}>Eval Cases</h3>
              <button className="btn btn--accent btn--sm" onClick={() => loadCases()}>
                {t('common.refresh', { defaultValue: 'Refresh' })}
              </button>
            </div>

            {cases.length === 0 ? (
              <div className="empty-state">No eval cases found</div>
            ) : (
              <div className="table-shell">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Case ID</th>
                      <th>Agent</th>
                      <th>Title</th>
                      <th>Severity</th>
                      <th>Scope</th>
                      <th>Source</th>
                      <th>Enabled</th>
                      <th>Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cases.map(c => (
                      <tr key={c.case_id} onClick={() => setSelectedCase(c)} style={{ cursor: 'pointer' }}>
                        <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>{c.case_id.slice(0, 20)}...</td>
                        <td><span className="tag tag--accent">{c.agent_name}</span></td>
                        <td>{c.title}</td>
                        <td><span className={severityTag(c.severity)}>{c.severity}</span></td>
                        <td>{c.eval_scope}</td>
                        <td>{c.source}</td>
                        <td>{c.enabled ? '✅' : '❌'}</td>
                        <td style={{ fontSize: '0.82rem', color: 'var(--color-text-secondary)' }}>{c.created_at?.slice(0, 10)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      ) : (
        <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.1s both' }}>
          <div className="surface-panel__content">
            <div className="section-header">
              <h3 style={{ margin: 0, fontSize: '0.95rem', color: 'var(--color-text-bright)' }}>Eval Runs</h3>
              <button className="btn btn--accent btn--sm" onClick={() => loadRuns()}>
                {t('common.refresh', { defaultValue: 'Refresh' })}
              </button>
            </div>

            {runs.length === 0 ? (
              <div className="empty-state">No eval runs found</div>
            ) : (
              <div className="table-shell">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Run ID</th>
                      <th>Name</th>
                      <th>Agent</th>
                      <th>Status</th>
                      <th>Started</th>
                      <th>Finished</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.map(r => (
                      <tr key={r.eval_run_id}>
                        <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>{r.eval_run_id.slice(0, 20)}...</td>
                        <td>{r.name}</td>
                        <td><span className="tag tag--accent">{r.agent_name}</span></td>
                        <td><span className={statusTag(r.status)}>{r.status}</span></td>
                        <td style={{ fontSize: '0.82rem' }}>{r.started_at?.slice(0, 19)}</td>
                        <td style={{ fontSize: '0.82rem' }}>{r.finished_at?.slice(0, 19) || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      )}

      {selectedCase && (
        <div className="modal-backdrop" onClick={() => setSelectedCase(null)}>
          <div className="modal-dialog" onClick={e => e.stopPropagation()} style={{ maxWidth: 700, maxHeight: '80vh', overflow: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--color-text-bright)' }}>Eval Case Detail</h3>
              <button className="btn btn--ghost btn--sm" onClick={() => setSelectedCase(null)}>✕</button>
            </div>
            <div style={{ display: 'grid', gap: 8, fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
              <div><span style={{ color: 'var(--color-text-muted)' }}>Case ID:</span> {selectedCase.case_id}</div>
              <div><span style={{ color: 'var(--color-text-muted)' }}>Agent:</span> {selectedCase.agent_name}</div>
              <div><span style={{ color: 'var(--color-text-muted)' }}>Title:</span> {selectedCase.title}</div>
              <div><span style={{ color: 'var(--color-text-muted)' }}>Description:</span> {selectedCase.description || '-'}</div>
              <div><span style={{ color: 'var(--color-text-muted)' }}>Severity:</span> <span className={severityTag(selectedCase.severity)}>{selectedCase.severity}</span></div>
              <div><span style={{ color: 'var(--color-text-muted)' }}>Category:</span> {selectedCase.category || '-'}</div>
              <div><span style={{ color: 'var(--color-text-muted)' }}>Scope:</span> {selectedCase.eval_scope}</div>
              <div><span style={{ color: 'var(--color-text-muted)' }}>Source:</span> {selectedCase.source}</div>
              <div><span style={{ color: 'var(--color-text-muted)' }}>Tags:</span> {selectedCase.tags?.join(', ') || '-'}</div>
              <div><span style={{ color: 'var(--color-text-muted)' }}>Enabled:</span> {selectedCase.enabled ? 'Yes' : 'No'}</div>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
