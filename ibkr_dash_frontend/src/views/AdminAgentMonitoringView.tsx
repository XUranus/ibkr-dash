import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
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
  promptTokens: number
  completionTokens: number
  avgLatencyMs: number
  errors: number
}

const PAGE_SIZE = 20

export default function AdminAgentMonitoringView() {
  const { t } = useTranslation()
  const [events, setEvents] = useState<MonitoringEvent[]>([])
  const [toolMetrics, setToolMetrics] = useState<ToolMetric[]>([])
  const [llmMetrics, setLlmMetrics] = useState<LLMMetric[]>([])
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const timerRef = useRef<number | undefined>(undefined)
  const [eventPage, setEventPage] = useState(0)

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
              <p className="eyebrow">{t('adminMonitoring.adminLabel')}</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem' }}>{t('adminMonitoring.title')}</h2>
              <p className="panel-subtitle">{t('adminMonitoring.subtitle')}</p>
            </div>
            <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, color: 'var(--color-text-secondary)' }}>
              <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} style={{ accentColor: 'var(--color-accent)' }} />
              <span>{t('adminMonitoring.autoRefresh')}</span>
            </label>
          </div>
          <AdminTabs />
        </div>
      </section>

      {loading ? (
        <section className="surface-panel"><div className="surface-panel__content"><div className="empty-state">{t('adminMonitoring.loadingMonitoring')}</div></div></section>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 'var(--space-4)' }}>
            <section className="surface-panel">
              <div className="surface-panel__content">
                <h3 className="panel-title">{t('adminMonitoring.llmMetrics')}</h3>
                {llmMetrics.length > 0 ? (
                  <div className="table-shell" style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr>{[t('adminMonitoring.model'), t('adminMonitoring.calls'), t('adminMonitoring.promptTokens'), t('adminMonitoring.completionTokens'), t('adminMonitoring.tokens'), t('adminMonitoring.avgLatency'), t('adminMonitoring.errors')].map((h) => <th key={h} style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)', textAlign: 'left', color: 'var(--color-text-secondary)', fontSize: '0.82rem', fontWeight: 700 }}>{h}</th>)}</tr>
                      </thead>
                      <tbody>
                        {llmMetrics.map((m) => (
                          <tr key={m.model}>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{m.model}</td>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{m.calls}</td>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{m.promptTokens?.toLocaleString() ?? 0}</td>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{m.completionTokens?.toLocaleString() ?? 0}</td>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{m.totalTokens.toLocaleString()}</td>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{Math.round(m.avgLatencyMs)}ms</td>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)', color: m.errors > 0 ? 'var(--color-negative)' : undefined }}>{m.errors}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : <div className="empty-state">{t('adminMonitoring.noLlmMetrics')}</div>}
              </div>
            </section>

            <section className="surface-panel">
              <div className="surface-panel__content">
                <h3 className="panel-title">{t('adminMonitoring.toolMetrics')}</h3>
                {toolMetrics.length > 0 ? (
                  <div className="table-shell" style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr>{[t('adminMonitoring.tool'), t('adminMonitoring.calls'), t('adminMonitoring.success'), t('adminMonitoring.failed'), t('adminMonitoring.avgLatency')].map((h) => <th key={h} style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)', textAlign: 'left', color: 'var(--color-text-secondary)', fontSize: '0.82rem', fontWeight: 700 }}>{h}</th>)}</tr>
                      </thead>
                      <tbody>
                        {toolMetrics.map((tool) => (
                          <tr key={tool.tool}>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{tool.tool}</td>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{tool.calls}</td>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)', color: 'var(--color-positive)' }}>{tool.successes}</td>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)', color: tool.failures > 0 ? 'var(--color-negative)' : undefined }}>{tool.failures}</td>
                            <td style={{ padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{Math.round(tool.avgLatencyMs)}ms</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : <div className="empty-state">{t('adminMonitoring.noToolMetrics')}</div>}
              </div>
            </section>
          </div>

          <section className="surface-panel">
            <div className="surface-panel__content">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <h3 className="panel-title" style={{ margin: 0 }}>{t('adminMonitoring.recentEvents')}</h3>
                {events.length > PAGE_SIZE && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)' }}>
                    <button className="btn btn--ghost btn--sm" onClick={() => setEventPage((p) => Math.max(0, p - 1))} disabled={eventPage === 0} style={{ padding: '2px 6px', fontSize: '0.7rem' }}>◀</button>
                    <span>{eventPage + 1} / {Math.ceil(events.length / PAGE_SIZE)}</span>
                    <button className="btn btn--ghost btn--sm" onClick={() => setEventPage((p) => Math.min(Math.ceil(events.length / PAGE_SIZE) - 1, p + 1))} disabled={eventPage >= Math.ceil(events.length / PAGE_SIZE) - 1} style={{ padding: '2px 6px', fontSize: '0.7rem' }}>▶</button>
                  </div>
                )}
              </div>
              {events.length > 0 ? (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem', fontFamily: 'var(--font-mono)' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                        <th style={{ textAlign: 'left', padding: '5px 8px', color: 'var(--color-text-muted)', fontSize: '0.72rem', fontWeight: 600 }}>{t('adminMonitoring.table.time')}</th>
                        <th style={{ textAlign: 'center', padding: '5px 8px', color: 'var(--color-text-muted)', fontSize: '0.72rem', fontWeight: 600 }}>{t('adminMonitoring.table.level')}</th>
                        <th style={{ textAlign: 'left', padding: '5px 8px', color: 'var(--color-text-muted)', fontSize: '0.72rem', fontWeight: 600 }}>{t('adminMonitoring.table.source')}</th>
                        <th style={{ textAlign: 'left', padding: '5px 8px', color: 'var(--color-text-muted)', fontSize: '0.72rem', fontWeight: 600 }}>{t('adminMonitoring.table.message')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {events.slice(eventPage * PAGE_SIZE, (eventPage + 1) * PAGE_SIZE).map((ev) => (
                        <tr key={ev.id} style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                          <td style={{ padding: '4px 8px', color: 'var(--color-text-secondary)', fontSize: '0.72rem', whiteSpace: 'nowrap' }}>{ev.timestamp.slice(0, 19).replace('T', ' ')}</td>
                          <td style={{ padding: '4px 8px', textAlign: 'center' }}>
                            <span style={{
                              padding: '1px 6px', borderRadius: 'var(--radius-sm)', fontSize: '0.68rem', fontWeight: 600,
                              background: ev.level === 'error' ? 'rgba(255, 107, 122, 0.15)' : ev.level === 'warn' ? 'rgba(255, 180, 84, 0.15)' : 'rgba(86, 213, 255, 0.15)',
                              color: ev.level === 'error' ? 'var(--color-negative)' : ev.level === 'warn' ? '#ffb454' : 'var(--color-accent)',
                            }}>
                              {t(`adminMonitoring.level.${ev.level}`, { defaultValue: ev.level.toUpperCase() })}
                            </span>
                          </td>
                          <td style={{ padding: '4px 8px', fontWeight: 600, fontSize: '0.75rem' }}>{t(`adminMonitoring.agent.${ev.source}`, { defaultValue: ev.source })}</td>
                          <td style={{ padding: '4px 8px', color: 'var(--color-text-secondary)', fontSize: '0.75rem' }}>{t(`adminMonitoring.status.${ev.message}`, { defaultValue: ev.message })}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="empty-state">{t('adminMonitoring.noRecentEvents')}</div>
              )}
            </div>
          </section>
        </>
      )}
    </section>
  )
}
