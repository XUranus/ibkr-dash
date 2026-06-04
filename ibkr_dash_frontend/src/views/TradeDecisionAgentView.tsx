import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import SymbolInput from '@/components/SymbolInput'
import AgentEvidencePanel from '@/components/AgentEvidencePanel'
import AgentTaskGraph from '@/components/AgentTaskGraph'
import type { AgentTask } from '@/types/agentTasks'
import type { TradeDecisionHoldingItem, TradeDecisionHealth, TradeDecisionResult } from '@/types/tradeDecision'
import { fetchTradeDecisionDetail, fetchTradeDecisionHoldings, fetchRecentTradeDecisions, fetchTradeDecisionHealth, fetchTradeDecisionTasks, startEntryDecisionTask, startHoldingDecisionTask } from '@/api/tradeDecision'

type DecisionMode = 'auto' | 'entry' | 'holding'
type DecisionTab = DecisionMode | 'research'

const scoreDimensions: [string, string][] = [
  ['fundamental_quality_score', 'Fundamental Quality'],
  ['valuation_score', 'Valuation'],
  ['trend_score', 'Trend Strength'],
  ['account_fit_score', 'Account Fit'],
  ['risk_reward_score', 'Risk/Reward'],
  ['review_constraint_score', 'Review Constraint'],
  ['event_catalyst_score', 'Event Catalyst'],
]

const actionLabels: Record<string, string> = { add: 'Add', add_small: 'Small Add', add_batch: 'Batch Add', hold: 'Hold', reduce: 'Reduce', reduce_batch: 'Batch Reduce', sell: 'Sell All', wait: 'Wait', avoid: 'Avoid', watchlist: 'Watchlist' }
const ratingLabels: Record<string, string> = { strong_buy_or_hold: 'Strong Buy/Hold', positive: 'Positive', neutral: 'Neutral', negative: 'Cautious' }
const decisionTypeLabels: Record<string, string> = { entry_decision: 'Entry Decision', holding_decision: 'Holding Decision' }

function actionLabel(v: string | null | undefined): string { return v ? (actionLabels[v] ?? v) : '--' }
function ratingLabel(v: string): string { return ratingLabels[v] ?? v }
function decisionTypeLabel(v: string): string { return decisionTypeLabels[v] ?? v }

export default function TradeDecisionAgentView() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [generatingKey, setGeneratingKey] = useState('')
  const [health, setHealth] = useState<TradeDecisionHealth | null>(null)
  const [currentHoldings, setCurrentHoldings] = useState<TradeDecisionHoldingItem[]>([])
  const [recentDecisions, setRecentDecisions] = useState<TradeDecisionResult[]>([])
  const [selectedDecision, setSelectedDecision] = useState<TradeDecisionResult | null>(null)
  const [taskItems, setTaskItems] = useState<AgentTask[]>([])
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null)
  const [showAllRecent, setShowAllRecent] = useState(false)
  const [symbol, setSymbol] = useState('')
  const [question, setQuestion] = useState('')
  const [decisionMode, setDecisionMode] = useState<DecisionMode>('auto')
  const [activeDecisionTab, setActiveDecisionTab] = useState<DecisionTab>((searchParams.get('tab') as DecisionTab) || 'auto')
  const [now, setNow] = useState(Date.now())
  const timerRef = useRef<number | undefined>(undefined)

  const recentLimit = 6
  const visibleRecent = showAllRecent ? recentDecisions : recentDecisions.slice(0, recentLimit)
  const hiddenCount = Math.max(0, recentDecisions.length - recentLimit)
  const activeTaskCount = taskItems.filter((t) => t.status === 'queued' || t.status === 'running').length
  const isGenerating = activeTaskCount > 0 || generatingKey !== ''
  const isDecisionWorkTab = activeDecisionTab !== 'research'

  function hasPosition(sym: string): TradeDecisionHoldingItem | undefined {
    return currentHoldings.find((h) => h.symbol === sym.trim().toUpperCase())
  }

  function setTab(tab: DecisionTab): void {
    setActiveDecisionTab(tab)
    if (tab !== 'research') setDecisionMode(tab)
    setSearchParams({ tab })
  }

  function taskElapsed(t: AgentTask): number {
    const start = Date.parse(t.started_at || t.created_at)
    const end = t.completed_at ? Date.parse(t.completed_at) : now
    return Math.max(0, Math.floor((end - start) / 1000))
  }

  function taskStage(t: AgentTask): string {
    if (t.status === 'completed') return 'Completed'
    if (t.status === 'failed') return t.error_message || 'Failed'
    const s = taskElapsed(t)
    if (s < 5) return 'Building account context'
    if (s < 20) return 'Fetching Longbridge quotes and events'
    if (s < 45) return 'Calling LLM for decision'
    return 'Saving result'
  }

  async function loadPage(): Promise<void> {
    setLoading(true); setErrorMessage('')
    try {
      const [h, holdings, decisions, tasks] = await Promise.all([
        fetchTradeDecisionHealth(), fetchTradeDecisionHoldings(),
        fetchRecentTradeDecisions({ limit: 10 }), fetchTradeDecisionTasks(20),
      ])
      setHealth(h); setCurrentHoldings(holdings.items); setRecentDecisions(decisions); setTaskItems(tasks)
      setGeneratingKey(tasks.some((t) => t.status === 'queued' || t.status === 'running') ? 'entry' : '')
      setSelectedDecision(decisions[0] ?? null)
    } catch (error) { setErrorMessage(error instanceof Error ? error.message : 'Failed to load') }
    finally { setLoading(false) }
  }

  async function generateDecision(): Promise<void> {
    const sym = symbol.trim().toUpperCase()
    if (!sym) return
    const position = hasPosition(sym)
    let mode = decisionMode
    if (mode === 'auto') mode = position ? 'holding' : 'entry'
    setGeneratingKey(mode); setErrorMessage('')
    try {
      const task = mode === 'holding'
        ? await startHoldingDecisionTask({ symbol: sym, question: question.trim() })
        : await startEntryDecisionTask({ symbol: sym, question: question.trim() })
      setTaskItems((prev) => [task, ...prev.filter((t) => t.id !== task.id)].slice(0, 20))
      await pollTasks()
    } catch (error) { setErrorMessage(error instanceof Error ? error.message : 'Generation failed'); setGeneratingKey('') }
  }

  async function pollTasks(): Promise<void> {
    try {
      const tasks = await fetchTradeDecisionTasks(20)
      setTaskItems(tasks)
      const latest = tasks.find((t) => t.status === 'completed' && t.result_id)
      if (latest?.result_id && selectedDecision?.id !== latest.result_id) {
        setSelectedDecision(await fetchTradeDecisionDetail(latest.result_id))
        setRecentDecisions(await fetchRecentTradeDecisions({ limit: 10 }))
      }
      if (!tasks.some((t) => t.status === 'queued' || t.status === 'running')) setGeneratingKey('')
    } catch { /* keep last state */ }
  }

  async function viewTaskResult(task: AgentTask): Promise<void> {
    if (task.result_id) setSelectedDecision(await fetchTradeDecisionDetail(task.result_id))
  }

  useEffect(() => {
    timerRef.current = window.setInterval(() => {
      setNow(Date.now())
      if (taskItems.some((t) => t.status === 'queued' || t.status === 'running')) void pollTasks()
    }, 2000)
    void loadPage()
    return () => { if (timerRef.current) window.clearInterval(timerRef.current) }
  }, [])

  const visibleTasks = [...taskItems.filter((t) => t.status === 'queued' || t.status === 'running'), ...taskItems.filter((t) => t.status === 'completed' || t.status === 'failed').slice(0, 2)]

  return (
    <section className="page-section">
      <section className="surface-panel"><div className="surface-panel__content">
        <div className="section-header" style={{ alignItems: 'center' }}>
          <div><p className="eyebrow">AGENT</p><h2 style={{ margin: 0, fontSize: '1.55rem' }}>AI Trade Decision</h2><p className="panel-subtitle">Enter a stock symbol for entry advice, holding management, or research analysis.</p></div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, justifyContent: 'flex-end' }}>
            <span style={{ padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', fontWeight: 600, background: health?.llm_configured ? 'rgba(52, 210, 163, 0.15)' : 'rgba(255, 107, 122, 0.15)', color: health?.llm_configured ? 'var(--color-positive)' : 'var(--color-negative)' }}>{health?.llm_configured ? 'LLM READY' : 'LLM MISSING'}</span>
            <span style={{ padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', fontWeight: 600, background: health?.longbridge_configured ? 'rgba(52, 210, 163, 0.15)' : 'rgba(86, 213, 255, 0.15)', color: health?.longbridge_configured ? 'var(--color-positive)' : 'var(--color-accent)' }}>{health?.longbridge_configured ? 'LONGBRIDGE READY' : 'LONGBRIDGE LIMITED'}</span>
          </div>
        </div>
      </div></section>

      {loading ? <section className="surface-panel"><div className="surface-panel__content"><div className="empty-state">Loading...</div></div></section> : (
        <>
          <section className="surface-panel"><div className="surface-panel__content">
            <div style={{ display: 'flex', gap: 12, marginBottom: 'var(--space-4)', padding: 12, border: '1px solid rgba(129, 160, 207, 0.14)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.46)' }}>
              {([['auto', 'Auto Detect'], ['entry', 'Entry (New)'], ['holding', 'Holding (Existing)'], ['research', 'Research']] as [DecisionTab, string][]).map(([tab, label]) => (
                <label key={tab} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', color: activeDecisionTab === tab ? 'var(--color-text-primary)' : 'var(--color-text-secondary)', fontWeight: 600 }}>
                  <input type="radio" checked={activeDecisionTab === tab} onChange={() => setTab(tab)} style={{ accentColor: 'var(--color-accent)' }} /><span>{label}</span>
                </label>
              ))}
            </div>

            {isDecisionWorkTab && (
              <form style={{ display: 'grid', gridTemplateColumns: 'minmax(180px, 0.6fr) minmax(240px, 1fr) auto', gap: 'var(--space-3)', alignItems: 'end' }} onSubmit={(e) => { e.preventDefault(); void generateDecision() }}>
                <label className="field-stack"><span className="field-stack__label">Symbol</span><SymbolInput value={symbol} onChange={setSymbol} required placeholder="AAPL / MSFT / NVDA" /></label>
                <label className="field-stack"><span className="field-stack__label">Question</span><input className="input" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Is now a good time to buy?" /></label>
                <button className="btn btn--accent" style={{ minWidth: 180, height: 44 }} type="submit" disabled={isGenerating}>{isGenerating ? 'Running...' : 'Generate'}</button>
              </form>
            )}

            {isDecisionWorkTab && symbol && hasPosition(symbol.toUpperCase()) && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 'var(--space-3)', padding: '10px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(32, 79, 129, 0.32)', color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
                <span style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', fontWeight: 600, background: 'rgba(86, 213, 255, 0.15)', color: 'var(--color-accent)' }}>EXISTING POSITION</span>
                <span>{symbol.toUpperCase()} has an existing position</span>
              </div>
            )}
          </div></section>

          {isDecisionWorkTab && visibleTasks.length > 0 && (
            <section className="surface-panel"><div className="surface-panel__content">
              <h3 className="panel-title">Background Tasks</h3>
              <p className="panel-subtitle">Tasks continue running on the backend. Status auto-refreshes.</p>
              <div style={{ display: 'grid', gap: 10 }}>
                {visibleTasks.map((task) => (
                  <div key={task.id} style={{ display: 'block', width: '100%', padding: '12px 14px', border: '1px solid rgba(129, 160, 207, 0.14)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.58)' }}>
                    <button type="button" style={{ display: 'grid', gridTemplateColumns: '12px minmax(0, 1fr) auto', gap: 12, alignItems: 'center', width: '100%', padding: 0, border: 0, background: 'transparent', color: 'var(--color-text-primary)', cursor: 'pointer', textAlign: 'left' }} onClick={() => setExpandedTaskId(expandedTaskId === task.id ? null : task.id)}>
                      <span style={{ width: 10, height: 10, borderRadius: 999, background: task.status === 'completed' ? 'var(--color-positive)' : task.status === 'failed' ? 'var(--color-negative)' : 'var(--color-accent)', animation: task.status === 'queued' || task.status === 'running' ? 'runner-pulse 1.2s ease-in-out infinite' : undefined }} />
                      <div style={{ display: 'grid', gap: 4 }}>
                        <strong>{task.label}</strong>
                        <span style={{ color: 'var(--color-text-secondary)' }}>{taskStage(task)}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', fontWeight: 600 }}>{task.status.toUpperCase()}</span>
                        <span style={{ color: 'var(--color-text-secondary)' }}>{taskElapsed(task)}s</span>
                        <span>{expandedTaskId === task.id ? '▲' : '▼'}</span>
                      </div>
                    </button>
                    {expandedTaskId === task.id && <AgentTaskGraph task={task} expanded={expandedTaskId === task.id} onSnapshot={() => {}} />}
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

          {isDecisionWorkTab && (
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 0.8fr) minmax(0, 1.2fr)', gap: 'var(--space-4)' }}>
              <section className="surface-panel"><div className="surface-panel__content">
                <h3 className="panel-title">Recent Decisions</h3>
                <p className="panel-subtitle">Each generation saves a history record.</p>
                {recentDecisions.length > 0 ? (
                  <div style={{ display: 'grid', gap: 10 }}>
                    {visibleRecent.map((item) => (
                      <button key={item.id} type="button" style={{ display: 'grid', gap: 6, width: '100%', padding: 14, border: `1px solid ${selectedDecision?.id === item.id ? 'rgba(86, 213, 255, 0.34)' : 'rgba(129, 160, 207, 0.14)'}`, borderRadius: 'var(--radius-md)', background: selectedDecision?.id === item.id ? 'rgba(19, 42, 70, 0.82)' : 'rgba(10, 18, 32, 0.62)', color: 'var(--color-text-primary)', cursor: 'pointer', textAlign: 'left' }} onClick={() => setSelectedDecision(item)}>
                        <strong>{item.symbol}</strong>
                        <span style={{ color: 'var(--color-text-secondary)' }}>{decisionTypeLabel(item.decision_type)}</span>
                        <span style={{ color: 'var(--color-text-secondary)' }}>{item.overall_score}/100 {'·'} {actionLabel(item.action)}</span>
                        <small style={{ color: 'var(--color-text-secondary)' }}>{item.decision_summary}</small>
                      </button>
                    ))}
                    {hiddenCount > 0 && <button type="button" className="btn btn--ghost btn--sm" onClick={() => setShowAllRecent(!showAllRecent)}>{showAllRecent ? 'Collapse' : `Show ${hiddenCount} more`}</button>}
                  </div>
                ) : <div className="empty-state">No AI decisions yet</div>}
              </div></section>

              {selectedDecision && (
                <section className="surface-panel"><div className="surface-panel__content">
                  <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) max-content', alignItems: 'flex-start', gap: 'var(--space-4)', marginBottom: 'var(--space-4)' }}>
                    <div><p className="eyebrow">{decisionTypeLabel(selectedDecision.decision_type)}</p>
                    <h3 style={{ margin: 0, fontSize: '3rem' }}>{selectedDecision.overall_score}<span style={{ fontSize: '1.1rem', color: 'var(--color-text-secondary)' }}>/100</span></h3>
                    <p className="panel-subtitle">{selectedDecision.decision_summary}</p></div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
                      <span style={{ padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', fontWeight: 600, background: 'rgba(86, 213, 255, 0.15)', color: 'var(--color-accent)' }}>{actionLabel(selectedDecision.action)}</span>
                      <span style={{ padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', fontWeight: 600, background: selectedDecision.overall_score >= 70 ? 'rgba(52, 210, 163, 0.15)' : selectedDecision.overall_score < 50 ? 'rgba(255, 107, 122, 0.15)' : 'rgba(86, 213, 255, 0.15)', color: selectedDecision.overall_score >= 70 ? 'var(--color-positive)' : selectedDecision.overall_score < 50 ? 'var(--color-negative)' : 'var(--color-accent)' }}>{ratingLabel(selectedDecision.rating)}</span>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 'var(--space-3)' }}>
                    {scoreDimensions.map(([key, label]) => (
                      <div key={key} style={{ padding: 16, border: '1px solid rgba(129, 160, 207, 0.12)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.58)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 8 }}>
                          <span style={{ color: 'var(--color-text-secondary)' }}>{label}</span>
                          <strong>{selectedDecision.score_detail[key]?.score ?? 0}/{selectedDecision.score_detail[key]?.max_score ?? 0}</strong>
                        </div>
                        <p style={{ margin: 0, color: 'var(--color-text-secondary)' }}>{selectedDecision.score_detail[key]?.reason ?? 'No explanation'}</p>
                      </div>
                    ))}
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 'var(--space-3)', marginTop: 'var(--space-4)' }}>
                    <div style={{ padding: 16, border: '1px solid rgba(129, 160, 207, 0.12)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.58)', display: 'grid', gap: 8 }}>
                      <h4 style={{ margin: 0 }}>Position Advice</h4>
                      <span style={{ color: 'var(--color-text-secondary)' }}>Current: {(selectedDecision.position_advice.current_position_pct ?? 0).toFixed(2)}%</span>
                      <span style={{ color: 'var(--color-text-secondary)' }}>Target: {(selectedDecision.position_advice.suggested_target_position_pct ?? 0).toFixed(2)}%</span>
                      <span style={{ color: 'var(--color-text-secondary)' }}>Max: {(selectedDecision.position_advice.max_position_pct ?? 0).toFixed(2)}%</span>
                    </div>
                    <div style={{ padding: 16, border: '1px solid rgba(129, 160, 207, 0.12)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.58)', display: 'grid', gap: 8 }}>
                      <h4 style={{ margin: 0 }}>Key Reasons</h4>
                      <ul style={{ margin: 0, paddingLeft: 18 }}>{selectedDecision.key_reasons.map((r, i) => <li key={i} style={{ color: 'var(--color-text-secondary)' }}>{r}</li>)}</ul>
                    </div>
                    <div style={{ padding: 16, border: '1px solid rgba(129, 160, 207, 0.12)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.58)', display: 'grid', gap: 8 }}>
                      <h4 style={{ margin: 0 }}>Major Risks</h4>
                      <ul style={{ margin: 0, paddingLeft: 18 }}>{selectedDecision.major_risks.map((r, i) => <li key={i} style={{ color: 'var(--color-text-secondary)' }}>{r}</li>)}</ul>
                    </div>
                    <div style={{ padding: 16, border: '1px solid rgba(129, 160, 207, 0.12)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.58)', display: 'grid', gap: 8 }}>
                      <h4 style={{ margin: 0 }}>Review Warnings</h4>
                      <ul style={{ margin: 0, paddingLeft: 18 }}>{selectedDecision.review_warnings.map((r, i) => <li key={i} style={{ color: 'var(--color-text-secondary)' }}>{r}</li>)}</ul>
                    </div>
                  </div>

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 'var(--space-4)' }}>
                    <span style={{ padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', fontWeight: 600, background: 'rgba(52, 210, 163, 0.15)', color: 'var(--color-positive)' }}>Account/Positions: IBKR</span>
                    <span style={{ padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', fontWeight: 600, background: 'rgba(86, 213, 255, 0.15)', color: 'var(--color-accent)' }}>Market Data: Longbridge</span>
                    <span style={{ padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', fontWeight: 600, background: 'rgba(86, 213, 255, 0.15)', color: 'var(--color-accent)' }}>Decision: LLM</span>
                  </div>
                </div></section>
              )}
            </div>
          )}

          {isDecisionWorkTab && selectedDecision && (
            <AgentEvidencePanel metadata={selectedDecision.metadata} evidenceSummary={selectedDecision.evidence_summary} runTraceSummary={selectedDecision.run_trace_summary} />
          )}
        </>
      )}
    </section>
  )
}
