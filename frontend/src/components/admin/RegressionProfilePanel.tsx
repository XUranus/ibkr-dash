import { useState, useEffect, useCallback } from 'react'
import Modal from '@/components/Modal'
import JsonBlock from '@/components/admin/JsonBlock'
import {
  buildRegressionPayloadFromProfile,
  disableRegressionProfile,
  listRegressionProfiles,
  upsertRegressionProfile,
} from '@/api/adminHarness'
import type { RegressionProfile, RegressionProfileUpsertPayload } from '@/types/adminHarness'

const AGENT_OPTIONS = ['trade_decision', 'daily_position_review', 'trade_review', 'account_copilot']

interface ProfileForm {
  agent_name: string
  enabled: boolean
  mode: 'static' | 'live_mock'
  case_tag: string
  severity: string
  category: string
  include_disabled: boolean
  include_judge: boolean
  include_node_eval: boolean
  node_name: string
  limit: number
  gate_fail_on_critical: boolean
  gate_fail_on_high: boolean
  gate_min_pass_rate: number
  gate_max_failed: number | ''
  trigger_policy_on_prompt_save: boolean
  trigger_policy_on_code_change: boolean
  trigger_policy_on_deploy: boolean
  notes: string
}

const DEFAULT_FORM: ProfileForm = {
  agent_name: '',
  enabled: true,
  mode: 'static',
  case_tag: 'regression',
  severity: '',
  category: '',
  include_disabled: false,
  include_judge: false,
  include_node_eval: false,
  node_name: '',
  limit: 100,
  gate_fail_on_critical: true,
  gate_fail_on_high: false,
  gate_min_pass_rate: 0.9,
  gate_max_failed: '',
  trigger_policy_on_prompt_save: false,
  trigger_policy_on_code_change: false,
  trigger_policy_on_deploy: false,
  notes: '',
}

function formatDateTime(iso: string | undefined): string {
  if (!iso) return '-'
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

export default function RegressionProfilePanel() {
  const [profiles, setProfiles] = useState<RegressionProfile[]>([])
  const [summary, setSummary] = useState({ profile_count: 0, enabled_count: 0 })
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [noticeMessage, setNoticeMessage] = useState('')

  const [editorVisible, setEditorVisible] = useState(false)
  const [editorMode, setEditorMode] = useState<'create' | 'edit'>('create')
  const [editorSaving, setEditorSaving] = useState(false)
  const [editorError, setEditorError] = useState('')
  const [form, setForm] = useState<ProfileForm>({ ...DEFAULT_FORM })

  const [payloadPreviewVisible, setPayloadPreviewVisible] = useState(false)
  const [payloadPreviewLoading, setPayloadPreviewLoading] = useState(false)
  const [payloadPreviewData, setPayloadPreviewData] = useState<Record<string, unknown> | null>(null)
  const [payloadPreviewAgent, setPayloadPreviewAgent] = useState('')

  const loadProfiles = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      const data = await listRegressionProfiles({ limit: 100 })
      setProfiles(data.items)
      setSummary(data.summary)
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadProfiles()
  }, [loadProfiles])

  function openCreate() {
    setEditorMode('create')
    setEditorError('')
    setForm({ ...DEFAULT_FORM })
    setEditorVisible(true)
  }

  function openEdit(profile: RegressionProfile) {
    setEditorMode('edit')
    setEditorError('')
    setForm({
      agent_name: profile.agent_name,
      enabled: profile.enabled,
      mode: (profile.mode as 'static' | 'live_mock') || 'static',
      case_tag: profile.case_tag || '',
      severity: profile.severity || '',
      category: profile.category || '',
      include_disabled: profile.include_disabled,
      include_judge: profile.include_judge,
      include_node_eval: profile.include_node_eval,
      node_name: profile.node_name || '',
      limit: profile.limit,
      gate_fail_on_critical: profile.gate?.fail_on_critical ?? true,
      gate_fail_on_high: profile.gate?.fail_on_high ?? false,
      gate_min_pass_rate: profile.gate?.min_pass_rate ?? 0.9,
      gate_max_failed: profile.gate?.max_failed ?? '',
      trigger_policy_on_prompt_save: profile.trigger_policy?.on_prompt_save ?? false,
      trigger_policy_on_code_change: profile.trigger_policy?.on_code_change ?? false,
      trigger_policy_on_deploy: profile.trigger_policy?.on_deploy ?? false,
      notes: profile.notes || '',
    })
    setEditorVisible(true)
  }

  function validate(): boolean {
    if (!form.agent_name) {
      setEditorError('请选择 Agent')
      return false
    }
    if (form.limit < 1 || form.limit > 1000) {
      setEditorError('Limit 必须在 1-1000 之间')
      return false
    }
    if (form.gate_min_pass_rate < 0 || form.gate_min_pass_rate > 1) {
      setEditorError('通过率必须在 0-1 之间')
      return false
    }
    if (form.gate_max_failed !== '' && (form.gate_max_failed as number) < 0) {
      setEditorError('最大失败数不能为负')
      return false
    }
    setEditorError('')
    return true
  }

  async function handleSave() {
    if (!validate()) return
    setEditorSaving(true)
    setEditorError('')
    try {
      const payload: RegressionProfileUpsertPayload = {
        enabled: form.enabled,
        mode: form.mode,
        case_tag: form.case_tag || null,
        severity: form.severity || null,
        category: form.category || null,
        include_disabled: form.include_disabled,
        include_judge: form.include_judge,
        include_node_eval: form.include_node_eval,
        node_name: form.node_name.trim() || null,
        limit: form.limit,
        gate: {
          fail_on_critical: form.gate_fail_on_critical,
          fail_on_high: form.gate_fail_on_high,
          min_pass_rate: form.gate_min_pass_rate,
          max_failed: form.gate_max_failed === '' ? null : form.gate_max_failed,
        },
        trigger_policy: {
          on_prompt_save: form.trigger_policy_on_prompt_save,
          on_code_change: form.trigger_policy_on_code_change,
          on_deploy: form.trigger_policy_on_deploy,
        },
        notes: form.notes,
      }
      await upsertRegressionProfile(form.agent_name, payload)
      setEditorVisible(false)
      setNoticeMessage(`Profile ${editorMode === 'create' ? '创建' : '更新'}成功`)
      await loadProfiles()
    } catch (err: unknown) {
      setEditorError(err instanceof Error ? err.message : String(err))
    } finally {
      setEditorSaving(false)
    }
  }

  async function handleDisable(profile: RegressionProfile) {
    if (!window.confirm(`确认禁用 ${profile.agent_name} 的回归配置？`)) return
    try {
      await disableRegressionProfile(profile.agent_name)
      setNoticeMessage(`${profile.agent_name} 已禁用`)
      await loadProfiles()
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : String(err))
    }
  }

  async function handleBuildPayload(profile: RegressionProfile) {
    setPayloadPreviewAgent(profile.agent_name)
    setPayloadPreviewLoading(true)
    setPayloadPreviewVisible(true)
    setPayloadPreviewData(null)
    try {
      const data = await buildRegressionPayloadFromProfile(profile.agent_name)
      setPayloadPreviewData(data)
    } catch (err: unknown) {
      setPayloadPreviewData({ error: err instanceof Error ? err.message : String(err) })
    } finally {
      setPayloadPreviewLoading(false)
    }
  }

  function updateForm(key: keyof ProfileForm, value: unknown) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <div className="regression-profile-panel" style={{ display: 'grid', gap: 'var(--space-4)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <div style={{ display: 'flex', gap: '1rem', fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
          <span>共 {summary.profile_count} 个配置</span>
          <span>启用 {summary.enabled_count}</span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn--primary btn--sm" onClick={openCreate}>新增配置</button>
          <button className="btn btn--secondary btn--sm" disabled={loading} onClick={() => void loadProfiles()}>
            {loading ? '刷新中...' : '刷新'}
          </button>
        </div>
      </div>

      {noticeMessage && (
        <p style={{ margin: 0, padding: '8px 12px', borderRadius: 'var(--radius-sm)', background: 'rgba(88,214,161,0.12)', color: 'var(--color-positive)', fontSize: '0.85rem' }}>{noticeMessage}</p>
      )}
      {errorMessage && (
        <p style={{ margin: 0, padding: '8px 12px', borderRadius: 'var(--radius-sm)', background: 'rgba(255,107,122,0.12)', color: 'var(--color-negative)', fontSize: '0.85rem' }}>{errorMessage}</p>
      )}

      {loading && !profiles.length ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-secondary)' }}>加载中...</div>
      ) : !profiles.length ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-secondary)' }}>暂无回归配置，点击&ldquo;新增配置&rdquo;创建。</div>
      ) : (
        <div className="table-shell">
          <table className="harness-table" style={{ fontSize: '0.82rem', width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th>Agent</th>
                <th>启用</th>
                <th>模式</th>
                <th>Include Node Eval</th>
                <th>Node Name</th>
                <th>Include Judge</th>
                <th>Case Tag</th>
                <th>Min Pass Rate</th>
                <th>Fail on Critical</th>
                <th>Fail on High</th>
                <th>Limit</th>
                <th>更新时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {profiles.map((profile) => (
                <tr key={profile.profile_id}>
                  <td><code>{profile.agent_name}</code></td>
                  <td><span className={`tag ${profile.enabled ? 'tag--positive' : ''}`}>{profile.enabled ? '启用' : '禁用'}</span></td>
                  <td>{profile.mode}</td>
                  <td>{profile.include_node_eval ? '是' : '否'}</td>
                  <td>{profile.node_name || '-'}</td>
                  <td>{profile.include_judge ? '是' : '否'}</td>
                  <td>{profile.case_tag || '-'}</td>
                  <td>{profile.gate?.min_pass_rate != null ? `${Math.round(profile.gate.min_pass_rate * 100)}%` : '-'}</td>
                  <td>{profile.gate?.fail_on_critical ? '是' : '否'}</td>
                  <td>{profile.gate?.fail_on_high ? '是' : '否'}</td>
                  <td>{profile.limit}</td>
                  <td>{formatDateTime(profile.updated_at)}</td>
                  <td style={{ display: 'flex', gap: 4, whiteSpace: 'nowrap' }}>
                    <button className="btn btn--secondary btn--sm" title="编辑" onClick={() => openEdit(profile)}>编辑</button>
                    <button className="btn btn--secondary btn--sm" title="预览回归参数" onClick={() => void handleBuildPayload(profile)}>预览</button>
                    {profile.enabled && (
                      <button className="btn btn--secondary btn--sm" title="禁用" onClick={() => void handleDisable(profile)}>禁用</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Editor Modal */}
      <Modal open={editorVisible} onClose={() => setEditorVisible(false)} title={editorMode === 'create' ? '新增回归配置' : '编辑回归配置'} width="640px">
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'flex-end' }}>
            <label style={labelStyle}>
              Agent
              <select value={form.agent_name} onChange={(e) => updateForm('agent_name', e.target.value)} disabled={editorMode === 'edit'} style={inputStyle}>
                <option value="" disabled>请选择</option>
                {AGENT_OPTIONS.map((a) => <option key={a} value={a}>{a}</option>)}
              </select>
            </label>
            <label style={labelStyle}>
              模式
              <select value={form.mode} onChange={(e) => updateForm('mode', e.target.value)} style={inputStyle}>
                <option value="static">Static Eval</option>
                <option value="live_mock">Live Mock Eval</option>
              </select>
            </label>
            <label style={labelStyle}>
              Case Tag
              <input value={form.case_tag} onChange={(e) => updateForm('case_tag', e.target.value)} placeholder="regression" style={inputStyle} />
            </label>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'flex-end' }}>
            <label style={labelStyle}>
              Severity
              <select value={form.severity} onChange={(e) => updateForm('severity', e.target.value)} style={inputStyle}>
                <option value="">全部</option>
                <option value="low">low</option>
                <option value="medium">medium</option>
                <option value="high">high</option>
                <option value="critical">critical</option>
              </select>
            </label>
            <label style={labelStyle}>
              Category
              <input value={form.category} onChange={(e) => updateForm('category', e.target.value)} placeholder="可选" style={inputStyle} />
            </label>
            <label style={labelStyle}>
              Limit
              <input type="number" value={form.limit} onChange={(e) => updateForm('limit', Number(e.target.value))} min={1} max={1000} style={{ ...inputStyle, width: '5rem' }} />
            </label>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'flex-end' }}>
            <label style={checkboxLabelStyle}>
              <input type="checkbox" checked={form.enabled} onChange={(e) => updateForm('enabled', e.target.checked)} />
              启用
            </label>
            <label style={checkboxLabelStyle}>
              <input type="checkbox" checked={form.include_disabled} onChange={(e) => updateForm('include_disabled', e.target.checked)} />
              Include Disabled
            </label>
            <label style={checkboxLabelStyle}>
              <input type="checkbox" checked={form.include_judge} onChange={(e) => updateForm('include_judge', e.target.checked)} />
              Include Judge
            </label>
            <label style={checkboxLabelStyle}>
              <input type="checkbox" checked={form.include_node_eval} onChange={(e) => updateForm('include_node_eval', e.target.checked)} />
              Include Node Eval
            </label>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'flex-end' }}>
            <label style={labelStyle}>
              Node Name
              <input value={form.node_name} onChange={(e) => updateForm('node_name', e.target.value)} placeholder="可选" disabled={!form.include_node_eval} style={inputStyle} />
            </label>
            <label style={labelStyle}>
              Notes
              <input value={form.notes} onChange={(e) => updateForm('notes', e.target.value)} placeholder="可选备注" style={inputStyle} />
            </label>
          </div>

          <fieldset style={{ border: '1px solid rgba(129,160,207,0.18)', borderRadius: 'var(--radius-sm)', padding: '0.75rem' }}>
            <legend style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', padding: '0 0.4rem' }}>Gate 配置</legend>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'flex-end' }}>
              <label style={checkboxLabelStyle}>
                <input type="checkbox" checked={form.gate_fail_on_critical} onChange={(e) => updateForm('gate_fail_on_critical', e.target.checked)} />
                Fail on Critical
              </label>
              <label style={checkboxLabelStyle}>
                <input type="checkbox" checked={form.gate_fail_on_high} onChange={(e) => updateForm('gate_fail_on_high', e.target.checked)} />
                Fail on High
              </label>
              <label style={labelStyle}>
                Min Pass Rate
                <input type="number" value={form.gate_min_pass_rate} onChange={(e) => updateForm('gate_min_pass_rate', Number(e.target.value))} min={0} max={1} step={0.01} style={{ ...inputStyle, width: '5rem' }} />
              </label>
              <label style={labelStyle}>
                Max Failed
                <input type="number" value={form.gate_max_failed} onChange={(e) => updateForm('gate_max_failed', e.target.value === '' ? '' : Number(e.target.value))} min={0} placeholder="不限" style={{ ...inputStyle, width: '5rem' }} />
              </label>
            </div>
          </fieldset>

          <fieldset style={{ border: '1px solid rgba(129,160,207,0.18)', borderRadius: 'var(--radius-sm)', padding: '0.75rem' }}>
            <legend style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', padding: '0 0.4rem' }}>触发策略（仅存储，暂不自动执行）</legend>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'flex-end' }}>
              <label style={checkboxLabelStyle}>
                <input type="checkbox" checked={form.trigger_policy_on_prompt_save} onChange={(e) => updateForm('trigger_policy_on_prompt_save', e.target.checked)} />
                Prompt 保存时
              </label>
              <label style={checkboxLabelStyle}>
                <input type="checkbox" checked={form.trigger_policy_on_code_change} onChange={(e) => updateForm('trigger_policy_on_code_change', e.target.checked)} />
                代码变更时
              </label>
              <label style={checkboxLabelStyle}>
                <input type="checkbox" checked={form.trigger_policy_on_deploy} onChange={(e) => updateForm('trigger_policy_on_deploy', e.target.checked)} />
                部署前
              </label>
            </div>
          </fieldset>

          {editorError && <p style={{ color: '#f87171', fontSize: '0.8rem', margin: 0 }}>{editorError}</p>}

          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 8 }}>
            <button className="btn btn--secondary" onClick={() => setEditorVisible(false)}>取消</button>
            <button className="btn btn--primary" disabled={editorSaving} onClick={() => void handleSave()}>
              {editorSaving ? '保存中...' : '保存'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Payload Preview Modal */}
      <Modal open={payloadPreviewVisible} onClose={() => setPayloadPreviewVisible(false)} title={`回归参数预览 — ${payloadPreviewAgent}`} width="600px">
        {payloadPreviewLoading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-secondary)' }}>生成中...</div>
        ) : payloadPreviewData ? (
          <JsonBlock title="payload" value={payloadPreviewData} />
        ) : null}
      </Modal>
    </div>
  )
}

const labelStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '0.2rem',
  fontSize: '0.8rem',
  color: 'var(--color-text-secondary)',
}

const checkboxLabelStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'row',
  alignItems: 'center',
  gap: '0.4rem',
  fontSize: '0.8rem',
  color: 'var(--color-text-secondary)',
}

const inputStyle: React.CSSProperties = {
  padding: '0.35rem 0.5rem',
  border: '1px solid var(--surface-border, #444)',
  borderRadius: 4,
  background: 'var(--surface-ground, #111)',
  color: 'var(--text-color, #eee)',
  fontSize: '0.85rem',
}
