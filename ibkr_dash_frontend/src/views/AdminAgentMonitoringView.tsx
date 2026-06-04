import { useState, useEffect, useCallback, useRef } from 'react'
import AdminTabs from '@/components/AdminTabs'

interface MonitoringEvent {
  id: string
  timestamp: string
  level: 'info' | 'warn' | 'error'
  source: string
  message: string
  details?: Record<string, unknown>
}

interface ToolMetric {
  tool: string
  calls: number
  successes: number
  failures: number
  avgLatencyMs: number
}

interface LLMMetric {
  model: string
  calls: number
  totalTokens: number
  avgLatencyMs: number
  errors: number
}

export default function AdminAgentMonitoringView() {
  const [events, setEvents] = useState<MonitoringEvent[]>([])
  const [toolMetrics, setToolMetrics] = useState<ToolMetric[]>([])
  const [llmMetrics, setLlmMetrics] = useState<LLMMetric[]>([])
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const timerRef = useRef<number | undefined>(undefined)

  const loadData = useCallback(async () => {
    try {
      const response = await fetch('/api/admin/agent-monitoring/overview', { credentials: 'include' })
      if (response.ok) {
        const data = await response.json()
        setEvents(data.recent_events ?? [])
        setToolMetrics(data.tool_metrics ?? [])
        setLlmMetrics(data.llm_metrics ?? [])
      }
    } catch {
      // Silently handle - monitoring may not be available
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadData()
  }, [loadData])

  useEffect(() => {
    if (autoRefresh) {
      timerRef.current = window.setInterval(() => { void loadData() }, 10000)
    }
    return () => { if (timerRef.current) window.clearInterval(timerRef.current) }
  }, [autoRefresh, loadData])

  return (
    <section className="page-section">
      <section className="surface-panel">
        <div className="surface-panel__content">
          <div className="section-header">
            <div>
              <p className="eyebrow">ADMIN</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem' }}>Agent Monitoring</h2>
              <p className="panel-subtitle">Monitor LLM calls, IBKR tools, Longbridge MCP tools, and runtime failures.</p>
            </div>
            <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, color: 'var(--color-text-secondary)' }}>
              <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} style={{ accentColor: 'var(--color-accent)' }} />
              <span>Auto-refresh</span>
            </label>
          </div>
          <AdminTabs />
        </div>
      </section>

      {loading ? (
        <section className="surface-panel"><div className="surface-panel__content"><div className="empty-state">Loading monitoring data...</div></div></section>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 'var(--space-4)' }}>
            <section className="surface-panel">
              <div className="surface-panel__content">
                <h3 className="panel-title">LLM Metrics</h3>
                {llmMetrics.length > 0 ? (
                  <div className="table-shell" style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr>{['Model', 'Calls', 'Tokens', 'Avg Latency', 'Errors'].map((h) => <th key={h} style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)', textAlign: 'left', color: 'var(--color-text-secondary)', fontSize: '0.82rem', fontWeight: 700 }}>{h}</th>)}</tr>
                      </thead>
                      <tbody>
                        {llmMetrics.map((m) => (
                          <tr key={m.model}>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{m.model}</td>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{m.calls}</td>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{m.totalTokens.toLocaleString()}</td>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{Math.round(m.avgLatencyMs)}ms</td>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)', color: m.errors > 0 ? 'var(--color-negative)' : undefined }}>{m.errors}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : <div className="empty-state">No LLM metrics available</div>}
              </div>
            </section>

            <section className="surface-panel">
              <div className="surface-panel__content">
                <h3 className="panel-title">Tool Metrics</h3>
                {toolMetrics.length > 0 ? (
                  <div className="table-shell" style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr>{['Tool', 'Calls', 'Success', 'Failed', 'Avg Latency'].map((h) => <th key={h} style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)', textAlign: 'left', color: 'var(--color-text-secondary)', fontSize: '0.82rem', fontWeight: 700 }}>{h}</th>)}</tr>
                      </thead>
                      <tbody>
                        {toolMetrics.map((t) => (
                          <tr key={t.tool}>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{t.tool}</td>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{t.calls}</td>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)', color: 'var(--color-positive)' }}>{t.successes}</td>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)', color: t.failures > 0 ? 'var(--color-negative)' : undefined }}>{t.failures}</td>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{Math.round(t.avgLatencyMs)}ms</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : <div className="empty-state">No tool metrics available</div>}
              </div>
            </section>
          </div>

          <section className="surface-panel">
            <div className="surface-panel__content">
              <h3 className="panel-title">Recent Events</h3>
              {events.length > 0 ? (
                <div style={{ display: 'grid', gap: 8 }}>
                  {events.map((ev) => (
                    <div key={ev.id} style={{ display: 'grid', gridTemplateColumns: '120px 100px 120px 1fr', gap: 12, alignItems: 'center', padding: '10px 12px', borderRadius: 'var(--radius-sm)', background: ev.level === 'error' ? 'rgba(255, 107, 122, 0.06)' : ev.level === 'warn' ? 'rgba(255, 180, 84, 0.06)' : 'rgba(129, 160, 207, 0.04)', fontSize: '0.86rem' }}>
                      <span style={{ color: 'var(--color-text-secondary)', fontFamily: 'monospace', fontSize: '0.78rem' }}>{ev.timestamp.slice(0, 19).replace('T', ' ')}</span>
                      <span style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', fontWeight: 600, background: ev.level === 'error' ? 'rgba(255, 107, 122, 0.15)' : ev.level === 'warn' ? 'rgba(255, 180, 84, 0.15)' : 'rgba(86, 213, 255, 0.15)', color: ev.level === 'error' ? 'var(--color-negative)' : ev.level === 'warn' ? '#ffb454' : 'var(--color-accent)', textAlign: 'center' }}>{ev.level.toUpperCase()}</span>
                      <span style={{ fontWeight: 600 }}>{ev.source}</span>
                      <span style={{ color: 'var(--color-text-secondary)' }}>{ev.message}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state">No recent monitoring events</div>
              )}
            </div>
          </section>
        </>
      )}
    </section>
  )
}
