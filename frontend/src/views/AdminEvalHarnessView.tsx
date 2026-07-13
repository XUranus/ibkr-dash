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

  function severityClass(severity: string): string {
    if (severity === 'critical') return 'tag tag--negative'
    if (severity === 'high') return 'tag tag--warning'
    if (severity === 'medium') return 'tag tag--accent'
    return 'tag tag--neutral'
  }

  function statusClass(status: string): string {
    if (status === 'success' || status === 'completed') return 'tag tag--positive'
    if (status === 'failed' || status === 'error') return 'tag tag--negative'
    if (status === 'running') return 'tag tag--accent'
    return 'tag tag--neutral'
  }

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 40, color: '#adc0df' }}>Loading...</div>
  }

  return (
    <div className="view-container">
      <AdminTabs />
      <h2>Agent Eval Harness</h2>
      {errorMessage && <div className="error-banner">{errorMessage}</div>}

      <div className="tab-bar" style={{ marginBottom: 16 }}>
        <button className={`tab-btn ${activeTab === 'cases' ? 'tab-btn--active' : ''}`} onClick={() => setActiveTab('cases')}>
          Eval Cases ({cases.length})
        </button>
        <button className={`tab-btn ${activeTab === 'runs' ? 'tab-btn--active' : ''}`} onClick={() => setActiveTab('runs')}>
          Eval Runs ({runs.length})
        </button>
      </div>

      {activeTab === 'cases' && (
        <div className="card">
          <div className="card__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Eval Cases</span>
            <button className="btn btn--primary btn--sm" onClick={() => loadCases()}>刷新</button>
          </div>
          <table className="table">
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
                  <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{c.case_id.slice(0, 20)}...</td>
                  <td><span className="tag tag--accent">{c.agent_name}</span></td>
                  <td>{c.title}</td>
                  <td><span className={severityClass(c.severity)}>{c.severity}</span></td>
                  <td>{c.eval_scope}</td>
                  <td>{c.source}</td>
                  <td>{c.enabled ? '✅' : '❌'}</td>
                  <td style={{ fontSize: '0.8rem', color: '#8b949e' }}>{c.created_at?.slice(0, 10)}</td>
                </tr>
              ))}
              {cases.length === 0 && (
                <tr><td colSpan={8} style={{ textAlign: 'center', color: '#8b949e' }}>No eval cases found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'runs' && (
        <div className="card">
          <div className="card__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Eval Runs</span>
            <button className="btn btn--primary btn--sm" onClick={() => loadRuns()}>刷新</button>
          </div>
          <table className="table">
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
                  <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{r.eval_run_id.slice(0, 20)}...</td>
                  <td>{r.name}</td>
                  <td><span className="tag tag--accent">{r.agent_name}</span></td>
                  <td><span className={statusClass(r.status)}>{r.status}</span></td>
                  <td style={{ fontSize: '0.8rem' }}>{r.started_at?.slice(0, 19)}</td>
                  <td style={{ fontSize: '0.8rem' }}>{r.finished_at?.slice(0, 19) || '-'}</td>
                </tr>
              ))}
              {runs.length === 0 && (
                <tr><td colSpan={6} style={{ textAlign: 'center', color: '#8b949e' }}>No eval runs found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {selectedCase && (
        <div className="modal-backdrop" onClick={() => setSelectedCase(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: 700, maxHeight: '80vh', overflow: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ margin: 0 }}>Eval Case Detail</h3>
              <button className="btn btn--secondary btn--sm" onClick={() => setSelectedCase(null)}>✕</button>
            </div>
            <div style={{ display: 'grid', gap: 12 }}>
              <div><strong>Case ID:</strong> {selectedCase.case_id}</div>
              <div><strong>Agent:</strong> {selectedCase.agent_name}</div>
              <div><strong>Title:</strong> {selectedCase.title}</div>
              <div><strong>Description:</strong> {selectedCase.description || '-'}</div>
              <div><strong>Severity:</strong> <span className={severityClass(selectedCase.severity)}>{selectedCase.severity}</span></div>
              <div><strong>Category:</strong> {selectedCase.category || '-'}</div>
              <div><strong>Scope:</strong> {selectedCase.eval_scope}</div>
              <div><strong>Source:</strong> {selectedCase.source}</div>
              <div><strong>Tags:</strong> {selectedCase.tags?.join(', ') || '-'}</div>
              <div><strong>Enabled:</strong> {selectedCase.enabled ? 'Yes' : 'No'}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
