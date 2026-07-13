import { useState } from 'react'
import JsonBlock from '@/components/admin/JsonBlock'
import {
  analyzeImpactChangedFiles,
  analyzeImpactGitDiff,
  regressionGateDryRun,
  runAgentRegressionEval,
} from '@/api/adminHarness'
import type { RegressionGateResult } from '@/types/adminHarness'
import type { AgentRegressionRunPayload, AgentRegressionRunResponse, ImpactAnalysisResult } from '@/types/adminHarness'

export default function ImpactAnalysisPanel() {
  const [changedFilesInput, setChangedFilesInput] = useState('')
  const [baseRef, setBaseRef] = useState('origin/main')
  const [headRef, setHeadRef] = useState('HEAD')
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [noticeMessage, setNoticeMessage] = useState('')
  const [result, setResult] = useState<ImpactAnalysisResult | null>(null)
  const [expandedPayloads, setExpandedPayloads] = useState<Set<string>>(new Set())

  const [regressionRunning, setRegressionRunning] = useState('')
  const [regressionResults, setRegressionResults] = useState<Map<string, AgentRegressionRunResponse>>(new Map())
  const [gateDryRunLoading, setGateDryRunLoading] = useState(false)
  const [gateDryRunResult, setGateDryRunResult] = useState<RegressionGateResult | null>(null)

  function togglePayload(agentName: string) {
    setExpandedPayloads((prev) => {
      const next = new Set(prev)
      if (next.has(agentName)) {
        next.delete(agentName)
      } else {
        next.add(agentName)
      }
      return next
    })
  }

  async function analyzeChangedFiles() {
    const files = changedFilesInput.split('\n').map((l) => l.trim()).filter(Boolean)
    if (!files.length) {
      setErrorMessage('请输入至少一个 changed file')
      return
    }
    setLoading(true)
    setErrorMessage('')
    setNoticeMessage('')
    setResult(null)
    try {
      const data = await analyzeImpactChangedFiles({
        changed_files: files,
        base_ref: baseRef || undefined,
        head_ref: headRef || undefined,
      })
      setResult(data)
      setNoticeMessage(`分析完成：${data.summary.impacted_agent_count} 个 Agent 受影响，${data.summary.recommended_run_count} 个建议运行回归`)
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  async function analyzeGitDiff() {
    if (!baseRef || !headRef) {
      setErrorMessage('请输入 base_ref 和 head_ref')
      return
    }
    setLoading(true)
    setErrorMessage('')
    setNoticeMessage('')
    setResult(null)
    try {
      const data = await analyzeImpactGitDiff({ base_ref: baseRef, head_ref: headRef })
      setResult(data)
      setNoticeMessage(`分析完成：${data.summary.impacted_agent_count} 个 Agent 受影响，${data.summary.recommended_run_count} 个建议运行回归`)
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  async function runRegression(agentName: string, payload: Record<string, unknown>) {
    const confirmMsg = `确认运行 ${agentName} 的回归评测？\n\n本次回归基于代码变更影响分析结果。`
    if (!window.confirm(confirmMsg)) return

    setRegressionRunning(agentName)
    setRegressionResults((prev) => {
      const next = new Map(prev)
      next.delete(agentName)
      return next
    })
    try {
      const runPayload = payload as unknown as AgentRegressionRunPayload
      const runResult = await runAgentRegressionEval(runPayload)
      setRegressionResults((prev) => {
        const next = new Map(prev)
        next.set(agentName, runResult)
        return next
      })
      if (runResult.gate_result?.passed) {
        setNoticeMessage(`${agentName} 回归评测通过。Eval Run: ${runResult.eval_run.eval_run_id}`)
      } else {
        setNoticeMessage(`${agentName} 回归评测未通过。Eval Run: ${runResult.eval_run.eval_run_id}`)
      }
    } catch (err: unknown) {
      setErrorMessage(`${agentName} 回归评测运行失败：${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setRegressionRunning('')
    }
  }

  async function runGateDryRun() {
    const files = changedFilesInput.split('\n').map((l) => l.trim()).filter(Boolean)
    if (!files.length && !(baseRef && headRef)) {
      setErrorMessage('请输入 changed files 或 base_ref + head_ref')
      return
    }
    setGateDryRunLoading(true)
    setGateDryRunResult(null)
    setErrorMessage('')
    setNoticeMessage('')
    try {
      const data = await regressionGateDryRun({
        changed_files: files.length ? files : undefined,
        base_ref: baseRef || undefined,
        head_ref: headRef || undefined,
      })
      setGateDryRunResult(data)
      const summary = data.summary
      if (summary.recommended_run_count === 0) {
        setNoticeMessage('无需回归，Gate 将通过')
      } else {
        setNoticeMessage(`Gate Dry Run：${summary.recommended_run_count} 个 Agent 需要运行回归`)
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : String(err))
    } finally {
      setGateDryRunLoading(false)
    }
  }

  return (
    <div style={{ display: 'grid', gap: 'var(--space-4)' }}>
      <div style={{ display: 'grid', gap: '0.75rem' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', flex: 1, fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
            Changed Files（一行一个）
            <textarea
              value={changedFilesInput}
              onChange={(e) => setChangedFilesInput(e.target.value)}
              rows={4}
              placeholder={'ibkr_show_backend/app/agents/trade_decision_graph/nodes.py\nibkr_show_backend/app/prompts/trade_decision/risk_control.md'}
              style={{ width: '100%', minHeight: 80, padding: '0.5rem', border: '1px solid var(--surface-border, #444)', borderRadius: 4, background: 'var(--surface-ground, #111)', color: 'var(--text-color, #eee)', fontSize: '0.85rem', fontFamily: 'monospace', resize: 'vertical' }}
            />
          </label>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', minWidth: 180, fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
            Base Ref
            <input value={baseRef} onChange={(e) => setBaseRef(e.target.value)} placeholder="origin/main" style={inputStyle} />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', minWidth: 180, fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
            Head Ref
            <input value={headRef} onChange={(e) => setHeadRef(e.target.value)} placeholder="HEAD" style={inputStyle} />
          </label>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn--primary" disabled={loading} onClick={() => void analyzeChangedFiles()}>
            {loading ? '分析中...' : '分析 Changed Files'}
          </button>
          <button className="btn btn--secondary" disabled={loading} onClick={() => void analyzeGitDiff()}>
            {loading ? '分析中...' : '分析 Git Diff'}
          </button>
          <button className="btn btn--secondary" disabled={gateDryRunLoading} onClick={() => void runGateDryRun()}>
            {gateDryRunLoading ? '运行中...' : '部署 Gate Dry Run'}
          </button>
        </div>
      </div>

      {noticeMessage && (
        <p style={{ margin: 0, padding: '8px 12px', borderRadius: 'var(--radius-sm)', background: 'rgba(88,214,161,0.12)', color: 'var(--color-positive)', fontSize: '0.85rem' }}>{noticeMessage}</p>
      )}
      {errorMessage && (
        <p style={{ margin: 0, padding: '8px 12px', borderRadius: 'var(--radius-sm)', background: 'rgba(255,107,122,0.12)', color: 'var(--color-negative)', fontSize: '0.85rem' }}>{errorMessage}</p>
      )}

      {result && (
        <div style={{ display: 'grid', gap: 'var(--space-4)' }}>
          {/* Summary Cards */}
          <div style={summaryGridStyle}>
            <article style={cardStyle}>
              <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>Changed Files</span>
              <strong style={{ fontSize: '1.2rem' }}>{result.summary.changed_file_count}</strong>
            </article>
            <article style={cardStyle}>
              <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>Impacted Agents</span>
              <strong style={{ fontSize: '1.2rem' }}>{result.summary.impacted_agent_count}</strong>
            </article>
            <article style={cardStyle}>
              <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>Recommended Runs</span>
              <strong style={{ fontSize: '1.2rem' }}>{result.summary.recommended_run_count}</strong>
            </article>
          </div>

          {/* Impacted Agents Table */}
          {result.impacted_agents.length > 0 && (
            <div>
              <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.95rem' }}>Impacted Agents</h4>
              <div className="table-shell">
                <table className="harness-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      <th>Agent</th><th>Confidence</th><th>Recommended</th><th>Profile</th>
                      <th>on_code_change</th><th>Nodes</th><th>Reason</th><th>Payload</th><th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.impacted_agents.map((agent) => (
                      <tr key={agent.agent_name}>
                        <td><code>{agent.agent_name}</code></td>
                        <td><span className={`tag ${agent.confidence === 'high' ? 'tag--positive' : 'tag--accent'}`}>{agent.confidence}</span></td>
                        <td><span className={`tag ${agent.recommended ? 'tag--positive' : ''}`}>{agent.recommended ? '是' : '否'}</span></td>
                        <td>
                          {!agent.profile_exists ? (
                            <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>未配置</span>
                          ) : !agent.profile_enabled ? (
                            <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>已禁用</span>
                          ) : (
                            <span className="tag tag--positive">启用</span>
                          )}
                        </td>
                        <td>{agent.trigger_policy_on_code_change ? '是' : '否'}</td>
                        <td>{agent.impacted_nodes.length ? agent.impacted_nodes.join(', ') : '-'}</td>
                        <td style={{ maxWidth: 200, fontSize: '0.78rem', color: 'var(--color-text-secondary)', overflowWrap: 'anywhere' }}>{agent.reason}</td>
                        <td>
                          {agent.regression_payload ? (
                            <button className="btn btn--secondary btn--sm" onClick={() => togglePayload(agent.agent_name)}>
                              {expandedPayloads.has(agent.agent_name) ? '收起' : '展开'}
                            </button>
                          ) : (
                            <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>-</span>
                          )}
                        </td>
                        <td>
                          {agent.recommended && agent.regression_payload && (
                            <button
                              className="btn btn--primary btn--sm"
                              disabled={!!regressionRunning}
                              onClick={() => void runRegression(agent.agent_name, agent.regression_payload!)}
                            >
                              {regressionRunning === agent.agent_name ? '运行中...' : '运行回归'}
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {result.impacted_agents.map((agent) =>
                expandedPayloads.has(agent.agent_name) && agent.regression_payload ? (
                  <div key={`payload-${agent.agent_name}`} style={{ marginTop: '0.5rem', padding: '0.75rem', border: '1px solid rgba(129,160,207,0.14)', borderRadius: 'var(--radius-sm)', background: 'rgba(10,18,32,0.3)' }}>
                    <JsonBlock title={`${agent.agent_name} payload`} value={agent.regression_payload} />
                  </div>
                ) : null,
              )}
            </div>
          )}

          {/* Unmatched Files */}
          {result.unmatched_files.length > 0 && (
            <div>
              <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.95rem' }}>Unmatched Files ({result.unmatched_files.length})</h4>
              <ul style={{ margin: 0, paddingLeft: '1.5rem', fontSize: '0.82rem', color: 'var(--color-text-secondary)' }}>
                {result.unmatched_files.map((file) => <li key={file} style={{ marginBottom: '0.2rem' }}><code>{file}</code></li>)}
              </ul>
            </div>
          )}

          {/* Regression Results */}
          {Array.from(regressionResults.entries()).map(([agentName, runResult]) => (
            <div key={`reg-${agentName}`} style={{ padding: '1rem', border: '1px solid rgba(129,160,207,0.18)', borderRadius: 'var(--radius-sm)', background: 'rgba(10,18,32,0.3)' }}>
              <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.95rem' }}>{agentName} 回归结果</h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center', fontSize: '0.85rem' }}>
                <span className={`tag ${runResult.gate_result?.passed ? 'tag--positive' : 'tag--danger'}`}>
                  {runResult.gate_result?.passed ? '通过' : '未通过'}
                </span>
                <span>通过率：{((runResult.gate_result?.pass_rate ?? 0) * 100).toFixed(1)}%</span>
                <span>Case 数：{runResult.selected_case_count ?? '-'}</span>
                {runResult.eval_run?.summary?.failed_count != null && <span>失败：{runResult.eval_run.summary.failed_count}</span>}
                {runResult.eval_run?.summary?.critical_failure_count != null && <span>Critical：{runResult.eval_run.summary.critical_failure_count}</span>}
                <span>Eval Run: <code>{runResult.eval_run?.eval_run_id}</code></span>
              </div>
              {runResult.gate_result?.reasons?.length ? (
                <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
                  {runResult.gate_result.reasons.map((reason) => <div key={reason}>- {reason}</div>)}
                </div>
              ) : null}
            </div>
          ))}

          {/* Gate Dry Run Result */}
          {gateDryRunResult && (
            <div style={{ padding: '1rem', border: '1px solid rgba(255,183,77,0.25)', borderRadius: 'var(--radius-sm)', background: 'rgba(10,18,32,0.3)' }}>
              <h4 style={{ margin: '0 0 0.75rem', fontSize: '0.95rem' }}>部署 Gate Dry Run</h4>
              <div style={summaryGridStyle}>
                <article style={cardStyle}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>Gate 状态</span>
                  <strong style={{ fontSize: '1.2rem' }}>{gateDryRunResult.ok ? '将通过' : '将阻断'}</strong>
                </article>
                <article style={cardStyle}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>需要运行</span>
                  <strong style={{ fontSize: '1.2rem' }}>{gateDryRunResult.summary.recommended_run_count}</strong>
                </article>
                <article style={cardStyle}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>受影响 Agent</span>
                  <strong style={{ fontSize: '1.2rem' }}>{gateDryRunResult.summary.impacted_agent_count}</strong>
                </article>
              </div>

              {gateDryRunResult.runs.length > 0 && (
                <div style={{ marginTop: '0.75rem' }}>
                  <h5 style={{ margin: '0 0 0.5rem', fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>将运行的回归</h5>
                  <div className="table-shell">
                    <table className="harness-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr><th>Agent</th><th>Payload</th></tr>
                      </thead>
                      <tbody>
                        {gateDryRunResult.runs.map((run) => (
                          <tr key={run.agent_name}>
                            <td><code>{run.agent_name}</code></td>
                            <td>
                              <button className="btn btn--secondary btn--sm" onClick={() => togglePayload(`gate-${run.agent_name}`)}>
                                {expandedPayloads.has(`gate-${run.agent_name}`) ? '收起' : '展开'}
                              </button>
                              {expandedPayloads.has(`gate-${run.agent_name}`) && run.regression_payload && (
                                <div style={{ marginTop: '0.5rem', padding: '0.75rem', border: '1px solid rgba(129,160,207,0.14)', borderRadius: 'var(--radius-sm)', background: 'rgba(10,18,32,0.3)' }}>
                                  <JsonBlock title={run.agent_name} value={run.regression_payload} />
                                </div>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {gateDryRunResult.reasons.length > 0 && (
                <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
                  {gateDryRunResult.reasons.map((reason) => <div key={reason}>- {reason}</div>)}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  padding: '0.35rem 0.5rem',
  border: '1px solid var(--surface-border, #444)',
  borderRadius: 4,
  background: 'var(--surface-ground, #111)',
  color: 'var(--text-color, #eee)',
  fontSize: '0.85rem',
}

const summaryGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
  gap: 'var(--space-3)',
}

const cardStyle: React.CSSProperties = {
  display: 'grid',
  gap: 6,
  padding: 14,
  border: '1px solid rgba(129,160,207,0.14)',
  borderRadius: 'var(--radius-sm)',
  background: 'rgba(10,18,32,0.42)',
}
