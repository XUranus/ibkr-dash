import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import SymbolInput from '@/components/SymbolInput'
import AgentEvidencePanel from '@/components/AgentEvidencePanel'
import AgentTaskGraph from '@/components/AgentTaskGraph'
import type { AgentTask } from '@/types/agentTasks'
import type { TradeReviewHealth, TradeReviewMistakeSummaryItem, TradeReviewResult } from '@/types/tradeReview'
import { fetchMistakeSummary, fetchRecentTradeReviews, fetchTradeReviewDetail, fetchTradeReviewHealth, fetchTradeReviewTasks, startSingleTradeReviewTask, startSymbolReviewTask } from '@/api/tradeReview'

type ReviewTab = 'symbol-review' | 'daily-review'

const scoreDimensions: [string, string][] = [
  ['return_result_score', 'Return Result'],
  ['relative_performance_score', 'Relative Performance'],
  ['entry_quality_score', 'Entry Quality'],
  ['exit_quality_score', 'Exit Quality'],
  ['position_sizing_score', 'Position Sizing'],
  ['holding_period_score', 'Holding Period'],
  ['risk_control_score', 'Risk Control'],
  ['decision_attribution_score', 'Decision Attribution'],
]

const mistakeTagLabels: Record<string, string> = { CHASE_HIGH: 'Chase High', SELL_TOO_EARLY: 'Sold Early', SELL_TOO_LATE: 'Sold Late', PANIC_SELL: 'Panic Sell', POSITION_TOO_SMALL: 'Position Too Small', POSITION_TOO_LARGE: 'Position Too Large', MISSED_OPPORTUNITY: 'Missed Opportunity', NO_CLEAR_PLAN: 'No Clear Plan', GOOD_ENTRY: 'Good Entry', GOOD_EXIT: 'Good Exit', GOOD_POSITION_SIZING: 'Good Sizing', GOOD_RISK_CONTROL: 'Good Risk Control' }
const reviewTypeLabels: Record<string, string> = { symbol_level_review: 'Symbol Review', single_trade_review: 'Single Trade Review' }
const ratingLabels: Record<string, string> = { excellent: 'Excellent', good: 'Good', average: 'Average', poor: 'Poor' }

export default function TradeReviewAgentView() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [health, setHealth] = useState<TradeReviewHealth | null>(null)
  const [recentReviews, setRecentReviews] = useState<TradeReviewResult[]>([])
  const [mistakeItems, setMistakeItems] = useState<TradeReviewMistakeSummaryItem[]>([])
  const [selectedReview, setSelectedReview] = useState<TradeReviewResult | null>(null)
  const [showAllRecent, setShowAllRecent] = useState(false)
  const [reviewTasks, setReviewTasks] = useState<AgentTask[]>([])
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null)
  const [activeReviewTab, setActiveReviewTab] = useState<ReviewTab>((searchParams.get('tab') as ReviewTab) || 'symbol-review')
  const [symbol, setSymbol] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [tradeId, setTradeId] = useState('')
  const [now, setNow] = useState(Date.now())
  const timerRef = useRef<number | undefined>(undefined)

  const recentLimit = 6
  const visibleRecent = showAllRecent ? recentReviews : recentReviews.slice(0, recentLimit)
  const hiddenCount = Math.max(0, recentReviews.length - recentLimit)
  const activeTaskCount = reviewTasks.filter((t) => t.status === 'queued' || t.status === 'running').length
  const visibleTasks = [...reviewTasks.filter((t) => t.status === 'queued' || t.status === 'running'), ...reviewTasks.filter((t) => t.status === 'completed' || t.status === 'failed').slice(0, 2)]
  const isGeneratingSymbol = reviewTasks.some((t) => t.task_type === 'symbol_level_review' && (t.status === 'queued' || t.status === 'running'))
  const isGeneratingTrade = reviewTasks.some((t) => t.task_type === 'single_trade_review' && (t.status === 'queued' || t.status === 'running'))

  function taskElapsed(t: AgentTask): number { const s = Date.parse(t.started_at || t.created_at); const e = t.completed_at ? Date.parse(t.completed_at) : now; return Math.max(0, Math.floor((e - s) / 1000)) }
  function formatElapsed(t: AgentTask): string { const s = taskElapsed(t); return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s` }
  function taskStage(t: AgentTask): string { if (t.status === 'completed') return 'Completed'; if (t.status === 'failed') return t.error_message || 'Failed'; const s = taskElapsed(t); if (s < 5) return 'Building IBKR trade facts'; if (s < 15) return 'Fetching Longbridge K-line and events'; if (s < 35) return 'Calling LLM for 8-dimension scoring'; return 'Saving review result' }
  function mistakeTagLabel(tag: string): string { return mistakeTagLabels[tag] ?? tag }
  function reviewTypeLabel(rt: string): string { return reviewTypeLabels[rt] ?? rt }
  function ratingLabel(r: string): string { return ratingLabels[r] ?? r }
  function ratingClass(r: string): string { if (r === 'excellent' || r === 'good') return 'tag-positive'; if (r === 'poor') return 'tag-negative'; return 'tag-accent' }

  const loadPage = useCallback(async () => {
    setLoading(true); setErrorMessage('')
    try {
      const [h, reviews, mistakes, tasks] = await Promise.all([
        fetchTradeReviewHealth(), fetchRecentTradeReviews({ limit: 20 }),
        fetchMistakeSummary(), fetchTradeReviewTasks(20),
      ])
      setHealth(h); setRecentReviews(reviews); setMistakeItems(mistakes.items); setReviewTasks(tasks)
      setSelectedReview(reviews[0] ?? null)
    } catch (error) { setErrorMessage(error instanceof Error ? error.message : 'Failed to load') }
    finally { setLoading(false) }
  }, [])

  async function generateSymbol(): Promise<void> {
    const sym = symbol.trim().toUpperCase()
    if (!sym) return
    setErrorMessage('')
    try {
      const task = await startSymbolReviewTask({ symbol: sym, start_date: startDate, end_date: endDate })
      setReviewTasks((prev) => [task, ...prev.filter((t) => t.id !== task.id)].slice(0, 20))
      await pollTasks()
    } catch (error) { setErrorMessage(error instanceof Error ? error.message : 'Generation failed') }
  }

  async function generateTrade(): Promise<void> {
    const tid = tradeId.trim()
    if (!tid) return
    setErrorMessage('')
    try {
      const task = await startSingleTradeReviewTask(tid)
      setReviewTasks((prev) => [task, ...prev.filter((t) => t.id !== task.id)].slice(0, 20))
      await pollTasks()
    } catch (error) { setErrorMessage(error instanceof Error ? error.message : 'Generation failed') }
  }

  async function pollTasks(): Promise<void> {
    try {
      const tasks = await fetchTradeReviewTasks(20)
      setReviewTasks(tasks)
      const latest = tasks.find((t) => t.status === 'completed' && t.result_id)
      if (latest?.result_id && selectedReview?.id !== latest.result_id) {
        setSelectedReview(await fetchTradeReviewDetail(latest.result_id))
        const [reviews, mistakes] = await Promise.all([fetchRecentTradeReviews({ limit: 20 }), fetchMistakeSummary()])
        setRecentReviews(reviews); setMistakeItems(mistakes.items)
      }
    } catch { /* keep last state */ }
  }

  async function selectReview(review: TradeReviewResult): Promise<void> {
    try { setSelectedReview(await fetchTradeReviewDetail(review.id)) }
    catch { setSelectedReview(review) }
  }

  async function viewTaskResult(task: AgentTask): Promise<void> {
    if (task.result_id) setSelectedReview(await fetchTradeReviewDetail(task.result_id))
  }

  useEffect(() => {
    const tid = searchParams.get('trade_id')
    if (tid) setTradeId(tid)
    timerRef.current = window.setInterval(() => {
      setNow(Date.now())
      if (activeTaskCount) void pollTasks()
    }, 1000)
    void loadPage()
    return () => { if (timerRef.current) window.clearInterval(timerRef.current) }
  }, [])

  return (
    <section className="page-section">
      <section className="surface-panel"><div className="surface-panel__content">
        <div className="section-header" style={{ alignItems: 'center' }}>
          <div><p className="eyebrow">AGENT</p><h2 style={{ margin: 0, fontSize: '1.55rem' }}>AI Trade Review</h2><p className="panel-subtitle">Review individual stock trade performance or analyze daily account P&L attribution.</p></div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, justifyContent: 'flex-end' }}>
            <span style={{ padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', fontWeight: 600, background: health?.llm_configured ? 'rgba(52, 210, 163, 0.15)' : 'rgba(255, 107, 122, 0.15)', color: health?.llm_configured ? 'var(--color-positive)' : 'var(--color-negative)' }}>{health?.llm_configured ? 'LLM READY' : 'LLM MISSING'}</span>
          </div>
        </div>
      </div></section>

      {loading ? <section className="surface-panel"><div className="surface-panel__content"><div className="empty-state">Loading...</div></div></section> : (
        <>
          <section className="surface-panel"><div className="surface-panel__content">
            <div style={{ display: 'flex', gap: 12, padding: 12, border: '1px solid rgba(129, 160, 207, 0.14)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.46)' }}>
              {([['symbol-review', 'Symbol Review'], ['daily-review', 'Daily Review']] as [ReviewTab, string][]).map(([tab, label]) => (
                <label key={tab} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', color: activeReviewTab === tab ? 'var(--color-text-primary)' : 'var(--color-text-secondary)', fontWeight: 600 }}>
                  <input type="radio" checked={activeReviewTab === tab} onChange={() => { setActiveReviewTab(tab); setSearchParams({ tab }) }} style={{ accentColor: 'var(--color-accent)' }} /><span>{label}</span>
                </label>
              ))}
            </div>
          </div></section>

          {activeReviewTab === 'symbol-review' && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 'var(--space-4)' }}>
                <section className="surface-panel"><div className="surface-panel__content">
                  <h3 className="panel-title">Symbol-Level Review</h3>
                  <p className="panel-subtitle">Review the full buy, add, reduce, sell history of a symbol.</p>
                  <form style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 'var(--space-3)' }} onSubmit={(e) => { e.preventDefault(); void generateSymbol() }}>
                    <label className="field-stack" style={{ gridColumn: '1 / -1' }}><span className="field-stack__label">Symbol</span><SymbolInput value={symbol} onChange={setSymbol} placeholder="ARM / MSFT / AMD" /></label>
                    <label className="field-stack"><span className="field-stack__label">Start Date</span><input className="input" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} /></label>
                    <label className="field-stack"><span className="field-stack__label">End Date</span><input className="input" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} /></label>
                    <div style={{ gridColumn: '1 / -1' }}><button className="btn btn--accent" disabled={isGeneratingSymbol} type="submit">{isGeneratingSymbol ? 'Generating...' : 'Generate Symbol Review'}</button></div>
                  </form>
                </div></section>
                <section className="surface-panel"><div className="surface-panel__content">
                  <h3 className="panel-title">Single Trade Review</h3>
                  <p className="panel-subtitle">Review a specific buy, sell, add, or reduce trade.</p>
                  <form style={{ display: 'grid', gap: 'var(--space-3)' }} onSubmit={(e) => { e.preventDefault(); void generateTrade() }}>
                    <label className="field-stack"><span className="field-stack__label">Trade ID</span><input className="input" value={tradeId} onChange={(e) => setTradeId(e.target.value)} placeholder="trade_id / transaction_id" /></label>
                    <button className="btn btn--accent" disabled={isGeneratingTrade} type="submit">{isGeneratingTrade ? 'Generating...' : 'Generate Trade Review'}</button>
                  </form>
                </div></section>
              </div>

              {visibleTasks.length > 0 && (
                <section className="surface-panel"><div className="surface-panel__content">
                  <h3 className="panel-title">Review Tasks</h3>
                  <p className="panel-subtitle">{activeTaskCount ? `${activeTaskCount} reviews running` : 'Recently completed reviews'}</p>
                  <div style={{ display: 'grid', gap: 10 }}>
                    {visibleTasks.map((task) => (
                      <div key={task.id} style={{ padding: '14px 16px', border: '1px solid rgba(129, 160, 207, 0.14)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.58)' }}>
                        <button type="button" style={{ display: 'grid', gridTemplateColumns: '12px minmax(0, 1fr) auto', gap: 14, alignItems: 'center', width: '100%', padding: 0, border: 0, background: 'transparent', color: 'var(--color-text-primary)', cursor: 'pointer', textAlign: 'left' }} onClick={() => setExpandedTaskId(expandedTaskId === task.id ? null : task.id)}>
                          <span style={{ width: 10, height: 10, borderRadius: 999, background: task.status === 'completed' ? '#58d6a1' : task.status === 'failed' ? '#ff6b7a' : 'var(--color-accent)', animation: task.status === 'queued' || task.status === 'running' ? 'runner-pulse 1.2s ease-in-out infinite' : undefined }} />
                          <div style={{ display: 'grid', gap: 4 }}><strong style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{task.label}</strong><span style={{ color: 'var(--color-text-secondary)', fontSize: '0.86rem' }}>{taskStage(task)}</span></div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <span style={{ color: 'var(--color-text-secondary)' }}>{formatElapsed(task)}</span>
                            <span style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', fontWeight: 600 }}>{task.status.toUpperCase()}</span>
                            <span>{expandedTaskId === task.id ? '▲' : '▼'}</span>
                          </div>
                        </button>
                        {expandedTaskId === task.id && <AgentTaskGraph task={task} expanded onSnapshot={() => {}} />}
                        {expandedTaskId === task.id && task.result_id && (
                          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 10 }}>
                            <button className="btn btn--ghost btn--sm" onClick={() => void viewTaskResult(task)}>View Result</button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div></section>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 0.72fr) minmax(0, 1.28fr)', gap: 'var(--space-4)', alignItems: 'start' }}>
                <section className="surface-panel"><div className="surface-panel__content">
                  <h3 className="panel-title">Recent Reviews</h3>
                  <p className="panel-subtitle">Default shows the latest review result.</p>
                  {recentReviews.length > 0 ? (
                    <div style={{ display: 'grid', gap: 10 }}>
                      {visibleRecent.map((review) => (
                        <button key={review.id} style={{ display: 'grid', gap: 6, width: '100%', padding: 14, border: `1px solid ${selectedReview?.id === review.id ? 'rgba(86, 213, 255, 0.34)' : 'rgba(129, 160, 207, 0.14)'}`, borderRadius: 'var(--radius-md)', background: selectedReview?.id === review.id ? 'rgba(19, 42, 70, 0.82)' : 'rgba(10, 18, 32, 0.62)', color: 'var(--color-text-primary)', cursor: 'pointer', textAlign: 'left' }} onClick={() => void selectReview(review)}>
                          <strong>{review.symbol}</strong>
                          <span style={{ color: 'var(--color-text-secondary)' }}>{reviewTypeLabel(review.review_type)}</span>
                          <span style={{ color: 'var(--color-text-secondary)' }}>{review.overall_score}/100 {'·'} {ratingLabel(review.rating)}</span>
                          <small style={{ color: 'var(--color-text-secondary)' }}>{review.summary}</small>
                        </button>
                      ))}
                      {hiddenCount > 0 && <button type="button" className="btn btn--ghost btn--sm" onClick={() => setShowAllRecent(!showAllRecent)}>{showAllRecent ? 'Collapse' : `Show ${hiddenCount} more`}</button>}
                    </div>
                  ) : <div className="empty-state">No reviews yet</div>}
                </div></section>

                {selectedReview ? (
                  <section className="surface-panel"><div className="surface-panel__content">
                    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) max-content', alignItems: 'flex-start', gap: 'var(--space-4)', marginBottom: 'var(--space-4)' }}>
                      <div>
                        <p className="eyebrow">{reviewTypeLabel(selectedReview.review_type)}</p>
                        <h3 style={{ margin: 0, fontSize: '3rem' }}>{selectedReview.overall_score}<span style={{ fontSize: '1.1rem', color: 'var(--color-text-secondary)' }}>/100</span></h3>
                        <p className="panel-subtitle">{selectedReview.summary}</p>
                      </div>
                      <span className={ratingClass(selectedReview.rating)} style={{ padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: '0.82rem', fontWeight: 600 }}>{ratingLabel(selectedReview.rating)}</span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 'var(--space-3)' }}>
                      {scoreDimensions.map(([key, label]) => {
                        const item = selectedReview.score_detail[key]
                        const isNA = item?.applicable === false
                        return (
                          <div key={key} style={{ padding: 16, borderRadius: 'var(--radius-md)', border: '1px solid rgba(129, 160, 207, 0.12)', background: 'rgba(10, 18, 32, 0.58)', opacity: isNA ? 0.5 : 1 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 8 }}>
                              <span style={{ color: 'var(--color-text-secondary)' }}>{label}</span>
                              <strong style={isNA ? { color: 'var(--color-text-secondary)', fontWeight: 500 } : undefined}>{isNA ? 'N/A' : `${item?.score ?? 0}/${item?.max_score ?? 0}`}</strong>
                            </div>
                            <p style={{ margin: 0, color: 'var(--color-text-secondary)' }}>{item?.reason || 'No explanation'}</p>
                          </div>
                        )
                      })}
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 'var(--space-3)', marginTop: 'var(--space-4)' }}>
                      {[['Strengths', selectedReview.strengths], ['Weaknesses', selectedReview.weaknesses], ['Improvements', selectedReview.improvement_suggestions], ['Data Limitations', selectedReview.data_limitations]].map(([title, items]) => (
                        <div key={title} style={{ padding: 16, borderRadius: 'var(--radius-md)', border: '1px solid rgba(129, 160, 207, 0.12)', background: 'rgba(10, 18, 32, 0.58)' }}>
                          <h4 style={{ margin: '0 0 10px' }}>{title}</h4>
                          <ul style={{ display: 'grid', gap: 8, margin: 0, paddingLeft: 18 }}>{(items as string[]).map((item, i) => <li key={i} style={{ color: 'var(--color-text-secondary)' }}>{item}</li>)}</ul>
                        </div>
                      ))}
                    </div>

                    {selectedReview.mistake_tags.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 'var(--space-4)' }}>
                        {selectedReview.mistake_tags.map((tag) => <span key={tag} style={{ padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', fontWeight: 600, background: 'rgba(86, 213, 255, 0.15)', color: 'var(--color-accent)' }}>{mistakeTagLabel(tag)}</span>)}
                      </div>
                    )}
                  </div></section>
                ) : <section className="surface-panel"><div className="surface-panel__content"><div className="empty-state">Select a review to view results</div></div></section>}
              </div>

              {selectedReview && <AgentEvidencePanel metadata={selectedReview.metadata} evidenceSummary={selectedReview.evidence_summary} runTraceSummary={selectedReview.run_trace_summary} />}

              <section className="surface-panel"><div className="surface-panel__content">
                <h3 className="panel-title">Mistake Pattern Summary</h3>
                <p className="panel-subtitle">Aggregated by mistake_tags across historical reviews.</p>
                {mistakeItems.length > 0 ? (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 'var(--space-3)' }}>
                    {mistakeItems.map((item) => (
                      <div key={item.tag} style={{ padding: 16, borderRadius: 'var(--radius-md)', border: '1px solid rgba(129, 160, 207, 0.12)', background: 'rgba(10, 18, 32, 0.58)', display: 'grid', gap: 6 }}>
                        <strong>{mistakeTagLabel(item.tag)}</strong>
                        <span style={{ color: 'var(--color-accent)', fontWeight: 700 }}>{item.count} times</span>
                        <small style={{ color: 'var(--color-text-secondary)' }}>{item.symbols.join(', ') || '--'}</small>
                      </div>
                    ))}
                  </div>
                ) : <div className="empty-state">No mistake pattern data</div>}
              </div></section>
            </>
          )}
        </>
      )}
    </section>
  )
}
