import { useState, useEffect, useCallback } from 'react'
import {
  createEvalCaseFromReplay,
  exportAgentReplay,
  getAgentReplay,
  getAgentReplayByRun,
  getAgentRun,
  getEvalCase,
  getEvalRun,
  listAgentReplays,
  listAgentRuns,
  listEvalCases,
  listEvalRuns,
  listLlmCalls,
  runEval,
  seedEvalCases,
} from '@/api/adminHarness'
import AdminTabs from '@/components/AdminTabs'
import JsonBlock from '@/components/JsonBlock'
import type {
  AgentReplaySnapshot,
  AgentRunTraceDetail,
  AgentRunTraceListItem,
  EvalCase,
  EvalCaseResult,
  EvalRun,
  LLMCallMetric,
} from '@/types/adminHarness'

type HarnessTab = 'overview' | 'llm-calls' | 'agent-runs' | 'replays' | 'eval-cases' | 'eval-runs'

const harnessTabs: { key: HarnessTab; label: string; description: string }[] = [
  { key: 'overview', label: 'Overview', description: 'Overall agent harness status including LLM calls, tool calls, eval runs, and recent failures.' },
  { key: 'llm-calls', label: 'LLM Calls', description: 'LLM call records with model, provider, call type, latency, token usage, cost, and error info.' },
  { key: 'agent-runs', label: 'Agent Runs', description: 'Agent run records with status, execution time, call chain, fallback, data limitations, and errors.' },
  { key: 'replays', label: 'Replays', description: 'Replay snapshots for reproducing agent runs, including input, context, tool results, and final output.' },
  { key: 'eval-cases', label: 'Eval Cases', description: 'Agent evaluation test cases with input, expected fields, forbidden behavior, and scoring rubric.' },
  { key: 'eval-runs', label: 'Eval Runs', description: 'Eval run results with pass rate, failed cases, score details, and error reasons.' },
]

export default function AdminHarnessView() {
  const [activeTab, setActiveTab] = useState<HarnessTab>('overview')
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [noticeMessage, setNoticeMessage] = useState('')

  const [llmCalls, setLlmCalls] = useState<LLMCallMetric[]>([])
  const [llmSummary, setLlmSummary] = useState<Record<string, unknown>>({})
  const [agentRuns, setAgentRuns] = useState<AgentRunTraceListItem[]>([])
  const [agentRunSummary, setAgentRunSummary] = useState<Record<string, unknown>>({})
  const [replays, setReplays] = useState<AgentReplaySnapshot[]>([])
  const [evalCases, setEvalCases] = useState<EvalCase[]>([])
  const [evalRuns, setEvalRuns] = useState<EvalRun[]>([])
  const [evalRunSummary, setEvalRunSummary] = useState<Record<string, unknown>>({})

  const [selectedRun, setSelectedRun] = useState<AgentRunTraceDetail | null>(null)
  const [selectedReplay, setSelectedReplay] = useState<AgentReplaySnapshot | null>(null)
  const [selectedEvalCase, setSelectedEvalCase] = useState<EvalCase | null>(null)
  const [selectedEvalRun, setSelectedEvalRun] = useState<EvalRun | null>(null)
  const [exportPackage, setExportPackage] = useState<Record<string, unknown> | null>(null)

  const [llmFilters, setLlmFilters] = useState({ hours: 24, agent_name: '', prompt_key: '', model: '', ok: '', limit: 100 })
  const [runFilters, setRunFilters] = useState({ hours: 24, agent_name: '', final_status: '', limit: 100 })
  const [replayFilters, setReplayFilters] = useState({ hours: 24, agent_name: '', final_status: '', limit: 100 })
  const [caseFilters, setCaseFilters] = useState({ agent_name: '', source: '', limit: 100 })
  const [evalRunFilters, setEvalRunFilters] = useState({ hours: 24, agent_name: '', limit: 100 })

  function formatDateTime(v?: string | null): string { return v ? v.slice(0, 19).replace('T', ' ') : '-' }
  function formatNumber(v?: number | null): string { return v == null || Number.isNaN(v) ? '-' : new Intl.NumberFormat().format(v) }
  function formatLatency(v?: number | null): string { return v == null ? '-' : `${formatNumber(Math.round(v))}ms` }
  function formatCost(v?: number | null): string { return v == null ? '-' : `$${v.toFixed(6)}` }
  function formatRate(v?: number | null): string { return v == null || Number.isNaN(v) ? '-' : `${(v * 100).toFixed(1)}%` }
  function statusClass(s?: string | null): string { if (s === 'success' || s === 'passed' || s === 'completed') return 'tag-positive'; if (s === 'failed' || s === 'error') return 'tag-negative'; if (s === 'warning' || s === 'partial') return 'tag-warning'; return 'tag-accent' }

  async function withLoading(action: () => Promise<void>): Promise<void> {
    setLoading(true); setErrorMessage(''); setNoticeMessage('')
    try { await action() }
    catch (error) { setErrorMessage(error instanceof Error ? error.message : 'Load failed') }
    finally { setLoading(false) }
  }

  const loadOverview = useCallback(async () => {
    setLoading(true); setErrorMessage('')
    const [llm, runs, replayList, evalRunList] = await Promise.allSettled([
      listLlmCalls({ hours: 24, limit: 100 }), listAgentRuns({ hours: 24, limit: 100 }),
      listAgentReplays({ hours: 24, limit: 100 }), listEvalRuns({ hours: 24, limit: 100 }),
    ])
    if (llm.status === 'fulfilled') { setLlmCalls(llm.value.items); setLlmSummary(llm.value.summary ?? {}) }
    if (runs.status === 'fulfilled') { setAgentRuns(runs.value.items); setAgentRunSummary(runs.value.summary ?? {}) }
    if (replayList.status === 'fulfilled') setReplays(replayList.value.items)
    if (evalRunList.status === 'fulfilled') { setEvalRuns(evalRunList.value.items); setEvalRunSummary(evalRunList.value.summary ?? {}) }
    setLoading(false)
  }, [])

  async function loadLlmCalls(): Promise<void> { await withLoading(async () => { const r = await listLlmCalls({ ...llmFilters, ok: llmFilters.ok === '' ? null : llmFilters.ok === 'true' }); setLlmCalls(r.items); setLlmSummary(r.summary ?? {}) }) }
  async function loadAgentRuns(): Promise<void> { await withLoading(async () => { const r = await listAgentRuns(runFilters); setAgentRuns(r.items); setAgentRunSummary(r.summary ?? {}) }) }
  async function loadReplays(): Promise<void> { await withLoading(async () => { const r = await listAgentReplays(replayFilters); setReplays(r.items) }) }
  async function loadEvalCases(): Promise<void> { await withLoading(async () => { const r = await listEvalCases(caseFilters); setEvalCases(r.items) }) }
  async function loadEvalRuns(): Promise<void> { await withLoading(async () => { const r = await listEvalRuns(evalRunFilters); setEvalRuns(r.items); setEvalRunSummary(r.summary ?? {}) }) }

  async function loadCurrentTab(): Promise<void> {
    if (activeTab === 'overview') return loadOverview()
    if (activeTab === 'llm-calls') return loadLlmCalls()
    if (activeTab === 'agent-runs') return loadAgentRuns()
    if (activeTab === 'replays') return loadReplays()
    if (activeTab === 'eval-cases') return loadEvalCases()
    return loadEvalRuns()
  }

  async function openRun(row: AgentRunTraceListItem): Promise<void> { setSelectedRun(await getAgentRun(row.run_id)) }
  async function openReplay(row: AgentReplaySnapshot): Promise<void> { if (!row.replay_id) return; setExportPackage(null); setSelectedReplay(await getAgentReplay(row.replay_id)) }
  async function openReplayByRun(runId?: string | null): Promise<void> {
    if (!runId) return
    try { const r = await getAgentReplayByRun(runId); setSelectedReplay(r); setNoticeMessage(`Found replay ${r.replay_id}`) }
    catch (error) { setErrorMessage(error instanceof Error ? error.message : 'No replay for this run') }
  }
  async function openEvalCase(row: EvalCase): Promise<void> { if (row.case_id) setSelectedEvalCase(await getEvalCase(row.case_id)) }
  async function openEvalRun(row: EvalRun): Promise<void> { if (row.eval_run_id) setSelectedEvalRun(await getEvalRun(row.eval_run_id)) }
  async function exportReplay(): Promise<void> { if (selectedReplay?.replay_id) setExportPackage(await exportAgentReplay(selectedReplay.replay_id)) }
  async function createCaseFromReplay(): Promise<void> {
    if (!selectedReplay?.replay_id) return
    const c = await createEvalCaseFromReplay(selectedReplay.replay_id, true); setNoticeMessage(`Created eval case: ${c.case_id}`); void loadEvalCases()
  }
  async function runEvalForReplay(): Promise<void> {
    if (!selectedReplay?.replay_id) return
    const r = await runEval({ replay_ids: [selectedReplay.replay_id], mode: 'static', name: `Static eval from replay ${selectedReplay.replay_id}` }); setSelectedEvalRun(r); setActiveTab('eval-runs'); setNoticeMessage(`Eval run complete: ${r.eval_run_id}`); void loadEvalRuns()
  }
  async function seedCases(): Promise<void> { const r = await seedEvalCases(false); setNoticeMessage(`Seed: created=${(r as Record<string, unknown>).created_count ?? 0}`); void loadEvalCases() }
  async function runEvalForCase(caseId?: string): Promise<void> {
    if (!caseId) return
    const r = await runEval({ case_ids: [caseId], mode: 'static', name: `Static eval case ${caseId}` }); setSelectedEvalRun(r); setActiveTab('eval-runs'); setNoticeMessage(`Eval run: ${r.eval_run_id}`); void loadEvalRuns()
  }

  useEffect(() => { void loadOverview() }, [])
  useEffect(() => { void loadCurrentTab() }, [activeTab])

  const activeHarnessTab = harnessTabs.find((t) => t.key === activeTab) ?? harnessTabs[0]
  const overviewCards = [
    { label: 'LLM Calls', value: formatNumber(llmSummary.call_count as number ?? llmCalls.length) },
    { label: 'LLM Success Rate', value: formatRate(llmSummary.success_rate as number ?? (llmCalls.length ? llmCalls.filter((c) => c.ok).length / llmCalls.length : 0)) },
    { label: 'Total Tokens', value: formatNumber(llmCalls.reduce((s, c) => s + (c.total_tokens ?? 0), 0)) },
    { label: 'Agent Runs', value: formatNumber(agentRuns.length) },
    { label: 'Run Success Rate', value: formatRate(agentRuns.length ? agentRuns.filter((r) => r.final_status === 'success').length / agentRuns.length : 0) },
    { label: 'Replays', value: formatNumber(replays.length) },
    { label: 'Eval Runs', value: formatNumber(evalRuns.length) },
    { label: 'Eval Pass Rate', value: formatRate((evalRuns[0]?.summary?.pass_rate as number) ?? 0) },
  ]

  const cellStyle: React.CSSProperties = { padding: '10px 8px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)', textAlign: 'left', verticalAlign: 'top' }
  const thStyle: React.CSSProperties = { ...cellStyle, color: 'var(--color-text-secondary)', fontWeight: 700 }

  return (
    <section className="page-section">
      <section className="surface-panel"><div className="surface-panel__content">
        <div className="section-header">
          <div><p className="eyebrow">ADMIN</p><h2 style={{ margin: 0, fontSize: '1.5rem' }}>Harness Console</h2><p className="panel-subtitle">Observe LLM calls, agent run chains, replay snapshots, and eval results.</p></div>
        </div>
        <AdminTabs />
      </div></section>

      <section className="surface-panel"><div className="surface-panel__content" style={{ display: 'grid', gap: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {harnessTabs.map((tab) => (
              <button key={tab.key} type="button" style={{ padding: '8px 12px', border: `1px solid ${activeTab === tab.key ? 'rgba(86, 213, 255, 0.36)' : 'rgba(129, 160, 207, 0.14)'}`, borderRadius: 'var(--radius-sm)', background: activeTab === tab.key ? 'rgba(86, 213, 255, 0.08)' : 'rgba(10, 18, 32, 0.5)', color: activeTab === tab.key ? 'var(--color-text-primary)' : 'var(--color-text-secondary)', cursor: 'pointer', fontWeight: 600 }} onClick={() => setActiveTab(tab.key)}>{tab.label}</button>
            ))}
          </div>
          <button className="btn btn--ghost" disabled={loading} onClick={() => void loadCurrentTab()}>Reload</button>
        </div>
        <div style={{ padding: '12px 14px', border: '1px solid rgba(86, 213, 255, 0.18)', borderRadius: 'var(--radius-sm)', background: 'rgba(10, 18, 32, 0.42)', color: 'var(--color-text-secondary)' }}>
          <strong style={{ color: 'var(--color-text-primary)', fontSize: '0.95rem' }}>{activeHarnessTab.label}</strong>
          <p style={{ margin: '4px 0 0', lineHeight: 1.7, overflowWrap: 'anywhere' }}>{activeHarnessTab.description}</p>
        </div>
      </div></section>

      {noticeMessage && <p style={{ margin: 0, padding: '10px 14px', borderRadius: 'var(--radius-sm)', background: 'rgba(88, 214, 161, 0.12)', color: 'var(--color-positive)' }}>{noticeMessage}</p>}
      {errorMessage && <p style={{ margin: 0, padding: '10px 14px', borderRadius: 'var(--radius-sm)', background: 'rgba(255, 107, 122, 0.12)', color: 'var(--color-negative)' }}>{errorMessage}</p>}

      {activeTab === 'overview' && (
        <div style={{ display: 'grid', gap: 'var(--space-4)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--space-3)' }}>
            {overviewCards.map((card) => (
              <article key={card.label} className="surface-panel" style={{ display: 'grid', gap: 8, padding: 16 }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>{card.label}</span>
                <strong style={{ fontSize: '1.35rem' }}>{card.value}</strong>
              </article>
            ))}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 'var(--space-4)' }}>
            {[{ title: 'Recent LLM Calls', items: llmCalls.slice(0, 5), render: (item: LLMCallMetric) => <tr key={item.call_id} style={{ cursor: 'pointer' }}><td style={cellStyle}>{formatDateTime(item.created_at)}</td><td style={cellStyle}>{item.agent_name || '-'}</td><td style={cellStyle}>{item.model || '-'}</td><td style={cellStyle}>{formatNumber(item.total_tokens)}</td></tr> },
              { title: 'Recent Agent Runs', items: agentRuns.slice(0, 5), render: (item: AgentRunTraceListItem) => <tr key={item.run_id} style={{ cursor: 'pointer' }} onClick={() => void openRun(item)}><td style={cellStyle}>{formatDateTime(item.started_at)}</td><td style={cellStyle}>{item.agent_name || '-'}</td><td style={cellStyle}><span className={statusClass(item.final_status)} style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', fontWeight: 600 }}>{item.final_status || '-'}</span></td><td style={cellStyle}>{formatLatency(item.latency_ms)}</td></tr> },
              { title: 'Recent Eval Runs', items: evalRuns.slice(0, 5), render: (item: EvalRun) => <tr key={item.eval_run_id} style={{ cursor: 'pointer' }} onClick={() => void openEvalRun(item)}><td style={cellStyle}>{formatDateTime(item.started_at)}</td><td style={cellStyle}>{item.name || '-'}</td><td style={cellStyle}><span className={statusClass(item.status)} style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', fontWeight: 600 }}>{item.status || '-'}</span></td><td style={cellStyle}>{formatRate((item.summary?.pass_rate as number) ?? 0)}</td></tr> },
            ].map((section) => (
              <article key={section.title} className="surface-panel"><div className="surface-panel__content">
                <h3 className="panel-title">{section.title}</h3>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}><tbody>{section.items.length > 0 ? section.items.map((item) => section.render(item as LLMCallMetric & AgentRunTraceListItem & EvalRun)) : <tr><td style={cellStyle} colSpan={4}>No data</td></tr>}</tbody></table>
              </div></article>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'llm-calls' && <section className="surface-panel"><div className="surface-panel__content">
        <FilterRow>
          <input value={llmFilters.hours} onChange={(e) => setLlmFilters({ ...llmFilters, hours: Number(e.target.value) })} placeholder="hours" style={filterInput} type="number" />
          <input value={llmFilters.agent_name} onChange={(e) => setLlmFilters({ ...llmFilters, agent_name: e.target.value })} placeholder="agent_name" style={filterInput} />
          <input value={llmFilters.model} onChange={(e) => setLlmFilters({ ...llmFilters, model: e.target.value })} placeholder="model" style={filterInput} />
          <select value={llmFilters.ok} onChange={(e) => setLlmFilters({ ...llmFilters, ok: e.target.value })} style={filterInput}><option value="">all</option><option value="true">success</option><option value="false">failed</option></select>
          <button className="btn btn--accent btn--sm" onClick={() => void loadLlmCalls()}>Query</button>
        </FilterRow>
        <div style={{ overflowX: 'auto' }}><table style={{ width: '100%', minWidth: 1200, borderCollapse: 'collapse' }}>
          <thead><tr>{['Time', 'Agent', 'Model', 'Prompt', 'Tokens', 'Latency', 'Cost', 'Status', 'Error'].map((h) => <th key={h} style={thStyle}>{h}</th>)}</tr></thead>
          <tbody>{llmCalls.map((item) => <tr key={item.call_id} style={{ cursor: 'pointer' }}><td style={cellStyle}>{formatDateTime(item.created_at)}</td><td style={cellStyle}>{item.agent_name || '-'}</td><td style={cellStyle}>{item.model || '-'}</td><td style={cellStyle}>{item.prompt_key || '-'}</td><td style={cellStyle}>{formatNumber(item.total_tokens)}</td><td style={cellStyle}>{formatLatency(item.latency_ms)}</td><td style={cellStyle}>{formatCost(item.estimated_cost)}</td><td style={cellStyle}><span className={item.ok ? 'tag-positive' : 'tag-negative'} style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', fontWeight: 600 }}>{item.ok ? 'OK' : 'FAIL'}</span></td><td style={cellStyle}>{item.error_code || '-'}</td></tr>)}</tbody>
        </table></div>
        {!llmCalls.length && <div className="empty-state">No LLM calls</div>}
      </div></section>}

      {activeTab === 'agent-runs' && <section className="surface-panel"><div className="surface-panel__content">
        <FilterRow>
          <input value={runFilters.hours} onChange={(e) => setRunFilters({ ...runFilters, hours: Number(e.target.value) })} placeholder="hours" style={filterInput} type="number" />
          <input value={runFilters.agent_name} onChange={(e) => setRunFilters({ ...runFilters, agent_name: e.target.value })} placeholder="agent" style={filterInput} />
          <input value={runFilters.final_status} onChange={(e) => setRunFilters({ ...runFilters, final_status: e.target.value })} placeholder="status" style={filterInput} />
          <button className="btn btn--accent btn--sm" onClick={() => void loadAgentRuns()}>Query</button>
        </FilterRow>
        <div style={{ overflowX: 'auto' }}><table style={{ width: '100%', minWidth: 1100, borderCollapse: 'collapse' }}>
          <thead><tr>{['Time', 'Agent', 'Status', 'Latency', 'LLM', 'Tools', 'Tokens', 'Run ID'].map((h) => <th key={h} style={thStyle}>{h}</th>)}</tr></thead>
          <tbody>{agentRuns.map((item) => <tr key={item.run_id} style={{ cursor: 'pointer' }} onClick={() => void openRun(item)}><td style={cellStyle}>{formatDateTime(item.started_at)}</td><td style={cellStyle}>{item.agent_name || '-'}</td><td style={cellStyle}><span className={statusClass(item.final_status)} style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', fontWeight: 600 }}>{item.final_status || '-'}</span></td><td style={cellStyle}>{formatLatency(item.latency_ms)}</td><td style={cellStyle}>{item.llm_call_count ?? 0}</td><td style={cellStyle}>{item.tool_call_count ?? 0}</td><td style={cellStyle}>{formatNumber(item.total_tokens)}</td><td style={cellStyle}><code style={{ color: 'var(--color-accent)' }}>{item.run_id}</code></td></tr>)}</tbody>
        </table></div>
        {!agentRuns.length && <div className="empty-state">No agent runs</div>}
      </div></section>}

      {activeTab === 'replays' && <section className="surface-panel"><div className="surface-panel__content">
        <FilterRow>
          <input value={replayFilters.hours} onChange={(e) => setReplayFilters({ ...replayFilters, hours: Number(e.target.value) })} placeholder="hours" style={filterInput} type="number" />
          <input value={replayFilters.agent_name} onChange={(e) => setReplayFilters({ ...replayFilters, agent_name: e.target.value })} placeholder="agent" style={filterInput} />
          <button className="btn btn--accent btn--sm" onClick={() => void loadReplays()}>Query</button>
        </FilterRow>
        <div style={{ overflowX: 'auto' }}><table style={{ width: '100%', minWidth: 1000, borderCollapse: 'collapse' }}>
          <thead><tr>{['Time', 'Agent', 'Status', 'Run ID', 'Replay ID', 'Model'].map((h) => <th key={h} style={thStyle}>{h}</th>)}</tr></thead>
          <tbody>{replays.map((item) => <tr key={item.replay_id} style={{ cursor: 'pointer' }} onClick={() => void openReplay(item)}><td style={cellStyle}>{formatDateTime(item.created_at)}</td><td style={cellStyle}>{item.agent_name || '-'}</td><td style={cellStyle}><span className={statusClass(item.final_status)} style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', fontWeight: 600 }}>{item.final_status || '-'}</span></td><td style={cellStyle}><code style={{ color: 'var(--color-accent)' }}>{item.run_id || '-'}</code></td><td style={cellStyle}><code style={{ color: 'var(--color-accent)' }}>{item.replay_id}</code></td><td style={cellStyle}>{(item.model_config as Record<string, unknown>)?.model as string || '-'}</td></tr>)}</tbody>
        </table></div>
        {!replays.length && <div className="empty-state">No replay snapshots</div>}
      </div></section>}

      {activeTab === 'eval-cases' && <section className="surface-panel"><div className="surface-panel__content">
        <FilterRow>
          <input value={caseFilters.agent_name} onChange={(e) => setCaseFilters({ ...caseFilters, agent_name: e.target.value })} placeholder="agent" style={filterInput} />
          <input value={caseFilters.source} onChange={(e) => setCaseFilters({ ...caseFilters, source: e.target.value })} placeholder="source" style={filterInput} />
          <button className="btn btn--accent btn--sm" onClick={() => void loadEvalCases()}>Query</button>
          <button className="btn btn--ghost btn--sm" onClick={() => void seedCases()}>Seed Built-in Cases</button>
        </FilterRow>
        <div style={{ overflowX: 'auto' }}><table style={{ width: '100%', minWidth: 900, borderCollapse: 'collapse' }}>
          <thead><tr>{['Case ID', 'Agent', 'Title', 'Source', 'Tags', 'Created'].map((h) => <th key={h} style={thStyle}>{h}</th>)}</tr></thead>
          <tbody>{evalCases.map((item) => <tr key={item.case_id} style={{ cursor: 'pointer' }} onClick={() => void openEvalCase(item)}><td style={cellStyle}><code style={{ color: 'var(--color-accent)' }}>{item.case_id}</code></td><td style={cellStyle}>{item.agent_name || '-'}</td><td style={cellStyle}>{item.title || '-'}</td><td style={cellStyle}>{item.source || '-'}</td><td style={cellStyle}>{(item.tags ?? []).join(', ') || '-'}</td><td style={cellStyle}>{formatDateTime(item.created_at)}</td></tr>)}</tbody>
        </table></div>
        {!evalCases.length && <div className="empty-state">No eval cases</div>}
      </div></section>}

      {activeTab === 'eval-runs' && <section className="surface-panel"><div className="surface-panel__content">
        <FilterRow>
          <input value={evalRunFilters.hours} onChange={(e) => setEvalRunFilters({ ...evalRunFilters, hours: Number(e.target.value) })} placeholder="hours" style={filterInput} type="number" />
          <input value={evalRunFilters.agent_name} onChange={(e) => setEvalRunFilters({ ...evalRunFilters, agent_name: e.target.value })} placeholder="agent" style={filterInput} />
          <button className="btn btn--accent btn--sm" onClick={() => void loadEvalRuns()}>Query</button>
        </FilterRow>
        <div style={{ overflowX: 'auto' }}><table style={{ width: '100%', minWidth: 1000, borderCollapse: 'collapse' }}>
          <thead><tr>{['Time', 'Name', 'Agent', 'Status', 'Cases', 'Passed', 'Pass Rate', 'Run ID'].map((h) => <th key={h} style={thStyle}>{h}</th>)}</tr></thead>
          <tbody>{evalRuns.map((item) => <tr key={item.eval_run_id} style={{ cursor: 'pointer' }} onClick={() => void openEvalRun(item)}><td style={cellStyle}>{formatDateTime(item.started_at)}</td><td style={cellStyle}>{item.name || '-'}</td><td style={cellStyle}>{item.agent_name || '-'}</td><td style={cellStyle}><span className={statusClass(item.status)} style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', fontWeight: 600 }}>{item.status || '-'}</span></td><td style={cellStyle}>{(item.summary?.case_count as number) ?? '-'}</td><td style={cellStyle}>{(item.summary?.passed_count as number) ?? '-'}</td><td style={cellStyle}>{formatRate((item.summary?.pass_rate as number) ?? 0)}</td><td style={cellStyle}><code style={{ color: 'var(--color-accent)' }}>{item.eval_run_id}</code></td></tr>)}</tbody>
        </table></div>
        {!evalRuns.length && <div className="empty-state">No eval runs</div>}
      </div></section>}

      {/* Dialogs */}
      {selectedRun && <Dialog title="Agent Run Detail" onClose={() => setSelectedRun(null)}>
        <button className="btn btn--ghost btn--sm" onClick={() => void openReplayByRun(selectedRun.run_id)}>View Replay</button>
        <JsonBlock title="Basic Info" value={{ run_id: selectedRun.run_id, agent_name: selectedRun.agent_name, final_status: selectedRun.final_status, latency_ms: selectedRun.latency_ms }} />
        <JsonBlock title="LLM Calls" value={selectedRun.llm_calls} collapsed />
        <JsonBlock title="Tool Calls" value={selectedRun.tool_calls} collapsed />
        <JsonBlock title="Node Traces" value={selectedRun.node_traces} collapsed />
        <JsonBlock title="Metadata" value={selectedRun.metadata} collapsed />
      </Dialog>}

      {selectedReplay && <Dialog title="Replay Snapshot" onClose={() => { setSelectedReplay(null); setExportPackage(null) }}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button className="btn btn--ghost btn--sm" onClick={() => void exportReplay()}>Export</button>
          <button className="btn btn--ghost btn--sm" onClick={() => void createCaseFromReplay()}>Create Eval Case</button>
          <button className="btn btn--accent btn--sm" onClick={() => void runEvalForReplay()}>Run Static Eval</button>
        </div>
        <JsonBlock title="Request" value={selectedReplay.request} />
        <JsonBlock title="Context Snapshot" value={selectedReplay.context_snapshot} collapsed />
        <JsonBlock title="Tool Snapshots" value={selectedReplay.tool_snapshots} collapsed />
        <JsonBlock title="Final Output" value={selectedReplay.final_output} />
        {exportPackage && <JsonBlock title="Export Package" value={exportPackage} collapsed />}
      </Dialog>}

      {selectedEvalCase && <Dialog title="Eval Case" onClose={() => setSelectedEvalCase(null)}>
        <button className="btn btn--accent btn--sm" onClick={() => void runEvalForCase(selectedEvalCase.case_id)}>Run Static Eval</button>
        <JsonBlock title="Input" value={selectedEvalCase.input} />
        <JsonBlock title="Expected Behavior" value={selectedEvalCase.expected_behavior} collapsed />
        <JsonBlock title="Scoring Rubric" value={selectedEvalCase.scoring_rubric} collapsed />
      </Dialog>}

      {selectedEvalRun && <Dialog title="Eval Run" onClose={() => setSelectedEvalRun(null)}>
        <JsonBlock title="Summary" value={selectedEvalRun.summary} />
        {selectedEvalRun.results && <div style={{ overflowX: 'auto' }}><table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead><tr>{['Case', 'Agent', 'Status', 'Score', 'Error'].map((h) => <th key={h} style={thStyle}>{h}</th>)}</tr></thead>
          <tbody>{selectedEvalRun.results.map((r) => <tr key={`${r.case_id}-${r.replay_id}`}><td style={cellStyle}><code style={{ color: 'var(--color-accent)' }}>{r.case_id}</code></td><td style={cellStyle}>{r.agent_name || '-'}</td><td style={cellStyle}><span className={statusClass(r.status)} style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', fontWeight: 600 }}>{r.status || '-'}</span></td><td style={cellStyle}>{r.score ?? 0}/{r.max_score ?? 0}</td><td style={cellStyle}>{r.error_code || '-'}</td></tr>)}</tbody>
        </table></div>}
      </Dialog>}
    </section>
  )
}

function FilterRow({ children }: { children: React.ReactNode }) {
  return <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center', marginBottom: 'var(--space-4)' }}>{children}</div>
}

function Dialog({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="admin-dialog-backdrop" onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <section className="surface-panel admin-dialog" style={{ width: 'min(980px, calc(100vw - 32px))', maxHeight: '85vh', overflow: 'auto' }}>
        <div className="surface-panel__content" style={{ display: 'grid', gap: 12 }}>
          <div className="section-header"><h3 className="panel-title">{title}</h3><button className="btn btn--ghost" onClick={onClose}>X</button></div>
          {children}
        </div>
      </section>
    </div>
  )
}

const filterInput: React.CSSProperties = { minHeight: 38, maxWidth: 180, border: '1px solid rgba(129, 160, 207, 0.18)', borderRadius: 'var(--radius-sm)', background: 'rgba(10, 18, 32, 0.72)', color: 'var(--color-text-primary)', padding: '0 10px' }
