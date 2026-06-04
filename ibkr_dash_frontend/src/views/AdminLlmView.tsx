import { useState, useEffect, useCallback } from 'react'
import {
  activateLlmProvider,
  createLlmProvider,
  deleteLlmProvider,
  fetchLlmHealth,
  fetchLlmProviders,
  testActiveLlmChat,
  testLlmProvider,
  updateLlmProvider,
} from '@/api/adminLlm'
import AdminTabs from '@/components/AdminTabs'
import type { LlmChatTestResponse, LlmHealth, LlmProvider, LlmProviderPayload, LlmProviderTestResponse } from '@/types/adminLlm'

interface ProviderForm {
  id: string
  name: string
  provider_type: string
  base_url: string
  api_key: string
  default_model: string
  available_models_text: string
  temperature: number
  context_window_tokens: number
  input_token_limit: number
  output_token_limit: number
  timeout_seconds: number
  enabled: boolean
  enable_thinking: boolean
  reasoning_effort: string
}

const defaultForm: ProviderForm = {
  id: '',
  name: '',
  provider_type: 'openai_compatible',
  base_url: '',
  api_key: '',
  default_model: '',
  available_models_text: '',
  temperature: 0.2,
  context_window_tokens: 200000,
  input_token_limit: 150000,
  output_token_limit: 10000,
  timeout_seconds: 60,
  enabled: true,
  enable_thinking: false,
  reasoning_effort: 'high',
}

export default function AdminLlmView() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testingId, setTestingId] = useState('')
  const [deletingId, setDeletingId] = useState('')
  const [activatingId, setActivatingId] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [noticeMessage, setNoticeMessage] = useState('')
  const [health, setHealth] = useState<LlmHealth | null>(null)
  const [providers, setProviders] = useState<LlmProvider[]>([])
  const [showForm, setShowForm] = useState(false)
  const [editingProvider, setEditingProvider] = useState<LlmProvider | null>(null)
  const [form, setForm] = useState<ProviderForm>({ ...defaultForm })
  const [testPrompt, setTestPrompt] = useState('Please reply with OK')
  const [activeChatMessage, setActiveChatMessage] = useState('Introduce yourself in one sentence')
  const [activeChatModel, setActiveChatModel] = useState('')
  const [providerTestResult, setProviderTestResult] = useState<LlmProviderTestResponse | null>(null)
  const [chatTestResult, setChatTestResult] = useState<LlmChatTestResponse | null>(null)

  const activeProvider = health?.active_provider ?? providers.find((p) => p.is_active) ?? null

  function splitModels(value: string): string[] {
    return value.split(',').map((item) => item.trim()).filter(Boolean)
  }

  function resetForm(provider?: LlmProvider): void {
    setEditingProvider(provider ?? null)
    setForm({
      id: provider?.id ?? '',
      name: provider?.name ?? '',
      provider_type: provider?.provider_type ?? 'openai_compatible',
      base_url: provider?.base_url ?? '',
      api_key: '',
      default_model: provider?.default_model ?? '',
      available_models_text: provider?.available_models.join(', ') ?? '',
      temperature: provider?.temperature ?? 0.2,
      context_window_tokens: provider?.context_window_tokens ?? 200000,
      input_token_limit: provider?.input_token_limit ?? 150000,
      output_token_limit: provider?.output_token_limit ?? 10000,
      timeout_seconds: provider?.timeout_seconds ?? 60,
      enabled: provider?.enabled ?? true,
      enable_thinking: provider?.enable_thinking ?? false,
      reasoning_effort: provider?.reasoning_effort ?? 'high',
    })
  }

  const loadData = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      const [healthResponse, providerItems] = await Promise.all([fetchLlmHealth(), fetchLlmProviders()])
      setHealth(healthResponse)
      setProviders(providerItems)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to load LLM config')
    } finally {
      setLoading(false)
    }
  }, [])

  function openCreateForm(): void {
    resetForm()
    setShowForm(true)
  }

  function openEditForm(provider: LlmProvider): void {
    resetForm(provider)
    setShowForm(true)
  }

  function closeForm(): void {
    setShowForm(false)
    resetForm()
  }

  function buildPayload(includeApiKey: boolean): LlmProviderPayload {
    const payload: LlmProviderPayload = {
      name: form.name.trim(),
      provider_type: form.provider_type,
      base_url: form.base_url.trim(),
      default_model: form.default_model.trim(),
      available_models: splitModels(form.available_models_text),
      enabled: form.enabled,
      enable_thinking: form.enable_thinking,
      reasoning_effort: form.reasoning_effort,
      timeout_seconds: Number(form.timeout_seconds),
      temperature: Number(form.temperature),
      context_window_tokens: Number(form.context_window_tokens),
      input_token_limit: Number(form.input_token_limit),
      output_token_limit: Number(form.output_token_limit),
    }
    if (includeApiKey && form.api_key.trim()) {
      payload.api_key = form.api_key.trim()
    }
    return payload
  }

  async function saveProvider(): Promise<void> {
    setSaving(true)
    setErrorMessage('')
    setNoticeMessage('')
    try {
      if (editingProvider) {
        await updateLlmProvider(editingProvider.id, buildPayload(Boolean(form.api_key.trim())))
        setNoticeMessage('Provider updated')
      } else {
        await createLlmProvider(buildPayload(true))
        setNoticeMessage('Provider created')
      }
      closeForm()
      await loadData()
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function activateProvider(provider: LlmProvider): Promise<void> {
    setActivatingId(provider.id)
    setErrorMessage('')
    setNoticeMessage('')
    try {
      await activateLlmProvider(provider.id)
      setNoticeMessage(`${provider.name} set as active provider`)
      await loadData()
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Activation failed')
    } finally {
      setActivatingId('')
    }
  }

  async function removeProvider(provider: LlmProvider): Promise<void> {
    if (!window.confirm(`Delete ${provider.name}?`)) return
    setDeletingId(provider.id)
    setErrorMessage('')
    setNoticeMessage('')
    try {
      const response = await deleteLlmProvider(provider.id)
      setNoticeMessage(response.message)
      await loadData()
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Delete failed')
    } finally {
      setDeletingId('')
    }
  }

  async function runProviderTest(provider: LlmProvider): Promise<void> {
    setTestingId(provider.id)
    setProviderTestResult(null)
    setErrorMessage('')
    try {
      setProviderTestResult(await testLlmProvider(provider.id, testPrompt.trim() || 'Please reply with OK'))
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Test failed')
    } finally {
      setTestingId('')
    }
  }

  async function runActiveChatTest(): Promise<void> {
    setTestingId('active-chat')
    setChatTestResult(null)
    setErrorMessage('')
    try {
      setChatTestResult(await testActiveLlmChat(activeChatMessage.trim(), activeChatModel.trim()))
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Chat test failed')
    } finally {
      setTestingId('')
    }
  }

  useEffect(() => {
    void loadData()
  }, [loadData])

  function updateForm(field: keyof ProviderForm, value: string | number | boolean): void {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  return (
    <section className="page-section">
      <section className="surface-panel">
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">ADMIN</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem' }}>LLM Configuration</h2>
              <p className="panel-subtitle">Manage OpenAI-compatible LLM providers. Only one active provider at a time.</p>
            </div>
            <button className="btn btn--accent" onClick={openCreateForm}>+ New Provider</button>
          </div>
          <AdminTabs />
        </div>
      </section>

      {loading ? (
        <section className="surface-panel"><div className="surface-panel__content"><div className="empty-state">Loading...</div></div></section>
      ) : errorMessage ? (
        <section className="surface-panel"><div className="surface-panel__content"><div className="empty-state" style={{ color: 'var(--color-negative)' }}>{errorMessage}</div></div></section>
      ) : (
        <>
          {noticeMessage && <p style={{ margin: 0, padding: '12px 16px', borderRadius: 'var(--radius-md)', color: 'var(--color-positive)', background: 'rgba(9, 47, 39, 0.48)', border: '1px solid rgba(52, 210, 163, 0.18)' }}>{noticeMessage}</p>}

          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.05fr) minmax(360px, 0.95fr)', gap: 'var(--space-4)' }}>
            <section className="surface-panel">
              <div className="surface-panel__content">
                <div className="section-header">
                  <div>
                    <h3 className="panel-title">Active Provider</h3>
                    <p className="panel-subtitle">Agents read this active configuration.</p>
                  </div>
                  <span style={{ padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: '0.82rem', fontWeight: 600, background: health?.enabled ? 'rgba(52, 210, 163, 0.15)' : 'rgba(255, 107, 122, 0.15)', color: health?.enabled ? 'var(--color-positive)' : 'var(--color-negative)' }}>{health?.enabled ? 'LLM ON' : 'LLM OFF'}</span>
                </div>

                {activeProvider ? (
                  <div style={{ display: 'grid', gap: 'var(--space-3)' }}>
                    <div style={{ display: 'grid', gap: 4, padding: 16, borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.72)', border: '1px solid rgba(129, 160, 207, 0.12)' }}>
                      <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>Provider</span>
                      <strong>{activeProvider.name}</strong>
                    </div>
                    <dl style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 'var(--space-3)', margin: 0 }}>
                      {[
                        ['Base URL', activeProvider.base_url],
                        ['Model', activeProvider.default_model],
                        ['API Key', activeProvider.api_key_masked || '--'],
                        ['Status', activeProvider.enabled ? 'Enabled' : 'Disabled'],
                        ['Thinking', activeProvider.enable_thinking ? 'On' : 'Off'],
                      ].map(([k, v]) => (
                        <div key={k} style={{ minWidth: 0, padding: 14, borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.52)' }}>
                          <dt style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>{k}</dt>
                          <dd style={{ margin: '6px 0 0', overflowWrap: 'anywhere', fontWeight: 600 }}>{v}</dd>
                        </div>
                      ))}
                    </dl>
                    <button className="btn btn--accent" disabled={testingId === activeProvider.id} onClick={() => void runProviderTest(activeProvider)}>
                      {testingId === activeProvider.id ? 'Testing...' : 'Test Connection'}
                    </button>
                  </div>
                ) : (
                  <div className="empty-state" style={{ minHeight: 180 }}>No active provider configured</div>
                )}
              </div>
            </section>

            <section className="surface-panel">
              <div className="surface-panel__content">
                <div className="section-header">
                  <div>
                    <h3 className="panel-title">Test Area</h3>
                    <p className="panel-subtitle">Test individual providers or the active chat.</p>
                  </div>
                </div>
                <div style={{ display: 'grid', gap: 'var(--space-3)' }}>
                  <label className="field-stack">
                    <span className="field-stack__label">Provider test prompt</span>
                    <textarea className="input" style={{ minHeight: 96, resize: 'vertical' as const }} value={testPrompt} onChange={(e) => setTestPrompt(e.target.value)} rows={3} />
                  </label>
                  <label className="field-stack">
                    <span className="field-stack__label">Active chat message</span>
                    <textarea className="input" style={{ minHeight: 96, resize: 'vertical' as const }} value={activeChatMessage} onChange={(e) => setActiveChatMessage(e.target.value)} rows={3} />
                  </label>
                  <label className="field-stack">
                    <span className="field-stack__label">Optional model override</span>
                    <input className="input" value={activeChatModel} onChange={(e) => setActiveChatModel(e.target.value)} placeholder="Leave empty for default" />
                  </label>
                  <button className="btn btn--accent" disabled={!activeProvider || testingId === 'active-chat'} onClick={() => void runActiveChatTest()}>
                    {testingId === 'active-chat' ? 'Testing...' : 'Test Active Chat'}
                  </button>
                </div>
              </div>
            </section>
          </div>

          {(providerTestResult || chatTestResult) && (
            <section className="surface-panel">
              <div className="surface-panel__content">
                <h3 className="panel-title">Test Results</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 'var(--space-3)', marginTop: 'var(--space-3)' }}>
                  {providerTestResult && (
                    <div style={{ display: 'grid', gap: 8, padding: 16, borderRadius: 'var(--radius-md)', background: providerTestResult.success ? 'rgba(9, 47, 39, 0.42)' : 'rgba(55, 18, 28, 0.5)', border: `1px solid ${providerTestResult.success ? 'rgba(52, 210, 163, 0.18)' : 'rgba(255, 107, 125, 0.2)'}` }}>
                      <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>Provider Test</span>
                      <strong>{providerTestResult.success ? 'Success' : providerTestResult.error_code}</strong>
                      <p style={{ margin: 0, color: 'var(--color-text-secondary)', whiteSpace: 'pre-wrap' }}>{providerTestResult.content || providerTestResult.message}</p>
                      {providerTestResult.latency_ms !== null && <small>{providerTestResult.latency_ms} ms {'·'} {providerTestResult.model}</small>}
                    </div>
                  )}
                  {chatTestResult && (
                    <div style={{ display: 'grid', gap: 8, padding: 16, borderRadius: 'var(--radius-md)', background: chatTestResult.success ? 'rgba(9, 47, 39, 0.42)' : 'rgba(55, 18, 28, 0.5)', border: `1px solid ${chatTestResult.success ? 'rgba(52, 210, 163, 0.18)' : 'rgba(255, 107, 125, 0.2)'}` }}>
                      <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>Active Chat</span>
                      <strong>{chatTestResult.success ? 'Success' : chatTestResult.error_code}</strong>
                      <p style={{ margin: 0, color: 'var(--color-text-secondary)', whiteSpace: 'pre-wrap' }}>{chatTestResult.content || chatTestResult.message}</p>
                      {chatTestResult.model && <small>{chatTestResult.model}</small>}
                    </div>
                  )}
                </div>
              </div>
            </section>
          )}

          <section className="surface-panel">
            <div className="surface-panel__content">
              <div className="section-header">
                <div>
                  <h3 className="panel-title">Provider List</h3>
                  <p className="panel-subtitle">Only one active provider at a time.</p>
                </div>
              </div>
              {providers.length > 0 ? (
                <div className="table-shell" style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', minWidth: 1400, borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        {['Name', 'Type', 'Base URL', 'Model', 'Token Profile', 'API Key', 'Enabled', 'Thinking', 'Reasoning', 'Active', 'Actions'].map((h) => (
                          <th key={h} style={{ padding: '0.9rem 1rem', borderBottom: '1px solid rgba(129, 160, 207, 0.12)', textAlign: 'left', color: 'var(--color-text-secondary)', fontSize: '0.8rem', letterSpacing: '0.08em', textTransform: 'uppercase' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {providers.map((p) => (
                        <tr key={p.id}>
                          <td style={cellStyle}>{p.name}</td>
                          <td style={cellStyle}>{p.provider_type}</td>
                          <td style={{ ...cellStyle, maxWidth: 260, overflowWrap: 'anywhere' }}>{p.base_url}</td>
                          <td style={cellStyle}>{p.default_model}</td>
                          <td style={{ ...cellStyle, color: 'var(--color-text-secondary)', fontVariantNumeric: 'tabular-nums' }}>{p.context_window_tokens.toLocaleString()} / {p.input_token_limit.toLocaleString()} / {p.output_token_limit.toLocaleString()}</td>
                          <td style={cellStyle}>{p.api_key_masked || '--'}</td>
                          <td style={cellStyle}><span style={{ padding: '2px 10px', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', fontWeight: 600, background: p.enabled ? 'rgba(52, 210, 163, 0.15)' : 'rgba(255, 107, 122, 0.15)', color: p.enabled ? 'var(--color-positive)' : 'var(--color-negative)' }}>{p.enabled ? 'YES' : 'NO'}</span></td>
                          <td style={cellStyle}>{p.enable_thinking ? 'On' : 'Off'}</td>
                          <td style={cellStyle}>{p.enable_thinking ? p.reasoning_effort : '--'}</td>
                          <td style={cellStyle}><span style={{ padding: '2px 10px', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', fontWeight: 600, background: p.is_active ? 'rgba(86, 213, 255, 0.15)' : 'transparent', color: p.is_active ? 'var(--color-accent)' : 'var(--color-text-secondary)' }}>{p.is_active ? 'ACTIVE' : 'STANDBY'}</span></td>
                          <td style={{ ...cellStyle, minWidth: 400 }}>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                              <button className="btn btn--ghost btn--sm" onClick={() => openEditForm(p)}>Edit</button>
                              <button className="btn btn--ghost btn--sm" disabled={p.is_active || !p.enabled || activatingId === p.id} onClick={() => void activateProvider(p)}>{activatingId === p.id ? '...' : 'Activate'}</button>
                              <button className="btn btn--ghost btn--sm" disabled={testingId === p.id} onClick={() => void runProviderTest(p)}>{testingId === p.id ? '...' : 'Test'}</button>
                              <button className="btn btn--ghost btn--sm" style={{ color: 'var(--color-negative)' }} disabled={deletingId === p.id} onClick={() => void removeProvider(p)}>{deletingId === p.id ? '...' : 'Delete'}</button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="empty-state">No providers configured</div>
              )}
            </div>
          </section>
        </>
      )}

      {showForm && (
        <div className="admin-dialog-backdrop" onClick={(e) => { if (e.target === e.currentTarget) closeForm() }}>
          <section className="surface-panel admin-dialog" style={{ width: 'min(880px, 100%)', maxHeight: 'min(86vh, 920px)', overflow: 'auto' }}>
            <div className="surface-panel__content">
              <div className="section-header">
                <div>
                  <p className="eyebrow">{editingProvider ? 'EDIT' : 'CREATE'}</p>
                  <h3 className="panel-title">{editingProvider ? 'Edit Provider' : 'New Provider'}</h3>
                </div>
                <button className="btn btn--ghost" onClick={closeForm}>X</button>
              </div>

              <form style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 'var(--space-3)' }} onSubmit={(e) => { e.preventDefault(); void saveProvider() }}>
                <label className="field-stack"><span className="field-stack__label">Name</span><input className="input" value={form.name} onChange={(e) => updateForm('name', e.target.value)} required placeholder="Bailian / OpenAI" /></label>
                <label className="field-stack"><span className="field-stack__label">Type</span><select className="input" value={form.provider_type} onChange={(e) => updateForm('provider_type', e.target.value)}><option value="openai_compatible">openai_compatible</option></select></label>
                <label className="field-stack" style={{ gridColumn: '1 / -1' }}><span className="field-stack__label">Base URL</span><input className="input" value={form.base_url} onChange={(e) => updateForm('base_url', e.target.value)} required placeholder="https://..." /></label>
                <label className="field-stack"><span className="field-stack__label">API Key</span><input className="input" type="password" value={form.api_key} onChange={(e) => updateForm('api_key', e.target.value)} required={!editingProvider} placeholder={editingProvider ? 'Leave empty to keep unchanged' : ''} /></label>
                <label className="field-stack"><span className="field-stack__label">Default Model</span><input className="input" value={form.default_model} onChange={(e) => updateForm('default_model', e.target.value)} required placeholder="gpt-4o" /></label>
                <label className="field-stack" style={{ gridColumn: '1 / -1' }}><span className="field-stack__label">Available Models (comma-separated)</span><input className="input" value={form.available_models_text} onChange={(e) => updateForm('available_models_text', e.target.value)} placeholder="model-a, model-b" /></label>
                <label className="field-stack"><span className="field-stack__label">Temperature</span><input className="input" type="number" min={0} max={2} step={0.1} value={form.temperature} onChange={(e) => updateForm('temperature', Number(e.target.value))} /></label>
                <label className="field-stack"><span className="field-stack__label">Context Window Tokens</span><input className="input" type="number" min={1} step={1000} value={form.context_window_tokens} onChange={(e) => updateForm('context_window_tokens', Number(e.target.value))} /></label>
                <label className="field-stack"><span className="field-stack__label">Input Token Limit</span><input className="input" type="number" min={1} step={1000} value={form.input_token_limit} onChange={(e) => updateForm('input_token_limit', Number(e.target.value))} /></label>
                <label className="field-stack"><span className="field-stack__label">Output Token Limit</span><input className="input" type="number" min={1} step={100} value={form.output_token_limit} onChange={(e) => updateForm('output_token_limit', Number(e.target.value))} /></label>
                <label className="field-stack"><span className="field-stack__label">Timeout (seconds)</span><input className="input" type="number" min={1} max={300} value={form.timeout_seconds} onChange={(e) => updateForm('timeout_seconds', Number(e.target.value))} /></label>
                <p style={{ gridColumn: '1 / -1', margin: 0, color: 'var(--color-text-secondary)', fontSize: '0.88rem', lineHeight: 1.6 }}>
                  Output token limit is sent as max_tokens to the model. Input token limit controls the system&apos;s tool result and evidence pack size. Context window must be &gt;= input + output.
                </p>
                <label style={{ display: 'inline-flex', alignItems: 'center', gap: 10, alignSelf: 'end', color: 'var(--color-text-secondary)' }}>
                  <input type="checkbox" checked={form.enabled} onChange={(e) => updateForm('enabled', e.target.checked)} style={{ width: 18, height: 18, accentColor: 'var(--color-accent)' }} /><span>Enabled</span>
                </label>
                <label style={{ display: 'inline-flex', alignItems: 'center', gap: 10, alignSelf: 'end', color: 'var(--color-text-secondary)' }}>
                  <input type="checkbox" checked={form.enable_thinking} onChange={(e) => updateForm('enable_thinking', e.target.checked)} style={{ width: 18, height: 18, accentColor: 'var(--color-accent)' }} /><span>Enable Thinking</span>
                </label>
                {form.enable_thinking && (
                  <label className="field-stack"><span className="field-stack__label">Reasoning Effort</span><select className="input" value={form.reasoning_effort} onChange={(e) => updateForm('reasoning_effort', e.target.value)}><option value="high">high</option><option value="max">max</option></select></label>
                )}
                <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
                  <button type="button" className="btn btn--ghost" onClick={closeForm}>Cancel</button>
                  <button type="submit" className="btn btn--accent" disabled={saving}>{saving ? 'Saving...' : 'Save'}</button>
                </div>
              </form>
            </div>
          </section>
        </div>
      )}
    </section>
  )
}

const cellStyle: React.CSSProperties = {
  padding: '0.9rem 1rem',
  borderBottom: '1px solid rgba(129, 160, 207, 0.12)',
  textAlign: 'left',
  verticalAlign: 'top',
}
