import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import AdminTabs from '@/components/AdminTabs'
import { request } from '@/api/http'
import JsonBlock from '@/components/admin/JsonBlock'

interface AgentReplay {
  replay_id: string
  run_id: string
  agent_name: string
  agent_version: string
  agent_mode: string
  source: string
  final_status: string
  created_at: string
  payload?: Record<string, unknown>
}

export default function AdminAgentReplaysView() {
  const { t } = useTranslation()
  const [replays, setReplays] = useState<AgentReplay[]>([])
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [selectedReplay, setSelectedReplay] = useState<AgentReplay | null>(null)

  const loadReplays = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      const data = await request<{ items?: AgentReplay[] } | AgentReplay[]>('/api/admin/agent-replays?limit=50')
      setReplays(Array.isArray(data) ? data : (data.items ?? []))
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to load replays')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadReplays() }, [loadReplays])

  function statusClass(status: string): string {
    if (status === 'success') return 'tag tag--positive'
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
      <h2>Agent Replays</h2>
      {errorMessage && <div className="error-banner">{errorMessage}</div>}

      <div className="card">
        <div className="card__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>Replay Snapshots ({replays.length})</span>
          <button className="btn btn--primary btn--sm" onClick={() => loadReplays()}>刷新</button>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Replay ID</th>
              <th>Agent</th>
              <th>Mode</th>
              <th>Status</th>
              <th>Source</th>
              <th>Run ID</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {replays.map(r => (
              <tr key={r.replay_id} onClick={() => setSelectedReplay(r)} style={{ cursor: 'pointer' }}>
                <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{r.replay_id.slice(0, 20)}...</td>
                <td><span className="tag tag--accent">{r.agent_name}</span></td>
                <td>{r.agent_mode}</td>
                <td><span className={statusClass(r.final_status)}>{r.final_status}</span></td>
                <td>{r.source}</td>
                <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{r.run_id?.slice(0, 16)}...</td>
                <td style={{ fontSize: '0.8rem', color: '#8b949e' }}>{r.created_at?.slice(0, 19)}</td>
              </tr>
            ))}
            {replays.length === 0 && (
              <tr><td colSpan={7} style={{ textAlign: 'center', color: '#8b949e' }}>No replays found</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {selectedReplay && (
        <div className="modal-backdrop" onClick={() => setSelectedReplay(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: 800, maxHeight: '80vh', overflow: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ margin: 0 }}>Replay Detail</h3>
              <button className="btn btn--secondary btn--sm" onClick={() => setSelectedReplay(null)}>✕</button>
            </div>
            <div style={{ display: 'grid', gap: 12, marginBottom: 16 }}>
              <div><strong>Replay ID:</strong> {selectedReplay.replay_id}</div>
              <div><strong>Agent:</strong> {selectedReplay.agent_name}</div>
              <div><strong>Version:</strong> {selectedReplay.agent_version}</div>
              <div><strong>Mode:</strong> {selectedReplay.agent_mode}</div>
              <div><strong>Status:</strong> <span className={statusClass(selectedReplay.final_status)}>{selectedReplay.final_status}</span></div>
              <div><strong>Source:</strong> {selectedReplay.source}</div>
              <div><strong>Run ID:</strong> {selectedReplay.run_id}</div>
              <div><strong>Created:</strong> {selectedReplay.created_at}</div>
            </div>
            {selectedReplay.payload && (
              <div>
                <h4>Payload</h4>
                <JsonBlock value={selectedReplay.payload} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
