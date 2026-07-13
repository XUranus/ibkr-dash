import { useState, useEffect, useCallback, useMemo } from 'react'
import { getEvalCoverage } from '@/api/adminHarness'
import type { EvalCaseCoverageRow, EvalCoverageResponse } from '@/types/adminHarness'

interface EvalCoverageMatrixPanelProps {
  onOpenCase?: (caseId: string) => void
  onOpenRun?: (runId: string) => void
  onFilterAgent?: (agentName: string) => void
  onFilterNode?: (agentName: string, nodeName: string) => void
}

const SUMMARY_CARDS = [
  { key: 'case_count', label: 'Case 总数' },
  { key: 'enabled_case_count', label: 'Enabled Case' },
  { key: 'disabled_case_count', label: 'Disabled Case' },
  { key: 'agent_count', label: 'Agent 数' },
  { key: 'judge_case_count', label: 'Judge Case' },
  { key: 'replay_source_count', label: 'Replay 来源' },
  { key: 'manual_source_count', label: 'Manual 来源' },
  { key: 'bad_case_source_count', label: 'Bad Case 来源' },
  { key: 'recent_eval_run_count', label: '最近 Eval Run' },
  { key: 'recent_evaluated_case_count', label: '最近被评测 Case' },
  { key: 'never_evaluated_case_count', label: '统计窗口内未运行 Case' },
] as const

interface NodeCoverageRow {
  agent_name: string
  node_name: string
  case_count: number
  enabled_case_count: number
  judge_case_count: number
  recent_pass_rate: number | null
  recent_failed_count: number
  never_evaluated_case_count: number
}

function formatRate(value?: number | null): string {
  if (value === null || value === undefined) return '-'
  return `${(value * 100).toFixed(1)}%`
}

function severityClass(severity?: string | null): string {
  if (severity === 'critical') return 'tag--danger'
  if (severity === 'high') return 'tag--warning'
  if (severity === 'low') return 'tag--info'
  return ''
}

function rowScopeTagClass(scope?: string | null): string {
  return scope === 'node' ? 'tag--info' : ''
}

function rowScopeLabel(scope?: string | null): string {
  return scope === 'node' ? 'NODE' : 'AGENT'
}

function gapNodeName(gap: { metadata?: Record<string, unknown> }): string {
  const fromMeta = gap.metadata?.node_name
  return fromMeta ? String(fromMeta) : '-'
}

function recNodeName(rec: { metadata?: Record<string, unknown> }): string {
  const fromMeta = rec.metadata?.node_name
  return fromMeta ? String(fromMeta) : '-'
}

export default function EvalCoverageMatrixPanel({ onOpenCase, onOpenRun, onFilterAgent, onFilterNode }: EvalCoverageMatrixPanelProps) {
  const [coverage, setCoverage] = useState<EvalCoverageResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [filters, setFilters] = useState({
    agent_name: '',
    hours: 720,
    limit: 1000,
    include_disabled: true,
  })

  const load = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      const data = await getEvalCoverage(filters)
      setCoverage(data)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '加载覆盖矩阵失败')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    void load()
  }, [load])

  const nodeCoverageRows = useMemo<NodeCoverageRow[]>(() => {
    if (!coverage) return []
    const rows = coverage.case_coverage ?? []
    const buckets = new Map<string, NodeCoverageRow>()
    for (const row of rows) {
      if (row.eval_scope !== 'node') continue
      const agent = row.agent_name || 'unknown'
      const node = row.node_name || '(unnamed)'
      const key = `${agent}::${node}`
      let bucket = buckets.get(key)
      if (!bucket) {
        bucket = {
          agent_name: agent,
          node_name: node,
          case_count: 0,
          enabled_case_count: 0,
          judge_case_count: 0,
          recent_pass_rate: null,
          recent_failed_count: 0,
          never_evaluated_case_count: 0,
        }
        buckets.set(key, bucket)
      }
      bucket.case_count += 1
      if (row.enabled !== false) bucket.enabled_case_count += 1
      if (row.judge_enabled) bucket.judge_case_count += 1
      if (row.never_evaluated) bucket.never_evaluated_case_count += 1
      const runs = row.recent_run_count ?? 0
      const passes = row.recent_pass_count ?? 0
      if (runs > 0) {
        const existing = bucket.recent_pass_rate ?? 0
        const existingCount = bucket.case_count - 1
        const totalRuns = (bucket.recent_pass_rate !== null ? existing * Math.max(1, existingCount) : 0) + runs
        const totalPasses = (bucket.recent_pass_rate !== null ? existing * Math.max(1, existingCount) : 0) + passes
        bucket.recent_pass_rate = totalRuns > 0 ? totalPasses / totalRuns : null
      }
      bucket.recent_failed_count += row.recent_failed_count ?? 0
    }
    return Array.from(buckets.values()).sort(
      (a, b) => a.agent_name.localeCompare(b.agent_name) || a.node_name.localeCompare(b.node_name),
    )
  }, [coverage])

  function updateFilter(key: string, value: unknown) {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }

  const thStyle: React.CSSProperties = {
    color: 'var(--text-color-secondary, #aaa)',
    fontSize: '0.75rem',
    textTransform: 'uppercase',
    padding: '10px 12px',
    borderBottom: '1px solid rgba(129,160,207,0.1)',
    textAlign: 'left',
  }

  const tdStyle: React.CSSProperties = {
    padding: '10px 12px',
    borderBottom: '1px solid rgba(129,160,207,0.1)',
    textAlign: 'left',
    fontSize: '0.82rem',
  }

  const clickableStyle: React.CSSProperties = {
    cursor: 'pointer',
    color: 'var(--color-accent, #59c9a5)',
  }

  return (
    <div style={{ display: 'grid', gap: 'var(--space-4)' }}>
      {/* Filters */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'flex-end' }}>
        <label style={labelStyle}>
          Agent
          <input value={filters.agent_name} onChange={(e) => updateFilter('agent_name', e.target.value)} placeholder="全部 Agent" style={inputStyle} />
        </label>
        <label style={labelStyle}>
          Hours
          <input type="number" value={filters.hours} onChange={(e) => updateFilter('hours', Number(e.target.value))} min={1} max={8760} style={{ ...inputStyle, width: '5rem' }} />
        </label>
        <label style={labelStyle}>
          Limit
          <input type="number" value={filters.limit} onChange={(e) => updateFilter('limit', Number(e.target.value))} min={1} max={5000} style={{ ...inputStyle, width: '5rem' }} />
        </label>
        <label style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--text-color-secondary, #aaa)' }}>
          <input type="checkbox" checked={filters.include_disabled} onChange={(e) => updateFilter('include_disabled', e.target.checked)} />
          包含禁用 Case
        </label>
        <button className="btn btn--primary" disabled={loading} onClick={() => void load()}>
          {loading ? '加载中...' : '刷新覆盖矩阵'}
        </button>
      </div>

      {errorMessage && <p style={{ color: '#f87171', fontSize: '0.85rem' }}>{errorMessage}</p>}

      {coverage ? (
        <>
          {/* Summary Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12 }}>
            {SUMMARY_CARDS.map((card) => (
              <article key={card.key} style={{ padding: 14, border: '1px solid rgba(129,160,207,0.12)', borderRadius: 'var(--radius-md, 8px)', background: 'rgba(10,18,32,0.46)', display: 'grid', gap: 4 }}>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-color-secondary, #aaa)' }}>{card.label}</span>
                <strong style={{ fontSize: '1.1rem' }}>{coverage.summary[card.key] ?? '-'}</strong>
              </article>
            ))}
          </div>

          {/* Agent Overview */}
          <section style={{ display: 'grid', gap: 10 }}>
            <h4 style={{ margin: 0, fontSize: '1rem' }}>Agent 覆盖总览</h4>
            <div className="table-shell">
              <table style={{ width: '100%', minWidth: 900, borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={thStyle}>agent_name</th><th style={thStyle}>case_count</th><th style={thStyle}>enabled</th>
                    <th style={thStyle}>judge</th><th style={thStyle}>high</th><th style={thStyle}>critical</th>
                    <th style={thStyle}>eval_runs</th><th style={thStyle}>pass_rate</th><th style={thStyle}>failed</th>
                    <th style={thStyle}>errors</th><th style={thStyle}>high_crit_fail</th><th style={thStyle}>未运行</th>
                  </tr>
                </thead>
                <tbody>
                  {(coverage.by_agent as Array<Record<string, unknown>>).map((row, i) => (
                    <tr key={String(row.agent_name ?? i)}>
                      <td style={tdStyle}><code style={clickableStyle} onClick={() => onFilterAgent?.(String(row.agent_name))}>{String(row.agent_name)}</code></td>
                      <td style={tdStyle}>{row.case_count != null ? String(row.case_count) : '-'}</td>
                      <td style={tdStyle}>{row.enabled_case_count != null ? String(row.enabled_case_count) : '-'}</td>
                      <td style={tdStyle}>{row.judge_case_count != null ? String(row.judge_case_count) : '-'}</td>
                      <td style={tdStyle}>{row.high_case_count != null ? String(row.high_case_count) : '-'}</td>
                      <td style={tdStyle}>{row.critical_case_count != null ? String(row.critical_case_count) : '-'}</td>
                      <td style={tdStyle}>{row.recent_eval_run_count != null ? String(row.recent_eval_run_count) : '-'}</td>
                      <td style={tdStyle}>{formatRate(row.recent_pass_rate as number | undefined)}</td>
                      <td style={tdStyle}>{row.recent_failed_count != null ? String(row.recent_failed_count) : '-'}</td>
                      <td style={tdStyle}>{row.recent_error_count != null ? String(row.recent_error_count) : '-'}</td>
                      <td style={{ ...tdStyle, color: ((row.high_critical_failure_count as number) ?? 0) > 0 ? '#f87171' : undefined, fontWeight: ((row.high_critical_failure_count as number) ?? 0) > 0 ? 600 : undefined }}>
                        {row.high_critical_failure_count != null ? String(row.high_critical_failure_count) : '-'}
                      </td>
                      <td style={{ ...tdStyle, color: ((row.never_evaluated_case_count as number) ?? 0) > 0 ? '#fbbf24' : undefined, fontWeight: ((row.never_evaluated_case_count as number) ?? 0) > 0 ? 600 : undefined }}>
                        {row.never_evaluated_case_count != null ? String(row.never_evaluated_case_count) : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!coverage.by_agent.length && <div style={emptyStateStyle}>暂无数据</div>}
          </section>

          {/* Agent x Category */}
          <section style={{ display: 'grid', gap: 10 }}>
            <h4 style={{ margin: 0, fontSize: '1rem' }}>Agent x Category</h4>
            <div className="table-shell">
              <table style={{ width: '100%', minWidth: 900, borderCollapse: 'collapse' }}>
                <thead>
                  <tr><th style={thStyle}>agent</th><th style={thStyle}>category</th><th style={thStyle}>cases</th><th style={thStyle}>enabled</th><th style={thStyle}>high</th><th style={thStyle}>critical</th><th style={thStyle}>pass_rate</th><th style={thStyle}>failed</th></tr>
                </thead>
                <tbody>
                  {(coverage.by_agent_category as Array<Record<string, unknown>>).map((row, i) => (
                    <tr key={`${row.agent_name}-${row.category}-${i}`}>
                      <td style={tdStyle}>{String(row.agent_name ?? '')}</td><td style={tdStyle}>{String(row.category ?? '')}</td>
                      <td style={tdStyle}>{row.case_count != null ? String(row.case_count) : '-'}</td><td style={tdStyle}>{row.enabled_case_count != null ? String(row.enabled_case_count) : '-'}</td>
                      <td style={tdStyle}>{row.high_case_count != null ? String(row.high_case_count) : '-'}</td><td style={tdStyle}>{row.critical_case_count != null ? String(row.critical_case_count) : '-'}</td>
                      <td style={tdStyle}>{formatRate(row.recent_pass_rate as number | undefined)}</td><td style={tdStyle}>{row.recent_failed_count != null ? String(row.recent_failed_count) : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!coverage.by_agent_category.length && <div style={emptyStateStyle}>暂无数据</div>}
          </section>

          {/* Agent x Severity */}
          <section style={{ display: 'grid', gap: 10 }}>
            <h4 style={{ margin: 0, fontSize: '1rem' }}>Agent x Severity</h4>
            <div className="table-shell">
              <table style={{ width: '100%', minWidth: 900, borderCollapse: 'collapse' }}>
                <thead>
                  <tr><th style={thStyle}>agent</th><th style={thStyle}>severity</th><th style={thStyle}>cases</th><th style={thStyle}>enabled</th><th style={thStyle}>pass_rate</th><th style={thStyle}>failed</th></tr>
                </thead>
                <tbody>
                  {(coverage.by_agent_severity as Array<Record<string, unknown>>).map((row, i) => (
                    <tr key={`${row.agent_name}-${row.severity}-${i}`}>
                      <td style={tdStyle}>{String(row.agent_name ?? '')}</td>
                      <td style={tdStyle}><span className={`tag ${severityClass(row.severity as string)}`}>{String(row.severity ?? '')}</span></td>
                      <td style={tdStyle}>{row.case_count != null ? String(row.case_count) : '-'}</td><td style={tdStyle}>{row.enabled_case_count != null ? String(row.enabled_case_count) : '-'}</td>
                      <td style={tdStyle}>{formatRate(row.recent_pass_rate as number | undefined)}</td><td style={tdStyle}>{row.recent_failed_count != null ? String(row.recent_failed_count) : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!coverage.by_agent_severity.length && <div style={emptyStateStyle}>暂无数据</div>}
          </section>

          {/* Agent x Tag */}
          <section style={{ display: 'grid', gap: 10 }}>
            <h4 style={{ margin: 0, fontSize: '1rem' }}>Agent x Tag</h4>
            <div className="table-shell">
              <table style={{ width: '100%', minWidth: 900, borderCollapse: 'collapse' }}>
                <thead>
                  <tr><th style={thStyle}>agent</th><th style={thStyle}>tag</th><th style={thStyle}>cases</th><th style={thStyle}>enabled</th><th style={thStyle}>pass_rate</th></tr>
                </thead>
                <tbody>
                  {(coverage.by_agent_tag as Array<Record<string, unknown>>).map((row, i) => (
                    <tr key={`${row.agent_name}-${row.tag}-${i}`}>
                      <td style={tdStyle}>{String(row.agent_name ?? '')}</td><td style={tdStyle}>{String(row.tag ?? '')}</td>
                      <td style={tdStyle}>{row.case_count != null ? String(row.case_count) : '-'}</td><td style={tdStyle}>{row.enabled_case_count != null ? String(row.enabled_case_count) : '-'}</td>
                      <td style={tdStyle}>{formatRate(row.recent_pass_rate as number | undefined)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!coverage.by_agent_tag.length && <div style={emptyStateStyle}>暂无数据</div>}
          </section>

          {/* Case Source Distribution */}
          <section style={{ display: 'grid', gap: 10 }}>
            <h4 style={{ margin: 0, fontSize: '1rem' }}>Case 来源分布</h4>
            <div className="table-shell">
              <table style={{ width: '100%', minWidth: 900, borderCollapse: 'collapse' }}>
                <thead>
                  <tr><th style={thStyle}>source</th><th style={thStyle}>cases</th><th style={thStyle}>enabled</th></tr>
                </thead>
                <tbody>
                  {(coverage.by_source as Array<Record<string, unknown>>).map((row, i) => (
                    <tr key={String(row.source ?? i)}>
                      <td style={tdStyle}>{String(row.source ?? '')}</td><td style={tdStyle}>{row.case_count != null ? String(row.case_count) : '-'}</td><td style={tdStyle}>{row.enabled_case_count != null ? String(row.enabled_case_count) : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!coverage.by_source.length && <div style={emptyStateStyle}>暂无数据</div>}
          </section>

          {/* Case Coverage Detail */}
          <section style={{ display: 'grid', gap: 10 }}>
            <h4 style={{ margin: 0, fontSize: '1rem' }}>Case 覆盖明细</h4>
            <div className="table-shell">
              <table style={{ width: '100%', minWidth: 900, borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={thStyle}>case_id</th><th style={thStyle}>agent</th><th style={thStyle}>scope</th><th style={thStyle}>node_name</th>
                    <th style={thStyle}>title</th><th style={thStyle}>enabled</th>
                    <th style={thStyle}>severity</th><th style={thStyle}>category</th><th style={thStyle}>tags</th><th style={thStyle}>source</th>
                    <th style={thStyle}>prompt_key</th><th style={thStyle}>model</th>
                    <th style={thStyle}>judge</th><th style={thStyle}>last_status</th><th style={thStyle}>score</th>
                    <th style={thStyle}>evaluated_at</th><th style={thStyle}>runs</th><th style={thStyle}>failed</th><th style={thStyle}>未运行</th>
                  </tr>
                </thead>
                <tbody>
                  {coverage.case_coverage.map((row) => (
                    <tr key={row.case_id}>
                      <td style={tdStyle}><code style={clickableStyle} onClick={() => onOpenCase?.(row.case_id)}>{row.case_id}</code></td>
                      <td style={tdStyle}>{row.agent_name || '-'}</td>
                      <td style={tdStyle}><span className={`tag ${rowScopeTagClass(row.eval_scope)}`}>{rowScopeLabel(row.eval_scope)}</span></td>
                      <td style={tdStyle}>{row.node_name || '-'}</td>
                      <td style={tdStyle}>{row.title || '-'}</td>
                      <td style={tdStyle}><span className={`tag ${row.enabled === false ? 'tag--warning' : 'tag--positive'}`}>{row.enabled === false ? '禁用' : '启用'}</span></td>
                      <td style={tdStyle}><span className={`tag ${severityClass(row.severity)}`}>{row.severity || '-'}</span></td>
                      <td style={tdStyle}>{row.category || '-'}</td>
                      <td style={tdStyle}>{(row.tags || []).join(', ') || '-'}</td>
                      <td style={tdStyle}>{row.source || '-'}</td>
                      <td style={tdStyle}>{row.prompt_key || '-'}</td>
                      <td style={tdStyle}>{row.model || '-'}</td>
                      <td style={tdStyle}>{row.judge_enabled ? <span className="tag tag--info">LLM Judge</span> : '-'}</td>
                      <td style={tdStyle}>
                        {row.last_eval_run_id ? (
                          <code style={clickableStyle} onClick={() => onOpenRun?.(row.last_eval_run_id!)}>{row.last_status || '-'}</code>
                        ) : (
                          row.last_status || '-'
                        )}
                      </td>
                      <td style={tdStyle}>{row.last_score != null ? `${row.last_score}/${row.last_max_score ?? '-'}` : '-'}</td>
                      <td style={tdStyle}>{row.last_evaluated_at || '-'}</td>
                      <td style={tdStyle}>{row.recent_run_count ?? 0}</td>
                      <td style={tdStyle}>{row.recent_failed_count ?? 0}</td>
                      <td style={tdStyle}>{row.never_evaluated ? <span className="tag tag--warning">统计窗口内未运行</span> : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!coverage.case_coverage.length && <div style={emptyStateStyle}>暂无数据</div>}
          </section>

          {/* Node Coverage */}
          <section style={{ display: 'grid', gap: 10 }}>
            <h4 style={{ margin: 0, fontSize: '1rem' }}>Node Coverage</h4>
            <div className="table-shell">
              <table style={{ width: '100%', minWidth: 900, borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={thStyle}>agent_name</th><th style={thStyle}>node_name</th><th style={thStyle}>case_count</th>
                    <th style={thStyle}>enabled_case_count</th><th style={thStyle}>judge_case_count</th>
                    <th style={thStyle}>recent_pass_rate</th><th style={thStyle}>recent_failed_count</th><th style={thStyle}>never_evaluated_case_count</th>
                  </tr>
                </thead>
                <tbody>
                  {nodeCoverageRows.map((row) => (
                    <tr key={`${row.agent_name}-${row.node_name}`}>
                      <td style={tdStyle}><code style={clickableStyle} onClick={() => onFilterAgent?.(row.agent_name)}>{row.agent_name}</code></td>
                      <td style={tdStyle}><code style={clickableStyle} onClick={() => onFilterNode?.(row.agent_name, row.node_name)}>{row.node_name}</code></td>
                      <td style={tdStyle}>{row.case_count}</td>
                      <td style={tdStyle}>{row.enabled_case_count}</td>
                      <td style={tdStyle}>{row.judge_case_count}</td>
                      <td style={tdStyle}>{formatRate(row.recent_pass_rate)}</td>
                      <td style={tdStyle}>{row.recent_failed_count}</td>
                      <td style={tdStyle}>{row.never_evaluated_case_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!nodeCoverageRows.length && <div style={emptyStateStyle}>暂无 Node Eval 覆盖数据</div>}
          </section>

          {/* Coverage Gaps */}
          <section style={{ display: 'grid', gap: 10 }}>
            <h4 style={{ margin: 0, fontSize: '1rem' }}>Coverage Gaps</h4>
            <div className="table-shell">
              <table style={{ width: '100%', minWidth: 900, borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={thStyle}>gap_id</th><th style={thStyle}>agent</th><th style={thStyle}>node_name</th><th style={thStyle}>gap_type</th><th style={thStyle}>severity</th>
                    <th style={thStyle}>category</th><th style={thStyle}>title</th><th style={thStyle}>description</th><th style={thStyle}>suggested_action</th>
                  </tr>
                </thead>
                <tbody>
                  {coverage.gaps.map((gap) => (
                    <tr key={gap.gap_id}>
                      <td style={tdStyle}><code>{gap.gap_id}</code></td>
                      <td style={tdStyle}><code style={clickableStyle} onClick={() => onFilterAgent?.(gap.agent_name)}>{gap.agent_name}</code></td>
                      <td style={tdStyle}>{gapNodeName(gap as unknown as { metadata?: Record<string, unknown> })}</td>
                      <td style={tdStyle}><code>{gap.gap_type}</code></td>
                      <td style={tdStyle}><span className={`tag ${severityClass(gap.severity)}`}>{gap.severity}</span></td>
                      <td style={tdStyle}>{gap.category}</td>
                      <td style={tdStyle}>{gap.title}</td>
                      <td style={tdStyle}>{gap.description}</td>
                      <td style={tdStyle}>{gap.suggested_action}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!coverage.gaps.length && <div style={emptyStateStyle}>暂无覆盖缺口</div>}
          </section>

          {/* Recommendations */}
          <section style={{ display: 'grid', gap: 10 }}>
            <h4 style={{ margin: 0, fontSize: '1rem' }}>Recommendations</h4>
            <div className="table-shell">
              <table style={{ width: '100%', minWidth: 900, borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={thStyle}>recommendation_id</th><th style={thStyle}>agent</th><th style={thStyle}>node_name</th><th style={thStyle}>priority</th>
                    <th style={thStyle}>action_type</th><th style={thStyle}>title</th><th style={thStyle}>description</th>
                  </tr>
                </thead>
                <tbody>
                  {coverage.recommendations.map((rec) => (
                    <tr key={rec.recommendation_id}>
                      <td style={tdStyle}><code>{rec.recommendation_id}</code></td>
                      <td style={tdStyle}><code style={clickableStyle} onClick={() => onFilterAgent?.(rec.agent_name)}>{rec.agent_name}</code></td>
                      <td style={tdStyle}>{recNodeName(rec as unknown as { metadata?: Record<string, unknown> })}</td>
                      <td style={tdStyle}><span className={`tag ${severityClass(rec.priority)}`}>{rec.priority}</span></td>
                      <td style={tdStyle}><code>{rec.action_type}</code></td>
                      <td style={tdStyle}>{rec.title}</td>
                      <td style={tdStyle}>{rec.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!coverage.recommendations.length && <div style={emptyStateStyle}>暂无建议</div>}
          </section>
        </>
      ) : !loading && !errorMessage ? (
        <div style={emptyStateStyle}>暂无覆盖数据，点击&ldquo;刷新覆盖矩阵&rdquo;加载。</div>
      ) : null}
    </div>
  )
}

const labelStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '0.2rem',
  fontSize: '0.8rem',
  color: 'var(--text-color-secondary, #aaa)',
}

const inputStyle: React.CSSProperties = {
  padding: '0.35rem 0.5rem',
  border: '1px solid var(--surface-border, #444)',
  borderRadius: 4,
  background: 'var(--surface-ground, #111)',
  color: 'var(--text-color, #eee)',
  fontSize: '0.85rem',
}

const emptyStateStyle: React.CSSProperties = {
  padding: '28px',
  border: '1px dashed rgba(129,160,207,0.18)',
  borderRadius: 'var(--radius-md)',
  color: 'var(--color-text-secondary)',
  textAlign: 'center',
}
