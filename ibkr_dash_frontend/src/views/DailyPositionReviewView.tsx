import { useState, useEffect, useCallback, useRef } from 'react'
import AgentEvidencePanel from '@/components/AgentEvidencePanel'
import AgentTaskGraph from '@/components/AgentTaskGraph'
import type { AgentTask } from '@/types/agentTasks'
import type { DailyPositionReviewContext, DailyPositionReviewHealth, DailyPositionReviewPositionItem, DailyPositionReviewResult } from '@/types/dailyPositionReview'
import { fetchDailyPositionReview, fetchDailyPositionReviewContext, fetchDailyPositionReviewDates, fetchDailyPositionReviewHealth, fetchDailyPositionReviewTasks, fetchRecentDailyPositionReviews, startDailyPositionReviewTask } from '@/api/dailyPositionReview'

interface Props { embedded?: boolean }

export default function DailyPositionReviewView({ embedded = false }: Props) {
  const [loading, setLoading] = useState(true)
  const [contextLoading, setContextLoading] = useState(false)
  const [reviewLoading, setReviewLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [dates, setDates] = useState<string[]>([])
  const [selectedDate, setSelectedDate] = useState('')
  const [health, setHealth] = useState<DailyPositionReviewHealth | null>(null)
  const [context, setContext] = useState<DailyPositionReviewContext | null>(null)
  const [review, setReview] = useState<DailyPositionReviewResult | null>(null)
  const [taskItems, setTaskItems] = useState<AgentTask[]>([])
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null)
  const [historyVisible, setHistoryVisible] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyItems, setHistoryItems] = useState<DailyPositionReviewResult[]>([])
  const [now, setNow] = useState(Date.now())
  const timerRef = useRef<number | undefined>(undefined)

  const activeTaskCount = taskItems.filter((t) => t.status === 'queued' || t.status === 'running').length
  const isGenerating = activeTaskCount > 0
  const visibleTasks = [...taskItems.filter((t) => t.status === 'queued' || t.status === 'running'), ...taskItems.filter((t) => t.status === 'completed' || t.status === 'failed').slice(0, 2)]

  function contextFromSavedReview(item: DailyPositionReviewResult): DailyPositionReviewContext | null {
    const stored = (item.display_context || item.deterministic_context) as Partial<DailyPositionReviewContext> | null
    if (!stored?.overview || !stored.rankings || !stored.risk) return null
    const rankings = stored.rankings as Record<string, DailyPositionReviewPositionItem[]>
    return {
      report_date: String(stored.report_date || item.report_date),
      data_sources: (stored.data_sources as Record<string, string>) || item.data_source_summary || {},
      overview: stored.overview as DailyPositionReviewContext['overview'],
      positions: Array.isArray(stored.positions) ? stored.positions : rankings.top_weights ?? [],
      rankings,
      risk: stored.risk as DailyPositionReviewContext['risk'],
      benchmarks: (stored.benchmarks as DailyPositionReviewContext['benchmarks']) || { items: [], beta_alpha_note: 'Read from archive.' },
      focus_symbols: Array.isArray(stored.focus_symbols) ? stored.focus_symbols : [],
      attribution_quality: stored.attribution_quality || {},
      data_quality: stored.data_quality || {},
    }
  }

  function formatNumber(v: number | null | undefined, d = 2): string { if (v == null) return '--'; return new Intl.NumberFormat('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }).format(v) }
  function formatPct(v: number | null | undefined): string { return v == null ? '--' : `${formatNumber(v * 100)}%` }
  function formatRawPct(v: number | null | undefined): string { return v == null ? '--' : `${formatNumber(v)}%` }
  function itemTone(item: DailyPositionReviewPositionItem): string { return (item.daily_pnl ?? 0) >= 0 ? 'metric-positive' : 'metric-negative' }

  function taskElapsed(t: AgentTask): number { const s = Date.parse(t.started_at || t.created_at); const e = t.completed_at ? Date.parse(t.completed_at) : now; return Math.max(0, Math.floor((e - s) / 1000)) }
  function taskStage(t: AgentTask): string { if (t.status === 'completed') return 'Completed'; if (t.status === 'failed') return t.error_message || 'Failed'; const s = taskElapsed(t); if (s < 6) return 'Computing account P&L and position contributions'; if (s < 24) return 'Fetching Longbridge public quotes and events'; if (s < 55) return 'Calling LLM for review report'; return 'Saving report' }

  async function loadSelectedDate(date: string): Promise<void> {
    if (!date) return; setSelectedDate(date); setErrorMessage(''); setContextLoading(true); setReviewLoading(true)
    try {
      const [tasksResp, reviewResp] = await Promise.all([fetchDailyPositionReviewTasks(20), fetchDailyPositionReview(date).catch(() => null)])
      setTaskItems(tasksResp)
      if (reviewResp) { setReview(reviewResp); setReviewLoading(false); const saved = contextFromSavedReview(reviewResp); if (saved) { setContext(saved); setContextLoading(false); return } }
      setReview(reviewResp); setReviewLoading(false); setContext(await fetchDailyPositionReviewContext(date)); setContextLoading(false)
    } catch (error) { setErrorMessage(error instanceof Error ? error.message : 'Load failed'); setContextLoading(false); setReviewLoading(false) }
  }

  async function openHistory(): Promise<void> {
    setHistoryVisible(true); setHistoryLoading(true); setErrorMessage('')
    try { setHistoryItems(await fetchRecentDailyPositionReviews(60)) }
    catch (error) { setErrorMessage(error instanceof Error ? error.message : 'Load history failed') }
    finally { setHistoryLoading(false) }
  }

  async function loadPage(): Promise<void> {
    setLoading(true); setErrorMessage('')
    try {
      const [h, dateItems] = await Promise.all([fetchDailyPositionReviewHealth(), fetchDailyPositionReviewDates(90)])
      setHealth(h); setDates(dateItems)
      if (dateItems[0]) { setSelectedDate(dateItems[0]); void loadSelectedDate(dateItems[0]) }
    } catch (error) { setErrorMessage(error instanceof Error ? error.message : 'Load failed') }
    finally { setLoading(false) }
  }

  async function generateReview(forceRefresh = false): Promise<void> {
    if (!selectedDate) return; setErrorMessage('')
    const optimisticId = `local-daily-review-${selectedDate}-${Date.now()}`
    const optimisticTask: AgentTask = { id: optimisticId, agent: 'daily_position_review', task_type: 'daily_position_review', label: `${selectedDate} Daily Review`, status: 'queued', payload: { report_date: selectedDate }, result_id: null, error_code: null, error_message: null, created_at: new Date().toISOString(), started_at: new Date().toISOString(), completed_at: null, updated_at: new Date().toISOString(), updated_seq: 0, graph_snapshot: null, graph_progress_summary: {}, graph_events: [] }
    setTaskItems((prev) => [optimisticTask, ...prev.filter((t) => t.id !== optimisticId)].slice(0, 20))
    try {
      const task = await startDailyPositionReviewTask(selectedDate, forceRefresh)
      setTaskItems((prev) => [task, ...prev.filter((t) => t.id !== task.id && t.id !== optimisticId)].slice(0, 20))
      await pollTasks()
    } catch (error) {
      setTaskItems((prev) => [{ ...optimisticTask, status: 'failed' as const, error_message: error instanceof Error ? error.message : 'Failed', completed_at: new Date().toISOString() }, ...prev.filter((t) => t.id !== optimisticId)].slice(0, 20))
      setErrorMessage(error instanceof Error ? error.message : 'Generation failed')
    }
  }

  async function pollTasks(): Promise<void> {
    try {
      const tasks = await fetchDailyPositionReviewTasks(20); setTaskItems(tasks)
      const completedForDate = tasks.find((t) => t.status === 'completed' && t.result_id === selectedDate)
      if (completedForDate) { const latestReview = await fetchDailyPositionReview(selectedDate); setReview(latestReview); const saved = contextFromSavedReview(latestReview); if (saved) setContext(saved) }
    } catch { /* keep current state */ }
  }

  async function viewTaskResult(task: AgentTask): Promise<void> {
    if (!task.result_id) return
    const item = await fetchDailyPositionReview(task.result_id); setReview(item)
    const saved = contextFromSavedReview(item); setContext(saved || await fetchDailyPositionReviewContext(item.report_date))
  }

  useEffect(() => {
    timerRef.current = window.setInterval(() => { setNow(Date.now()); if (activeTaskCount) void pollTasks() }, 2000)
    void loadPage()
    return () => { if (timerRef.current) window.clearInterval(timerRef.current) }
  }, [])

  const topContributors = context?.rankings.profit_contributors?.slice(0, 5) ?? []
  const topDrags = context?.rankings.loss_drags?.slice(0, 5) ?? []
  const topWeights = context?.rankings.top_weights?.slice(0, 5) ?? []
  const signedTone = (context?.overview.daily_pnl ?? 0) >= 0 ? 'metric-positive' : 'metric-negative'

  return (
    <section className="page-section">
      <section className="surface-panel"><div className="surface-panel__content">
        <div className="section-header" style={{ alignItems: 'center' }}>
          <div>{embedded ? <><h3 className="panel-title">Daily Review</h3><p className="panel-subtitle">Account P&L attribution, stock movement explanations, risk alerts, and next-day watchlist.</p></> : <><p className="eyebrow">DAILY POSITION REVIEW</p><h2 style={{ margin: 0, fontSize: '1.55rem' }}>Daily Position Review</h2><p className="panel-subtitle">Account P&L attribution, individual stock movement explanations, risk alerts, and next-day watchlist.</p></>}</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, justifyContent: 'flex-end', alignItems: 'center' }}>
            <span style={{ padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', fontWeight: 600, background: health?.llm_configured ? 'rgba(52, 210, 163, 0.15)' : 'rgba(255, 107, 122, 0.15)', color: health?.llm_configured ? 'var(--color-positive)' : 'var(--color-negative)' }}>{health?.llm_configured ? 'LLM READY' : 'LLM MISSING'}</span>
            <select className="input" style={{ width: 180 }} value={selectedDate} onChange={(e) => { setSelectedDate(e.target.value); void loadSelectedDate(e.target.value) }}>
              {dates.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
            <button className="btn btn--ghost" onClick={() => void openHistory()}>History</button>
            <button className="btn btn--accent" disabled={isGenerating || !selectedDate} onClick={() => void generateReview(Boolean(review))}>{isGenerating ? 'Generating...' : review ? 'Regenerate' : 'Generate'}</button>
          </div>
        </div>
      </div></section>

      {loading ? <section className="surface-panel"><div className="surface-panel__content"><div className="empty-state">Loading...</div></div></section> : (
        <>
          {errorMessage && <p style={{ margin: 0, padding: '12px 16px', borderRadius: 'var(--radius-md)', color: 'var(--color-negative)', background: 'rgba(55, 18, 28, 0.48)', border: '1px solid rgba(255, 107, 122, 0.18)' }}>{errorMessage}</p>}

          {(contextLoading || reviewLoading) && <section className="surface-panel"><div className="surface-panel__content"><div className="empty-state">{contextLoading ? 'Loading position context...' : 'Loading review report...'}</div></div></section>}

          {context && <>
            {visibleTasks.length > 0 && (
              <section className="surface-panel"><div className="surface-panel__content">
                <h3 className="panel-title">Background Tasks</h3>
                <p className="panel-subtitle">Report auto-refreshes when generation completes.</p>
                <div style={{ display: 'grid', gap: 10 }}>
                  {visibleTasks.map((task) => (
                    <div key={task.id} style={{ padding: '12px 14px', border: '1px solid rgba(129, 160, 207, 0.14)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.48)' }}>
                      <button type="button" style={{ display: 'grid', gridTemplateColumns: '12px minmax(0, 1fr) auto', gap: 12, alignItems: 'center', width: '100%', padding: 0, border: 0, background: 'transparent', color: 'var(--color-text-primary)', cursor: 'pointer', textAlign: 'left' }} onClick={() => setExpandedTaskId(expandedTaskId === task.id ? null : task.id)}>
                        <span style={{ width: 10, height: 10, borderRadius: 999, background: task.status === 'completed' ? 'var(--color-positive)' : task.status === 'failed' ? 'var(--color-negative)' : 'var(--color-accent)', animation: task.status === 'queued' || task.status === 'running' ? 'runner-pulse 1.2s ease-in-out infinite' : undefined }} />
                        <div style={{ display: 'grid', gap: 4 }}><strong>{task.label}</strong><span style={{ color: 'var(--color-text-secondary)' }}>{taskStage(task)}</span></div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <span style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', fontWeight: 600 }}>{task.status.toUpperCase()}</span>
                          <span style={{ color: 'var(--color-text-secondary)' }}>{taskElapsed(task)}s</span>
                          <span>{expandedTaskId === task.id ? '▲' : '▼'}</span>
                        </div>
                      </button>
                      {expandedTaskId === task.id && !task.id.startsWith('local-') && <AgentTaskGraph task={task} expanded onSnapshot={() => {}} />}
                      {expandedTaskId === task.id && task.result_id && (
                        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 10 }}>
                          <button className="btn btn--ghost btn--sm" onClick={() => void viewTaskResult(task)}>View Report</button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div></section>
            )}

            {historyVisible && (
              <section className="surface-panel"><div className="surface-panel__content">
                <div className="section-header">
                  <div><h3 className="panel-title">Review History</h3><p className="panel-subtitle">Browse archived daily reviews by date.</p></div>
                  <button className="btn btn--ghost" onClick={() => setHistoryVisible(false)}>X</button>
                </div>
                {historyLoading ? <div className="empty-state">Loading...</div> : historyItems.length > 0 ? (
                  <div style={{ display: 'grid', gap: 10 }}>
                    {historyItems.map((item) => (
                      <button key={item.id} style={{ display: 'grid', gridTemplateColumns: '18px minmax(0, 1fr) auto', gap: 12, alignItems: 'center', width: '100%', padding: '12px 14px', border: `1px solid ${item.report_date === selectedDate ? 'rgba(87, 182, 255, 0.45)' : 'rgba(129, 160, 207, 0.12)'}`, borderRadius: 'var(--radius-md)', background: item.report_date === selectedDate ? 'rgba(87, 182, 255, 0.1)' : 'rgba(10, 18, 32, 0.58)', color: 'var(--color-text-primary)', cursor: 'pointer', textAlign: 'left' }} onClick={() => { setHistoryVisible(false); void loadSelectedDate(item.report_date) }}>
                        <span style={{ width: 14, height: 14, border: `1px solid ${item.report_date === selectedDate ? 'transparent' : 'rgba(171, 198, 235, 0.6)'}`, borderRadius: 999, background: item.report_date === selectedDate ? 'var(--color-accent)' : undefined }} />
                        <span style={{ display: 'grid', gap: 4 }}><strong>{item.report_date}</strong><small style={{ color: 'var(--color-text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.summary}</small></span>
                        <span style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', fontWeight: 600 }}>{item.report_date === selectedDate ? 'Current' : 'View'}</span>
                      </button>
                    ))}
                  </div>
                ) : <div className="empty-state">No history reviews available.</div>}
              </div></section>
            )}

            {/* Overview cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.6fr) repeat(3, minmax(160px, 0.7fr))', gap: 'var(--space-4)' }}>
              <article className="surface-panel" style={{ padding: 16 }}>
                <p className="eyebrow">{context.overview.report_date}</p>
                <h3 className={signedTone} style={{ margin: 0, fontSize: '2.4rem' }}>{formatNumber(context.overview.daily_pnl)}</h3>
                <p style={{ margin: '8px 0 0', color: 'var(--color-text-secondary)' }}>{context.overview.summary}</p>
              </article>
              {[['Daily Return', formatRawPct(context.overview.daily_return_percent), signedTone], ['Total Equity', formatNumber(context.overview.total_equity), ''], ['Cash Ratio', formatPct(context.overview.cash_ratio), '']].map(([label, value, tone]) => (
                <article key={label} className="surface-panel" style={{ padding: 16 }}>
                  <span style={{ color: 'var(--color-text-secondary)' }}>{label}</span>
                  <strong className={tone as string} style={{ display: 'block', marginTop: 8, fontSize: '1.55rem' }}>{value}</strong>
                </article>
              ))}
            </div>

            {/* LLM Report */}
            <section className="surface-panel"><div className="surface-panel__content">
              <h3 className="panel-title">LLM Review Report</h3>
              <p className="panel-subtitle">LLM only explains and attributes; deterministic numbers come from backend calculation.</p>
              {review ? (
                <div style={{ display: 'grid', gap: 'var(--space-3)' }}>
                  {[['Account Conclusion', review.account_conclusion], ['P&L Attribution', review.attribution_summary], ['Market Context', review.market_context], ['Risk Changes', review.risk_analysis], ['Operation Observations', review.operation_observation]].map(([title, content]) => (
                    <article key={title} style={{ padding: 14, border: '1px solid rgba(129, 160, 207, 0.12)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.58)' }}>
                      <h4 style={{ margin: 0 }}>{title}</h4>
                      <p style={{ margin: 0, color: 'var(--color-text-secondary)', lineHeight: 1.7 }}>{content}</p>
                    </article>
                  ))}
                  <article style={{ padding: 14, border: '1px solid rgba(129, 160, 207, 0.12)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.58)' }}>
                    <h4 style={{ margin: 0 }}>Tomorrow Watchlist</h4>
                    <ul style={{ margin: '12px 0 0', paddingLeft: 18, color: 'var(--color-text-secondary)', lineHeight: 1.7 }}>
                      {review.tomorrow_watchlist.map((item, i) => {
                        const rec = item as Record<string, unknown>
                        return <li key={i}><strong>{String(rec.symbol || 'Watch')}</strong> {String(rec.reason || '')} {String(rec.conditions || '')}</li>
                      })}
                    </ul>
                  </article>
                </div>
              ) : <div className="empty-state">No LLM review report generated for this date.</div>}
            </div></section>

            {review && <AgentEvidencePanel metadata={review.metadata} evidenceSummary={review.evidence_summary} runTraceSummary={review.run_trace_summary} />}

            {/* Rankings */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 'var(--space-4)' }}>
              {[['Top Contributors', topContributors], ['Top Drags', topDrags]].map(([title, items]) => (
                <section key={title} className="surface-panel"><div className="surface-panel__content">
                  <h3 className="panel-title">{title}</h3>
                  <p className="panel-subtitle">{title === 'Top Contributors' ? 'Ranked by actual contribution to daily P&L.' : 'Position impact prioritized over pure price change.'}</p>
                  <div style={{ display: 'grid', gap: 10 }}>
                    {(items as DailyPositionReviewPositionItem[]).map((item) => (
                      <div key={item.symbol} style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 12, padding: 14, border: '1px solid rgba(129, 160, 207, 0.12)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.58)' }}>
                        <div style={{ display: 'grid', gap: 4 }}><strong>{item.symbol}</strong><span style={{ color: 'var(--color-text-secondary)' }}>{item.name ?? item.normalized_symbol}</span></div>
                        <div style={{ textAlign: 'right', display: 'grid', gap: 4 }}><strong className={itemTone(item)}>{formatNumber(item.daily_pnl)}</strong><span style={{ color: 'var(--color-text-secondary)' }}>{formatPct(item.contribution_ratio)} / {formatRawPct(item.daily_change_percent)}</span></div>
                      </div>
                    ))}
                  </div>
                </div></section>
              ))}
            </div>

            {/* Risk and Benchmarks */}
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(320px, 0.8fr)', gap: 'var(--space-4)' }}>
              <section className="surface-panel"><div className="surface-panel__content">
                <h3 className="panel-title">Position Risk</h3>
                <p className="panel-subtitle">Account is {context.risk.account_posture ?? 'unknown'}. Max 5% position drop impacts ~{formatRawPct(context.risk.max_position_down_5pct_account_impact_percent)} of account.</p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 'var(--space-3)' }}>
                  {[['Max Single', formatPct(context.risk.max_single_position_weight)], ['Top 3', formatPct(context.risk.top3_weight)], ['Top 5', formatPct(context.risk.top5_weight)], ['Semi/AI/Tech', formatPct(context.risk.semiconductor_ai_tech_weight)]].map(([k, v]) => (
                    <div key={k} style={{ display: 'grid', gap: 6, padding: 14, border: '1px solid rgba(129, 160, 207, 0.12)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.58)' }}><span style={{ color: 'var(--color-text-secondary)' }}>{k}</span><strong>{v}</strong></div>
                  ))}
                </div>
                <ul style={{ margin: '12px 0 0', paddingLeft: 18, color: 'var(--color-text-secondary)' }}>
                  {context.risk.risk_flags.length > 0 ? context.risk.risk_flags.map((f, i) => <li key={i}>{f}</li>) : <li>No concentration alerts.</li>}
                </ul>
              </div></section>

              <section className="surface-panel"><div className="surface-panel__content">
                <h3 className="panel-title">Benchmark Comparison</h3>
                <p className="panel-subtitle">{context.benchmarks.beta_alpha_note}</p>
                <div style={{ display: 'grid', gap: 8 }}>
                  {context.benchmarks.items.map((item) => (
                    <div key={item.symbol} style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 12, padding: 12, border: '1px solid rgba(129, 160, 207, 0.12)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.58)' }}>
                      <span>{item.symbol}</span>
                      <strong className={(item.account_excess_return_percent ?? 0) >= 0 ? 'metric-positive' : 'metric-negative'}>{formatRawPct(item.account_excess_return_percent)}</strong>
                    </div>
                  ))}
                </div>
              </div></section>
            </div>

            {/* Position Table */}
            <section className="surface-panel"><div className="surface-panel__content">
              <h3 className="panel-title">Current Positions Top 5</h3>
              <p className="panel-subtitle">For observing account concentration and primary risk sources.</p>
              <div style={{ overflowX: 'auto' }}>
                <div style={{ display: 'grid', gap: 8, minWidth: 720 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'minmax(160px, 1.3fr) repeat(4, minmax(90px, 1fr))', gap: 12, color: 'var(--color-text-secondary)', fontSize: '0.82rem' }}>
                    <span>Stock</span><span>Market Value</span><span>Weight</span><span>Daily P&L</span><span>Unrealized P&L</span>
                  </div>
                  {topWeights.map((item) => (
                    <div key={item.symbol} style={{ display: 'grid', gridTemplateColumns: 'minmax(160px, 1.3fr) repeat(4, minmax(90px, 1fr))', gap: 12, padding: '12px 14px', border: '1px solid rgba(129, 160, 207, 0.12)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.58)' }}>
                      <span style={{ display: 'grid', gap: 3 }}><strong>{item.symbol}</strong><small style={{ color: 'var(--color-text-secondary)', overflowWrap: 'anywhere' }}>{item.name}</small></span>
                      <span>{formatNumber(item.market_value)}</span>
                      <span>{formatPct(item.weight)}</span>
                      <span className={itemTone(item)}>{formatNumber(item.daily_pnl)}</span>
                      <span className={(item.unrealized_pnl ?? 0) >= 0 ? 'metric-positive' : 'metric-negative'}>{formatNumber(item.unrealized_pnl)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div></section>
          </>}
        </>
      )}
    </section>
  )
}
