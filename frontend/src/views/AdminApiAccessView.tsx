import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import AdminTabs from '@/components/AdminTabs'
import {
  listApiTokens,
  createApiToken,
  revokeApiToken,
  deleteApiToken,
} from '@/api/adminApiTokens'
import type { ApiToken, CreateTokenRequest } from '@/api/adminApiTokens'

const ENDPOINTS = [
  { method: 'GET', path: '/api/mcp', desc: 'API discovery & endpoint list' },
  { method: 'GET', path: '/api/mcp/positions', desc: 'Current positions' },
  { method: 'GET', path: '/api/mcp/account/overview', desc: 'Latest account overview' },
  { method: 'GET', path: '/api/mcp/account/snapshots', desc: 'Historical account snapshots' },
  { method: 'GET', path: '/api/mcp/trades', desc: 'Trade history' },
  { method: 'GET', path: '/api/mcp/cash-flows', desc: 'Cash flow history' },
  { method: 'GET', path: '/api/mcp/dividends', desc: 'Dividend history' },
  { method: 'GET', path: '/api/mcp/charts/equity-curve', desc: 'Equity curve' },
  { method: 'GET', path: '/api/mcp/charts/performance-calendar', desc: 'Performance calendar' },
  { method: 'GET', path: '/api/mcp/reviews', desc: 'Daily position reviews' },
  { method: 'GET', path: '/api/mcp/portfolio/review', desc: 'Portfolio review reports' },
]

const SCOPES = [
  { value: 'read', label: 'All Data (read)' },
  { value: 'read:positions', label: 'Positions' },
  { value: 'read:account', label: 'Account' },
  { value: 'read:trades', label: 'Trades' },
  { value: 'read:cashflows', label: 'Cash Flows & Dividends' },
  { value: 'read:charts', label: 'Charts' },
  { value: 'read:reviews', label: 'Reviews' },
]

export default function AdminApiAccessView() {
  const { t } = useTranslation()
  const [tokens, setTokens] = useState<ApiToken[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [newTokenResult, setNewTokenResult] = useState<string | null>(null)
  const [form, setForm] = useState<CreateTokenRequest>({
    name: '',
    description: '',
    scopes: ['read'],
  })
  const [error, setError] = useState('')

  const loadTokens = useCallback(async () => {
    setLoading(true)
    try {
      setTokens(await listApiTokens())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tokens')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadTokens() }, [loadTokens])

  const handleCreate = async () => {
    setError('')
    try {
      const result = await createApiToken(form)
      setNewTokenResult(result.token ?? null)
      setForm({ name: '', description: '', scopes: ['read'] })
      void loadTokens()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create token')
    }
  }

  const handleRevoke = async (id: number) => {
    if (!confirm(t('adminApiTokens.revokeConfirm'))) return
    try {
      await revokeApiToken(id)
      void loadTokens()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to revoke token')
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm(t('adminApiTokens.deleteConfirm'))) return
    try {
      await deleteApiToken(id)
      void loadTokens()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete token')
    }
  }

  const copyToken = async () => {
    if (!newTokenResult) return
    try {
      await navigator.clipboard.writeText(newTokenResult)
    } catch {
      // Fallback for non-secure contexts (HTTP)
      const el = document.createElement('textarea')
      el.value = newTokenResult
      el.style.position = 'fixed'
      el.style.opacity = '0'
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }
  }

  const toggleScope = (scope: string) => {
    setForm(prev => {
      const current = prev.scopes || []
      if (scope === 'read') {
        return { ...prev, scopes: current.includes('read') ? [] : ['read'] }
      }
      const withoutRead = current.filter(s => s !== 'read')
      const has = withoutRead.includes(scope)
      return {
        ...prev,
        scopes: has ? withoutRead.filter(s => s !== scope) : [...withoutRead, scope],
      }
    })
  }

  const baseUrl = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8080'

  return (
    <section className="page-section">
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease' }}>
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">{t('adminSystem.adminLabel')}</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-bright)' }}>
                {t('adminApiTokens.title')}
              </h2>
              <p style={{ margin: '4px 0 0', fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                {t('adminApiTokens.subtitle')}
              </p>
            </div>
          </div>
          <AdminTabs />
        </div>
      </section>

      {error && (
        <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(242,92,92,0.2)', background: 'rgba(242,92,92,0.05)', color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
          {error}
        </div>
      )}

      {/* Newly created token banner */}
      {newTokenResult && (
        <section className="surface-panel" style={{ animation: 'slideUp 0.3s ease', border: '1px solid rgba(106,190,126,0.3)' }}>
          <div className="surface-panel__content">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span style={{ color: 'var(--color-positive)', fontWeight: 600 }}>✓ {t('adminApiTokens.tokenCreated')}</span>
            </div>
            <p style={{ color: 'var(--color-negative)', fontSize: '0.82rem', marginBottom: 8 }}>
              ⚠ {t('adminApiTokens.tokenCreatedWarning')}
            </p>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <code style={{
                flex: 1, padding: '10px 14px', borderRadius: 'var(--radius-sm)',
                background: 'rgba(10,14,26,0.6)', fontFamily: 'var(--font-mono)',
                fontSize: '0.82rem', color: 'var(--color-text-bright)',
                wordBreak: 'break-all', userSelect: 'all',
              }}>
                {newTokenResult}
              </code>
              <button className="btn btn--accent" onClick={copyToken} style={{ whiteSpace: 'nowrap' }}>
                Copy
              </button>
              <button className="btn" onClick={() => setNewTokenResult(null)} style={{ whiteSpace: 'nowrap' }}>
                {t('common.close', { defaultValue: 'Close' })}
              </button>
            </div>
          </div>
        </section>
      )}

      {/* Create form */}
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.1s both' }}>
        <div className="surface-panel__content">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: showCreate ? 16 : 0 }}>
            <h3 style={{ margin: 0, fontSize: '0.95rem', color: 'var(--color-text-bright)' }}>
              {t('adminApiTokens.createToken')}
            </h3>
            <button
              className="btn btn--accent"
              onClick={() => setShowCreate(!showCreate)}
            >
              {showCreate ? '−' : '+'} {t('adminApiTokens.createToken')}
            </button>
          </div>

          {showCreate && (
            <div style={{ display: 'grid', gap: 12, marginTop: 12 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--color-text-muted)', marginBottom: 4 }}>
                    {t('adminApiTokens.tokenName')} *
                  </label>
                  <input
                    type="text"
                    placeholder={t('adminApiTokens.tokenNamePlaceholder')}
                    value={form.name}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                    style={{
                      width: '100%', padding: '8px 12px', borderRadius: 'var(--radius-sm)',
                      background: 'rgba(10,14,26,0.6)', border: '1px solid rgba(255,255,255,0.08)',
                      color: 'var(--color-text-bright)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem',
                      outline: 'none', boxSizing: 'border-box',
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--color-text-muted)', marginBottom: 4 }}>
                    {t('adminApiTokens.description')}
                  </label>
                  <input
                    type="text"
                    placeholder={t('adminApiTokens.descriptionPlaceholder')}
                    value={form.description}
                    onChange={e => setForm({ ...form, description: e.target.value })}
                    style={{
                      width: '100%', padding: '8px 12px', borderRadius: 'var(--radius-sm)',
                      background: 'rgba(10,14,26,0.6)', border: '1px solid rgba(255,255,255,0.08)',
                      color: 'var(--color-text-bright)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem',
                      outline: 'none', boxSizing: 'border-box',
                    }}
                  />
                </div>
              </div>

              {/* Scopes */}
              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--color-text-muted)', marginBottom: 6 }}>
                  {t('adminApiTokens.scopes')}
                  <span style={{ marginLeft: 8, fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
                    {t('adminApiTokens.scopesHint')}
                  </span>
                </label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {SCOPES.map(s => {
                    const active = form.scopes?.includes(s.value)
                    return (
                      <button
                        key={s.value}
                        onClick={() => toggleScope(s.value)}
                        style={{
                          padding: '4px 10px', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem',
                          fontFamily: 'var(--font-mono)', cursor: 'pointer', transition: 'all 0.15s',
                          background: active ? 'rgba(99,179,237,0.15)' : 'rgba(10,14,26,0.4)',
                          border: active ? '1px solid rgba(99,179,237,0.4)' : '1px solid rgba(255,255,255,0.08)',
                          color: active ? 'var(--color-accent)' : 'var(--color-text-muted)',
                        }}
                      >
                        {s.label}
                      </button>
                    )
                  })}
                </div>
              </div>

              <button
                className="btn btn--accent"
                onClick={handleCreate}
                disabled={!form.name.trim()}
                style={{ justifySelf: 'start' }}
              >
                {t('adminApiTokens.createToken')}
              </button>
            </div>
          )}
        </div>
      </section>

      {/* Token list */}
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.2s both' }}>
        <div className="surface-panel__content">
          <h3 style={{ margin: '0 0 12px', fontSize: '0.95rem', color: 'var(--color-text-bright)' }}>
            API Tokens
          </h3>

          {loading ? (
            <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>{t('common.loading')}</p>
          ) : tokens.length === 0 ? (
            <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', fontFamily: 'var(--font-mono)' }}>
              {t('adminApiTokens.noTokens')}
            </p>
          ) : (
            <div style={{ display: 'grid', gap: 6 }}>
              {tokens.map(tok => {
                const isRevoked = tok.revoked
                return (
                  <div
                    key={tok.id}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr auto auto auto auto',
                      alignItems: 'center',
                      gap: 12,
                      padding: '8px 12px',
                      borderRadius: 'var(--radius-sm)',
                      background: 'rgba(10,14,26,0.4)',
                      opacity: isRevoked ? 0.5 : 1,
                    }}
                  >
                    {/* Name & preview */}
                    <div>
                      <div style={{ fontSize: '0.85rem', color: 'var(--color-text-bright)', fontWeight: 500 }}>
                        {tok.name || '—'}
                      </div>
                      <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)' }}>
                        {tok.token_preview}
                      </div>
                    </div>

                    {/* Status */}
                    <span className={`tag ${isRevoked ? 'tag--negative' : 'tag--positive'}`} style={{ fontSize: '0.72rem' }}>
                      {isRevoked ? t('adminApiTokens.revoked') : t('adminApiTokens.active')}
                    </span>

                    {/* Last used */}
                    <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                      {tok.last_used_at || t('adminApiTokens.never')}
                    </span>

                    {/* Created */}
                    <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                      {tok.created_at?.split('T')[0] ?? '—'}
                    </span>

                    {/* Actions */}
                    <div style={{ display: 'flex', gap: 4 }}>
                      {!isRevoked && (
                        <button
                          className="btn"
                          onClick={() => handleRevoke(tok.id)}
                          style={{ padding: '3px 8px', fontSize: '0.72rem' }}
                        >
                          {t('adminApiTokens.revoke')}
                        </button>
                      )}
                      <button
                        className="btn"
                        onClick={() => handleDelete(tok.id)}
                        style={{ padding: '3px 8px', fontSize: '0.72rem', color: 'var(--color-negative)' }}
                      >
                        {t('adminApiTokens.delete')}
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </section>

      {/* Usage guide */}
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.3s both' }}>
        <div className="surface-panel__content">
          <h3 style={{ margin: '0 0 12px', fontSize: '0.95rem', color: 'var(--color-text-bright)' }}>
            {t('adminApiTokens.bearerAuth')}
          </h3>
          <p style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', marginBottom: 12 }}>
            {t('adminApiTokens.bearerAuthHint')}
          </p>

          <div style={{
            padding: '12px 14px', borderRadius: 'var(--radius-sm)',
            background: 'rgba(10,14,26,0.6)', fontFamily: 'var(--font-mono)', fontSize: '0.8rem',
            color: 'var(--color-text-bright)', marginBottom: 16,
          }}>
            <div style={{ color: 'var(--color-text-muted)', marginBottom: 4 }}># {t('adminApiTokens.mcpBaseUrl')}</div>
            <div>{baseUrl}/api/mcp</div>
            <div style={{ marginTop: 8, color: 'var(--color-text-muted)' }}># Example: list positions</div>
            <div>curl -H "Authorization: Bearer ibkr_xxx..." {baseUrl}/api/mcp/positions</div>
          </div>

          <h4 style={{ margin: '0 0 8px', fontSize: '0.85rem', color: 'var(--color-text-bright)' }}>
            {t('adminApiTokens.availableEndpoints')}
          </h4>
          <div style={{ display: 'grid', gap: 2 }}>
            {ENDPOINTS.map(ep => (
              <div
                key={ep.path}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '60px 1fr 1fr',
                  gap: 12,
                  padding: '5px 10px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'rgba(10,14,26,0.3)',
                  fontSize: '0.78rem',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                <span style={{ color: 'var(--color-positive)', fontWeight: 600 }}>{ep.method}</span>
                <span style={{ color: 'var(--color-text-bright)' }}>{ep.path}</span>
                <span style={{ color: 'var(--color-text-muted)' }}>{ep.desc}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </section>
  )
}
