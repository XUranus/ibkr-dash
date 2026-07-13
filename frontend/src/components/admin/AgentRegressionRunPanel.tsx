import { useState } from 'react'
import type { AgentRegressionGatePayload, AgentRegressionRunPayload } from '@/types/adminHarness'

interface AgentRegressionRunPanelProps {
  loading?: boolean
  onRun: (payload: AgentRegressionRunPayload) => void
}

const AGENT_OPTIONS = [
  'trade_decision',
  'daily_position_review',
  'trade_review',
  'account_copilot',
]

function normalizeNullableNumber(value: unknown): number | null {
  if (value === '' || value === null || value === undefined) return null
  const num = Number(value)
  if (Number.isNaN(num)) return null
  return num
}

export default function AgentRegressionRunPanel({ loading = false, onRun }: AgentRegressionRunPanelProps) {
  const [agentName, setAgentName] = useState('trade_decision')
  const [mode, setMode] = useState<'static' | 'live_mock'>('static')
  const [caseTag, setCaseTag] = useState('regression')
  const [severity, setSeverity] = useState('')
  const [includeDisabled, setIncludeDisabled] = useState(false)
  const [includeJudge, setIncludeJudge] = useState(false)
  const [includeNodeEval, setIncludeNodeEval] = useState(false)
  const [nodeName, setNodeName] = useState('')
  const [limit, setLimit] = useState(100)
  const [gateFailOnCritical, setGateFailOnCritical] = useState(true)
  const [gateFailOnHigh, setGateFailOnHigh] = useState(true)
  const [gateMinPassRate, setGateMinPassRate] = useState<number | ''>(0.95)
  const [gateMaxFailed, setGateMaxFailed] = useState<number | ''>(0)
  const [baselineEvalRunId, setBaselineEvalRunId] = useState('')
  const [validationError, setValidationError] = useState('')

  function validate(): boolean {
    if (!agentName) {
      setValidationError('请选择 Agent')
      return false
    }
    if (mode !== 'static' && mode !== 'live_mock') {
      setValidationError('评测模式无效')
      return false
    }
    if (limit < 1 || limit > 1000) {
      setValidationError('Limit 必须在 1-1000 之间')
      return false
    }
    const minPassRate = normalizeNullableNumber(gateMinPassRate)
    if (gateMinPassRate !== '' && gateMinPassRate != null && minPassRate === null) {
      setValidationError('通过率必须为数字')
      return false
    }
    if (minPassRate != null && (minPassRate < 0 || minPassRate > 1)) {
      setValidationError('通过率必须在 0-1 之间')
      return false
    }
    const maxFailed = normalizeNullableNumber(gateMaxFailed)
    if (gateMaxFailed !== '' && gateMaxFailed !== null && gateMaxFailed !== undefined && maxFailed === null) {
      setValidationError('最大失败数必须为数字')
      return false
    }
    if (maxFailed !== null && maxFailed < 0) {
      setValidationError('最大失败数不能为负')
      return false
    }
    setValidationError('')
    return true
  }

  function buildConfirmMessage(): string {
    const lines = [`确认运行 ${agentName} 的 Agent 回归评测吗？`]
    lines.push(`模式：${mode === 'static' ? 'Static Eval' : 'Live Mock Eval'}`)
    if (caseTag) lines.push(`Case Tag：${caseTag}`)
    if (includeNodeEval) {
      lines.push('本次将同时运行 Node Eval Case。Node Eval 失败也会计入 Gate 结果。')
      if (nodeName) lines.push(`Node Name：${nodeName}`)
    }
    const gateDesc: string[] = []
    if (gateFailOnCritical) gateDesc.push('critical 失败阻断')
    if (gateFailOnHigh) gateDesc.push('high 失败阻断')
    if (gateMinPassRate) gateDesc.push(`通过率要求 ${Math.round(gateMinPassRate * 100)}%`)
    if (gateDesc.length) lines.push(`Gate：${gateDesc.join('，')}`)
    if (mode === 'live_mock') {
      lines.push('')
      lines.push('Live Mock 会基于 mock 数据用评测 Prompt 重新生成输出，不读取真实账户/行情；当前不是完整 Agent Graph 重跑。')
    }
    if (includeJudge) {
      lines.push('')
      lines.push('所选回归评测启用了 LLM Judge，可能产生额外 token 成本。')
    }
    return lines.join('\n')
  }

  function handleRun() {
    if (!validate()) return
    const message = buildConfirmMessage()
    if (!window.confirm(message)) return

    const gate: AgentRegressionGatePayload = {
      fail_on_critical: gateFailOnCritical,
      fail_on_high: gateFailOnHigh,
      min_pass_rate: normalizeNullableNumber(gateMinPassRate),
      max_failed: normalizeNullableNumber(gateMaxFailed),
    }

    const payload: AgentRegressionRunPayload = {
      agent_name: agentName,
      mode,
      case_tag: caseTag || null,
      severity: severity || null,
      category: null,
      include_disabled: includeDisabled,
      include_judge: includeJudge,
      include_node_eval: includeNodeEval,
      node_name: nodeName.trim() || null,
      limit,
      gate,
      trigger: 'manual',
      baseline_eval_run_id: baselineEvalRunId || null,
    }

    onRun(payload)
  }

  return (
    <div className="agent-regression-panel" style={{ border: '1px solid var(--surface-border, #333)', borderRadius: 6, padding: '1rem', marginBottom: '1rem', background: 'var(--surface-card, #1e1e1e)' }}>
      <h3 style={{ margin: '0 0 0.75rem', fontSize: '1rem' }}>Agent 回归评测</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'flex-end' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', fontSize: '0.8rem', color: 'var(--text-color-secondary, #aaa)' }}>
            Agent
            <select value={agentName} onChange={(e) => setAgentName(e.target.value)} style={inputStyle}>
              {AGENT_OPTIONS.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', fontSize: '0.8rem', color: 'var(--text-color-secondary, #aaa)' }}>
            评测模式
            <select value={mode} onChange={(e) => setMode(e.target.value as 'static' | 'live_mock')} style={inputStyle}>
              <option value="static">Static Eval</option>
              <option value="live_mock">Live Mock Eval</option>
            </select>
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', fontSize: '0.8rem', color: 'var(--text-color-secondary, #aaa)' }}>
            Case Tag
            <input value={caseTag} onChange={(e) => setCaseTag(e.target.value)} placeholder="regression" style={inputStyle} />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', fontSize: '0.8rem', color: 'var(--text-color-secondary, #aaa)' }}>
            Severity
            <select value={severity} onChange={(e) => setSeverity(e.target.value)} style={inputStyle}>
              <option value="">全部</option>
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
              <option value="critical">critical</option>
            </select>
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', fontSize: '0.8rem', color: 'var(--text-color-secondary, #aaa)' }}>
            Limit
            <input type="number" value={limit} onChange={(e) => setLimit(Number(e.target.value))} min={1} max={1000} style={{ ...inputStyle, width: '5rem' }} />
          </label>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'flex-end' }}>
          <label style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--text-color-secondary, #aaa)' }}>
            <input type="checkbox" checked={includeDisabled} onChange={(e) => setIncludeDisabled(e.target.checked)} />
            Include Disabled
          </label>
          <label style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--text-color-secondary, #aaa)' }}>
            <input type="checkbox" checked={includeJudge} onChange={(e) => setIncludeJudge(e.target.checked)} />
            Include Judge
          </label>
          <label
            style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--text-color-secondary, #aaa)' }}
            title={includeNodeEval ? '同时运行该 Agent 下的 Node Eval Case' : '默认只跑 Agent 级 Case'}
          >
            <input type="checkbox" checked={includeNodeEval} onChange={(e) => setIncludeNodeEval(e.target.checked)} data-testid="regression-include-node-eval" />
            Include Node Eval
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', fontSize: '0.8rem', color: 'var(--text-color-secondary, #aaa)' }}>
            Node Name
            <input value={nodeName} onChange={(e) => setNodeName(e.target.value)} placeholder="可选，如 event_catalyst" disabled={!includeNodeEval} data-testid="regression-node-name" style={inputStyle} />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', fontSize: '0.8rem', color: 'var(--text-color-secondary, #aaa)' }}>
            Baseline Eval Run ID
            <input value={baselineEvalRunId} onChange={(e) => setBaselineEvalRunId(e.target.value)} placeholder="可选" style={inputStyle} />
          </label>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'flex-end' }}>
          <label style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--text-color-secondary, #aaa)' }}>
            <input type="checkbox" checked={gateFailOnCritical} onChange={(e) => setGateFailOnCritical(e.target.checked)} />
            Fail on Critical
          </label>
          <label style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--text-color-secondary, #aaa)' }}>
            <input type="checkbox" checked={gateFailOnHigh} onChange={(e) => setGateFailOnHigh(e.target.checked)} />
            Fail on High
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', fontSize: '0.8rem', color: 'var(--text-color-secondary, #aaa)' }}>
            Min Pass Rate
            <input type="number" value={gateMinPassRate} onChange={(e) => setGateMinPassRate(Number(e.target.value))} min={0} max={1} step={0.01} style={{ ...inputStyle, width: '5rem' }} />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', fontSize: '0.8rem', color: 'var(--text-color-secondary, #aaa)' }}>
            Max Failed
            <input type="number" value={gateMaxFailed} onChange={(e) => setGateMaxFailed(e.target.value === '' ? '' : Number(e.target.value))} min={0} style={{ ...inputStyle, width: '5rem' }} />
          </label>
        </div>

        {validationError && <div style={{ color: '#f87171', fontSize: '0.8rem' }}>{validationError}</div>}
        <div style={{ marginTop: '0.25rem' }}>
          <button className="btn btn--primary" disabled={!agentName || loading} onClick={handleRun}>
            {loading ? '运行中...' : '运行 Agent 回归评测'}
          </button>
        </div>
      </div>
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
