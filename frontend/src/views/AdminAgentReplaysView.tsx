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

  function statusTag(status: string) {
    if (status === 'success') return 'tag tag--positive'
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
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-bright)' }}>Agent Replays</h2>
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

      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.1s both' }}>
        <div className="surface-panel__content">
          <div className="section-header">
            <h3 style={{ margin: 0, fontSize: '0.95rem', color: 'var(--color-text-bright)' }}>
              Replay Snapshots ({replays.length})
            </h3>
            <button className="btn btn--accent btn--sm" onClick={() => loadReplays()}>
              {t('common.refresh', { defaultValue: 'Refresh' })}
            </button>
          </div>

          {loading ? (
            <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>{t('common.loading')}</p>
          ) : replays.length === 0 ? (
            <div className="empty-state">No replays found</div>
          ) : (
            <div className="table-shell">
              <table className="data-table">
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
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>{r.replay_id.length > 20 ? r.replay_id.slice(0, 20) + '...' : r.replay_id}</td>
                      <td><span className="tag tag--accent">{r.agent_name}</span></td>
                      <td>{r.agent_mode}</td>
                      <td><span className={statusTag(r.final_status)}>{r.final_status}</span></td>
                      <td>{r.source}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>{r.run_id ? (r.run_id.length > 16 ? r.run_id.slice(0, 16) + '...' : r.run_id) : '-'}</td>
                      <td style={{ fontSize: '0.82rem', color: 'var(--color-text-secondary)' }}>{r.created_at?.slice(0, 19)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      {selectedReplay && (
        <div className="modal-backdrop" onClick={() => setSelectedReplay(null)}>
          <div className="modal-dialog" onClick={e => e.stopPropagation()} style={{ maxWidth: 800, maxHeight: '80vh', overflow: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--color-text-bright)' }}>Replay Detail</h3>
              <button className="btn btn--ghost btn--sm" onClick={() => setSelectedReplay(null)}>✕</button>
            </div>
            <div style={{ display: 'grid', gap: 8, marginBottom: 16, fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
              <div><span style={{ color: 'var(--color-text-muted)' }}>Replay ID:</span> {selectedReplay.replay_id}</div>
              <div><span style={{ color: 'var(--color-text-muted)' }}>Agent:</span> {selectedReplay.agent_name}</div>
              <div><span style={{ color: 'var(--color-text-muted)' }}>Version:</span> {selectedReplay.agent_version}</div>
              <div><span style={{ color: 'var(--color-text-muted)' }}>Mode:</span> {selectedReplay.agent_mode}</div>
              <div><span style={{ color: 'var(--color-text-muted)' }}>Status:</span> <span className={statusTag(selectedReplay.final_status)}>{selectedReplay.final_status}</span></div>
              <div><span style={{ color: 'var(--color-text-muted)' }}>Source:</span> {selectedReplay.source}</div>
              <div><span style={{ color: 'var(--color-text-muted)' }}>Run ID:</span> {selectedReplay.run_id}</div>
              <div><span style={{ color: 'var(--color-text-muted)' }}>Created:</span> {selectedReplay.created_at}</div>
            </div>
            {selectedReplay.payload && (
              <div>
                <h4 style={{ margin: '0 0 8px', fontSize: '0.9rem', color: 'var(--color-text-bright)' }}>Payload</h4>
                <JsonBlock value={selectedReplay.payload} />
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
