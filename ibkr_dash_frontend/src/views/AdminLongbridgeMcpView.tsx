import { useState, useEffect, useCallback } from 'react'
import {
  completeLongbridgeOpenApiOauth,
  disconnectLongbridgeOpenApiOauth,
  fetchLongbridgeOpenApiHealth,
  fetchLongbridgeOpenApiStatus,
  fetchLongbridgeUnifiedHealth,
  fetchLongbridgeUnifiedStatus,
  refreshLongbridgeUnifiedOauth,
  startLongbridgeOpenApiOauth,
  testLongbridgeMcp,
} from '@/api/adminLongbridgeMcp'
import AdminTabs from '@/components/AdminTabs'
import type { LongbridgeMcpTestResponse, LongbridgeOpenApiHealth, LongbridgeOpenApiOauthStartResponse, LongbridgeOpenApiStatus, LongbridgeUnifiedOAuthStatus } from '@/types/adminLongbridgeMcp'

export default function AdminLongbridgeMcpView() {
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)
  const [completing, setCompleting] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [disconnecting, setDisconnecting] = useState(false)
  const [checking, setChecking] = useState(false)
  const [testing, setTesting] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [noticeMessage, setNoticeMessage] = useState('')
  const [unifiedStatus, setUnifiedStatus] = useState<LongbridgeUnifiedOAuthStatus | null>(null)
  const [openApiStatus, setOpenApiStatus] = useState<LongbridgeOpenApiStatus | null>(null)
  const [oauthStart, setOauthStart] = useState<LongbridgeOpenApiOauthStartResponse | null>(null)
  const [openApiHealth, setOpenApiHealth] = useState<LongbridgeOpenApiHealth | null>(null)
  const [mcpTestResult, setMcpTestResult] = useState<LongbridgeMcpTestResponse | null>(null)
  const [scope, setScope] = useState('')
  const [code, setCode] = useState('')
  const [state, setState] = useState('')

  function callbackUrl(): string { return `${window.location.origin}/api/admin/longbridge/openapi/oauth/callback` }

  const loadData = useCallback(async () => {
    setLoading(true); setErrorMessage('')
    try {
      const [unified, openapi] = await Promise.all([fetchLongbridgeUnifiedStatus(), fetchLongbridgeOpenApiStatus()])
      setUnifiedStatus(unified); setOpenApiStatus(openapi)
      if (openapi.scope) setScope(openapi.scope)
    } catch (error) { setErrorMessage(error instanceof Error ? error.message : 'Failed to load') }
    finally { setLoading(false) }
  }, [])

  async function startOauth(): Promise<void> {
    setStarting(true); setErrorMessage(''); setNoticeMessage(''); setOauthStart(null)
    try {
      const result = await startLongbridgeOpenApiOauth({ redirect_uri: callbackUrl(), scope: scope.trim() || undefined })
      setOauthStart(result); setState(result.state)
      window.open(result.authorization_url, '_blank', 'noopener,noreferrer')
      setNoticeMessage('Opened LongBridge authorization page. After authorization, OpenAPI/SDK and MCP will share the token.')
      await loadData()
    } catch (error) { setErrorMessage(error instanceof Error ? error.message : 'OAuth start failed') }
    finally { setStarting(false) }
  }

  async function completeOauth(): Promise<void> {
    setCompleting(true); setErrorMessage(''); setNoticeMessage('')
    try {
      const response = await completeLongbridgeOpenApiOauth({ code: code.trim(), state: state.trim() })
      if (response.status) setOpenApiStatus(response.status); setCode(''); setNoticeMessage(response.message)
      await loadData()
    } catch (error) { setErrorMessage(error instanceof Error ? error.message : 'OAuth complete failed') }
    finally { setCompleting(false) }
  }

  async function refreshOauth(): Promise<void> {
    setRefreshing(true); setErrorMessage(''); setNoticeMessage('')
    try { const r = await refreshLongbridgeUnifiedOauth(); setUnifiedStatus(r.status); setNoticeMessage(r.message); await loadData() }
    catch (error) { setErrorMessage(error instanceof Error ? error.message : 'Refresh failed') }
    finally { setRefreshing(false) }
  }

  async function disconnectOauth(): Promise<void> {
    setDisconnecting(true); setErrorMessage(''); setNoticeMessage(''); setMcpTestResult(null); setOpenApiHealth(null)
    try { const r = await disconnectLongbridgeOpenApiOauth(); if (r.status) setOpenApiStatus(r.status); setNoticeMessage(r.message); await loadData() }
    catch (error) { setErrorMessage(error instanceof Error ? error.message : 'Disconnect failed') }
    finally { setDisconnecting(false) }
  }

  async function checkHealth(): Promise<void> {
    setChecking(true); setErrorMessage(''); setNoticeMessage('')
    try { const [oh, uh] = await Promise.all([fetchLongbridgeOpenApiHealth(), fetchLongbridgeUnifiedHealth()]); setOpenApiHealth(oh); setOpenApiStatus(oh.oauth_status); setUnifiedStatus(uh); setNoticeMessage(uh.message) }
    catch (error) { setErrorMessage(error instanceof Error ? error.message : 'Health check failed') }
    finally { setChecking(false) }
  }

  async function runMcpTest(): Promise<void> {
    setTesting(true); setErrorMessage(''); setNoticeMessage(''); setMcpTestResult(null)
    try { const r = await testLongbridgeMcp(); setMcpTestResult(r); setNoticeMessage(r.message); await loadData() }
    catch (error) { setErrorMessage(error instanceof Error ? error.message : 'MCP test failed') }
    finally { setTesting(false) }
  }

  useEffect(() => { void loadData() }, [loadData])

  const statusLabel = unifiedStatus?.openapi_connected && unifiedStatus?.mcp_effective_connected ? 'UNIFIED OAUTH CONNECTED' : 'AUTH REQUIRED'
  const statusClass = unifiedStatus?.openapi_connected ? 'tag-positive' : 'tag-negative'
  const metaGrid: React.CSSProperties = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, margin: 0 }
  const metaItem: React.CSSProperties = { padding: 12, border: '1px solid rgba(148, 163, 184, 0.18)', borderRadius: 8, background: 'rgba(15, 23, 42, 0.42)' }

  return (
    <section className="page-section">
      <section className="surface-panel">
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">ADMIN</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem' }}>LongBridge Unified Auth</h2>
              <p className="panel-subtitle">OpenAPI OAuth is the single auth source; OpenAPI/SDK and hosted MCP share the same token.</p>
            </div>
            <span className={statusClass} style={{ padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: '0.82rem', fontWeight: 600 }}>{statusLabel}</span>
          </div>
          <AdminTabs />
        </div>
      </section>

      {loading ? <section className="surface-panel"><div className="surface-panel__content"><div className="empty-state">Loading...</div></div></section> : (
        <>
          {noticeMessage && <p style={{ margin: 0, padding: '12px 16px', borderRadius: 'var(--radius-md)', color: 'var(--color-positive)', background: 'rgba(9, 47, 39, 0.48)', border: '1px solid rgba(52, 210, 163, 0.18)' }}>{noticeMessage}</p>}
          {errorMessage && <p style={{ margin: 0, padding: '12px 16px', borderRadius: 'var(--radius-md)', color: 'var(--color-negative)', background: 'rgba(55, 18, 28, 0.48)', border: '1px solid rgba(255, 107, 122, 0.18)' }}>{errorMessage}</p>}

          <section className="surface-panel"><div className="surface-panel__content">
            <h3 className="panel-title">Unified Auth Status</h3>
            <dl style={metaGrid}>
              {[['Auth Mode', 'OpenAPI OAuth'], ['Token Source', unifiedStatus?.token_source === 'openapi_oauth_store' ? 'OpenAPI OAuth Store' : '--'], ['OpenAPI/SDK', unifiedStatus?.openapi_connected ? 'Connected' : 'Not connected'], ['MCP', unifiedStatus?.mcp_effective_connected ? 'Connected' : 'Not connected'], ['Client ID', unifiedStatus?.client_id_masked || '--'], ['Refresh', unifiedStatus?.refresh_available ? 'Available' : 'Unavailable'], ['Expires In', `${unifiedStatus?.expires_in_seconds ?? '--'}s`], ['Message', unifiedStatus?.message || '--']].map(([k, v]) => (
                <div key={k} style={metaItem}><dt style={{ marginBottom: 6, color: 'var(--color-text-secondary)', fontSize: 12 }}>{k}</dt><dd style={{ margin: 0, overflowWrap: 'anywhere', color: 'var(--color-text-primary)' }}>{String(v)}</dd></div>
              ))}
            </dl>
          </div></section>

          <section className="surface-panel"><div className="surface-panel__content">
            <h3 className="panel-title">LongBridge OAuth</h3>
            <p className="panel-subtitle">Complete one OAuth authorization and both OpenAPI/SDK and MCP will share it.</p>
            <dl style={metaGrid}>
              {[['Client ID', openApiStatus?.client_id_configured ? openApiStatus.client_id : 'Not initialized'], ['Access Token', openApiStatus?.access_token_masked || '--'], ['Refresh Token', openApiStatus?.has_refresh_token ? 'Exists' : 'None'], ['Config File', openApiStatus?.config_file || '--']].map(([k, v]) => (
                <div key={k} style={metaItem}><dt style={{ marginBottom: 6, color: 'var(--color-text-secondary)', fontSize: 12 }}>{k}</dt><dd style={{ margin: 0, overflowWrap: 'anywhere', color: 'var(--color-text-primary)' }}>{String(v)}</dd></div>
              ))}
            </dl>
            {openApiStatus?.last_error && <p style={{ marginTop: 16, padding: 12, borderRadius: 8, background: 'rgba(248, 113, 113, 0.12)', color: 'var(--color-text-primary)' }}>Last error: {openApiStatus.last_error}</p>}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginTop: 16 }}>
              <label className="field-stack"><span className="field-stack__label">Scope</span><input className="input" value={scope} onChange={(e) => setScope(e.target.value)} placeholder="Leave empty for default" /></label>
              <label className="field-stack"><span className="field-stack__label">Auth Code</span><input className="input" value={code} onChange={(e) => setCode(e.target.value)} placeholder="Paste code here" /></label>
              <label className="field-stack"><span className="field-stack__label">State</span><input className="input" value={state} onChange={(e) => setState(e.target.value)} placeholder="Auto-filled after start" /></label>
            </div>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 16 }}>
              <button className="btn btn--accent" disabled={starting} onClick={() => void startOauth()}>{starting ? 'Starting...' : 'Start OAuth'}</button>
              <button className="btn btn--ghost" disabled={completing || !code.trim() || !state.trim()} onClick={() => void completeOauth()}>{completing ? 'Completing...' : 'Complete Auth'}</button>
              <button className="btn btn--ghost" disabled={refreshing || !openApiStatus?.refresh_available} onClick={() => void refreshOauth()}>{refreshing ? 'Refreshing...' : 'Refresh Token'}</button>
              <button className="btn btn--ghost" disabled={disconnecting || !openApiStatus?.has_access_token} onClick={() => void disconnectOauth()}>{disconnecting ? 'Disconnecting...' : 'Disconnect'}</button>
              <button className="btn btn--ghost" disabled={checking} onClick={() => void checkHealth()}>{checking ? 'Checking...' : 'Health Check'}</button>
            </div>
            {oauthStart && <div style={{ marginTop: 16, padding: 12, borderRadius: 8, background: 'rgba(14, 165, 233, 0.1)', color: 'var(--color-text-primary)', overflowWrap: 'anywhere' }}><p>Authorization link generated. If browser did not open, use: <a href={oauthStart.authorization_url} target="_blank" rel="noreferrer" style={{ color: 'var(--color-accent)' }}>{oauthStart.authorization_url}</a></p></div>}
            {openApiHealth && <dl style={{ ...metaGrid, marginTop: 16 }}>{[['SDK Installed', openApiHealth.sdk_loaded ? 'Yes' : 'No'], ['SDK OAuth Support', openApiHealth.sdk_oauth_supported ? 'Yes' : 'No'], ['Can Init Config', openApiHealth.can_initialize_config ? 'Yes' : 'No'], ['Message', openApiHealth.message]].map(([k, v]) => <div key={k} style={metaItem}><dt style={{ marginBottom: 6, color: 'var(--color-text-secondary)', fontSize: 12 }}>{k}</dt><dd style={{ margin: 0, color: 'var(--color-text-primary)' }}>{String(v)}</dd></div>)}</dl>}
          </div></section>

          <section className="surface-panel"><div className="surface-panel__content">
            <h3 className="panel-title">MCP Tool Health</h3>
            <p className="panel-subtitle">MCP only exposes read-only market tools.</p>
            <dl style={metaGrid}>
              {[['MCP Endpoint', unifiedStatus?.mcp_endpoint || '--'], ['MCP Enabled', unifiedStatus?.mcp_endpoint ? 'Configured' : 'Not configured'], ['Auth Mode', unifiedStatus?.auth_mode || '--'], ['Token Source', unifiedStatus?.token_source || '--']].map(([k, v]) => (
                <div key={k} style={metaItem}><dt style={{ marginBottom: 6, color: 'var(--color-text-secondary)', fontSize: 12 }}>{k}</dt><dd style={{ margin: 0, color: 'var(--color-text-primary)' }}>{String(v)}</dd></div>
              ))}
            </dl>
            <div style={{ marginTop: 16 }}>
              <button className="btn btn--accent" disabled={testing} onClick={() => void runMcpTest()}>{testing ? 'Testing...' : 'Test MCP'}</button>
            </div>
            {mcpTestResult && <dl style={{ ...metaGrid, marginTop: 16 }}>{[['tools/list', mcpTestResult.success ? 'Available' : 'Unavailable'], ['Tool Count', mcpTestResult.tool_count ?? '--'], ['Error Code', mcpTestResult.error_code || '--'], ['Message', mcpTestResult.message]].map(([k, v]) => <div key={k} style={metaItem}><dt style={{ marginBottom: 6, color: 'var(--color-text-secondary)', fontSize: 12 }}>{k}</dt><dd style={{ margin: 0, color: 'var(--color-text-primary)' }}>{String(v)}</dd></div>)}</dl>}
            {mcpTestResult?.quote_sample && <pre style={{ marginTop: 16, padding: 12, maxHeight: 280, overflow: 'auto', borderRadius: 8, background: 'rgba(2, 6, 23, 0.5)', color: 'var(--color-text-primary)' }}>{JSON.stringify(mcpTestResult.quote_sample, null, 2)}</pre>}
          </div></section>
        </>
      )}
    </section>
  )
}
