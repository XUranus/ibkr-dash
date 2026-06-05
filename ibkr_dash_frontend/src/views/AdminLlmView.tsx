import { useState, useEffect, useCallback } from 'react'
import { fetchLlmHealth, fetchLlmProviders, testLlmProvider, testActiveLlmChat } from '@/api/adminLlm'
import AdminTabs from '@/components/AdminTabs'
import type { LlmChatTestResponse, LlmHealth, LlmProvider, LlmProviderTestResponse } from '@/types/adminLlm'

export default function AdminLlmView() {
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [health, setHealth] = useState<LlmHealth | null>(null)
  const [providers, setProviders] = useState<LlmProvider[]>([])
  const [testingId, setTestingId] = useState('')
  const [testPrompt, setTestPrompt] = useState('Please reply with OK')
  const [providerTestResult, setProviderTestResult] = useState<LlmProviderTestResponse | null>(null)
  const [chatTestResult, setChatTestResult] = useState<LlmChatTestResponse | null>(null)
  const [activeChatMessage, setActiveChatMessage] = useState('Introduce yourself in one sentence')

  const activeProvider = providers.find((p) => p.is_active) ?? null

  const loadData = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      const [h, p] = await Promise.all([fetchLlmHealth(), fetchLlmProviders()])
      setHealth(h)
      setProviders(Array.isArray(p) ? p : [])
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to load LLM config')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadData() }, [loadData])

  async function handleTestProvider() {
    if (!activeProvider) return
    setTestingId('active')
    setProviderTestResult(null)
    try {
      const result = await testLlmProvider(testPrompt)
      setProviderTestResult(result)
    } catch (err) {
      setProviderTestResult({ success: false, model: null, content: null, latency_ms: null, message: err instanceof Error ? err.message : 'Test failed' })
    } finally {
      setTestingId('')
    }
  }

  async function handleTestChat() {
    setTestingId('chat')
    setChatTestResult(null)
    try {
      const result = await testActiveLlmChat(activeChatMessage)
      setChatTestResult(result)
    } catch (err) {
      setChatTestResult({ success: false, model: null, content: null, message: err instanceof Error ? err.message : 'Test failed' })
    } finally {
      setTestingId('')
    }
  }

  if (loading) return <section className="page-section"><div className="surface-panel"><div className="surface-panel__content">Loading...</div></div></section>

  return (
    <section className="page-section">
      <AdminTabs />

      {errorMessage && (
        <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(242,92,92,0.2)', background: 'rgba(242,92,92,0.05)', color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
          {errorMessage}
        </div>
      )}

      {/* Active Provider */}
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease' }}>
        <div className="surface-panel__content">
          <p className="eyebrow">ACTIVE PROVIDER</p>
          {activeProvider ? (
            <div style={{ display: 'grid', gap: 12, marginTop: 12 }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
                {[
                  { label: 'Name', value: activeProvider.name },
                  { label: 'Model', value: activeProvider.default_model },
                  { label: 'Base URL', value: activeProvider.base_url },
                  { label: 'Temperature', value: String(activeProvider.temperature) },
                  { label: 'Max Tokens', value: String(activeProvider.max_tokens ?? 'N/A') },
                  { label: 'API Key', value: activeProvider.api_key_masked },
                ].map((item) => (
                  <div key={item.label} style={{ padding: '10px 14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)', background: 'rgba(10,14,26,0.4)' }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--color-text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 4 }}>{item.label}</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: 'var(--color-text-bright)', wordBreak: 'break-all' }}>{item.value}</div>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="tag tag--positive">ACTIVE</span>
                {health?.status === 'ok' && <span className="tag">HEALTHY</span>}
              </div>
            </div>
          ) : (
            <p style={{ color: 'var(--color-text-muted)', marginTop: 12 }}>No active LLM provider configured.</p>
          )}
        </div>
      </section>

      {/* Test Connection */}
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.1s both' }}>
        <div className="surface-panel__content">
          <p className="eyebrow">TEST CONNECTION</p>
          <div style={{ display: 'grid', gap: 16, marginTop: 12 }}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
              <label className="field-stack" style={{ flex: 1 }}>
                <span className="field-stack__label">Test Prompt</span>
                <input className="input" value={testPrompt} onChange={(e) => setTestPrompt(e.target.value)} placeholder="Say OK" />
              </label>
              <button className="btn btn--accent" onClick={handleTestProvider} disabled={!!testingId || !activeProvider}>
                {testingId === 'active' ? 'Testing...' : 'Test Provider'}
              </button>
            </div>
            {providerTestResult && (
              <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', border: `1px solid ${providerTestResult.success ? 'rgba(61,214,140,0.2)' : 'rgba(242,92,92,0.2)'}`, background: providerTestResult.success ? 'rgba(61,214,140,0.05)' : 'rgba(242,92,92,0.05)' }}>
                <div style={{ display: 'flex', gap: 12, marginBottom: 8 }}>
                  <span className={`tag ${providerTestResult.success ? 'tag--positive' : 'tag--negative'}`}>{providerTestResult.success ? 'SUCCESS' : 'FAILED'}</span>
                  {providerTestResult.model && <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>Model: {providerTestResult.model}</span>}
                  {providerTestResult.latency_ms && <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>{providerTestResult.latency_ms}ms</span>}
                </div>
                <pre style={{ margin: 0, fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--color-text-secondary)', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                  {providerTestResult.content || providerTestResult.error || providerTestResult.message || 'No response'}
                </pre>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Active Chat Test */}
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.2s both' }}>
        <div className="surface-panel__content">
          <p className="eyebrow">CHAT TEST</p>
          <div style={{ display: 'grid', gap: 16, marginTop: 12 }}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
              <label className="field-stack" style={{ flex: 1 }}>
                <span className="field-stack__label">Message</span>
                <input className="input" value={activeChatMessage} onChange={(e) => setActiveChatMessage(e.target.value)} placeholder="Introduce yourself" />
              </label>
              <button className="btn btn--accent" onClick={handleTestChat} disabled={!!testingId}>
                {testingId === 'chat' ? 'Sending...' : 'Send'}
              </button>
            </div>
            {chatTestResult && (
              <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', border: `1px solid ${chatTestResult.success ? 'rgba(61,214,140,0.2)' : 'rgba(242,92,92,0.2)'}`, background: chatTestResult.success ? 'rgba(61,214,140,0.05)' : 'rgba(242,92,92,0.05)' }}>
                <div style={{ display: 'flex', gap: 12, marginBottom: 8 }}>
                  <span className={`tag ${chatTestResult.success ? 'tag--positive' : 'tag--negative'}`}>{chatTestResult.success ? 'SUCCESS' : 'FAILED'}</span>
                  {chatTestResult.model && <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>Model: {chatTestResult.model}</span>}
                </div>
                <pre style={{ margin: 0, fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--color-text-secondary)', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                  {chatTestResult.content || chatTestResult.message || 'No response'}
                </pre>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* All Providers */}
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.3s both' }}>
        <div className="surface-panel__content">
          <p className="eyebrow">ALL PROVIDERS ({providers.length})</p>
          <div style={{ marginTop: 12 }}>
            {providers.length === 0 ? (
              <p style={{ color: 'var(--color-text-muted)' }}>No providers configured.</p>
            ) : (
              <div className="table-shell">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Model</th>
                      <th>Base URL</th>
                      <th>Temp</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {providers.map((p, i) => (
                      <tr key={p.id || i}>
                        <td style={{ fontWeight: 600 }}>{p.name}</td>
                        <td><span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>{p.default_model}</span></td>
                        <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--color-text-secondary)', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.base_url}</td>
                        <td>{p.temperature}</td>
                        <td>{p.is_active ? <span className="tag tag--positive">Active</span> : <span className="tag">Inactive</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </section>
    </section>
  )
}
