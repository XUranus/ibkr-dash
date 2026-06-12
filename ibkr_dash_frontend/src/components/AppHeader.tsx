import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/hooks/useAuth'
import { useAccountOverview } from '@/hooks/useAccountOverview'
import { formatNumber, pnlClass } from '@/utils/format'

export default function AppHeader() {
  const { t, i18n } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const { authenticated, username, loading: authLoading, ensureAuth, loginWithCredentials, logout } = useAuth()
  const { overview, ensureLoaded } = useAccountOverview()
  const [showLogin, setShowLogin] = useState(false)
  const [loginForm, setLoginForm] = useState({ username: '', password: '' })
  const [loginError, setLoginError] = useState('')

  const baseNavItems = [
    { label: t('nav.dashboard'), to: '/' },
    { label: t('nav.positions'), to: '/positions' },
  ]

  const protectedNavItems = [
    { label: t('nav.trades'), to: '/trades' },
    { label: t('nav.cashFlows'), to: '/cash-flows' },
    { label: t('nav.dividends'), to: '/dividends' },
    { label: t('nav.aiDecision'), to: '/trade-decision' },
    { label: t('nav.aiReview'), to: '/trade-review' },
    { label: t('nav.copilot'), to: '/copilot' },
    { label: t('nav.admin'), to: '/admin/system' },
  ]

  useEffect(() => {
    void ensureAuth()
    void ensureLoaded()
  }, [])

  const navItems = authenticated ? [...baseNavItems, ...protectedNavItems] : baseNavItems

  function isActive(path: string): boolean {
    if (location.pathname === path) return true
    if (path.startsWith('/admin')) return location.pathname.startsWith('/admin')
    return false
  }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoginError('')
    try {
      await loginWithCredentials(loginForm.username.trim(), loginForm.password)
      setShowLogin(false)
      setLoginForm({ username: '', password: '' })
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : t('auth.loginFailed'))
    }
  }

  async function handleLogout() {
    await logout()
    if (location.pathname !== '/') navigate('/')
  }

  function toggleLanguage() {
    const next = i18n.language === 'zh-CN' ? 'en' : 'zh-CN'
    void i18n.changeLanguage(next)
  }

  return (
    <>
      <header style={{
        background: 'var(--color-bg-panel)',
        borderBottom: '1px solid var(--color-border)',
        padding: '0 16px',
      }}>
        {/* Top bar: title + account metrics + auth */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 16,
          height: 40,
          flexWrap: 'wrap',
        }}>
          {/* Left: title */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.72rem',
              fontWeight: 700,
              color: 'var(--color-text-bright)',
              letterSpacing: '0.04em',
            }}>
              IBKR DASH
            </span>
            <span style={{
              width: 6, height: 6, borderRadius: '50%',
              background: 'var(--color-positive)',
              display: 'inline-block',
            }} />
          </div>

          {/* Center: account metrics strip */}
          <div style={{ display: 'flex', gap: 0, overflow: 'auto' }}>
            {[
              { label: t('header.equity'), value: formatNumber(overview?.total_equity ?? null) },
              { label: t('header.pnl'), value: formatNumber(overview?.fifo_total_pnl ?? null), className: pnlClass(overview?.fifo_total_pnl) },
              { label: t('header.date'), value: overview?.report_date ?? '--' },
            ].map((item) => (
              <div key={item.label} style={{
                display: 'flex', alignItems: 'baseline', gap: 6,
                padding: '0 14px',
                borderRight: '1px solid var(--color-border)',
                whiteSpace: 'nowrap',
              }}>
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.58rem',
                  color: 'var(--color-text-muted)',
                  letterSpacing: '0.06em',
                  textTransform: 'uppercase',
                }}>
                  {item.label}
                </span>
                <strong
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    color: item.className ? undefined : 'var(--color-text-bright)',
                    fontVariantNumeric: 'tabular-nums',
                  }}
                  className={item.className}
                >
                  {item.value}
                </strong>
              </div>
            ))}
          </div>

          {/* Right: auth + language */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button className="btn btn--ghost btn--sm" onClick={toggleLanguage} style={{
              fontSize: '0.65rem', fontFamily: 'var(--font-mono)', padding: '0 6px', minHeight: 22,
            }}>
              {i18n.language === 'zh-CN' ? 'EN' : '中文'}
            </button>
            {!authenticated ? (
              <button className="btn btn--ghost btn--sm" onClick={() => setShowLogin(true)} style={{ minHeight: 22, padding: '0 8px', fontSize: '0.7rem' }}>
                {t('auth.login')}
              </button>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.68rem',
                  color: 'var(--color-text-muted)',
                }}>
                  {username}
                </span>
                <button className="btn btn--ghost btn--sm" onClick={handleLogout} style={{ minHeight: 22, padding: '0 8px', fontSize: '0.7rem' }}>
                  {t('auth.logout')}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Navigation tabs */}
        <nav style={{
          display: 'flex',
          gap: 0,
          borderTop: '1px solid var(--color-border-subtle)',
        }}>
          {navItems.map((item) => {
            const active = isActive(item.to)
            return (
              <button
                key={item.to}
                onClick={() => navigate(item.to)}
                style={{
                  minHeight: 30,
                  padding: '0 12px',
                  border: 'none',
                  borderBottom: active ? '2px solid var(--color-accent)' : '2px solid transparent',
                  background: 'transparent',
                  color: active ? 'var(--color-text-bright)' : 'var(--color-text-secondary)',
                  fontFamily: 'var(--font-body)',
                  fontSize: '0.75rem',
                  fontWeight: active ? 600 : 400,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                {item.label}
              </button>
            )
          })}
        </nav>
      </header>

      {/* Login modal */}
      {showLogin && (
        <div className="modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget) setShowLogin(false) }}>
          <section className="modal-dialog" style={{ width: 'min(380px, 100%)' }}>
            <div style={{ display: 'grid', gap: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                <div>
                  <p className="eyebrow">ACCESS</p>
                  <h2 style={{ margin: 0, fontSize: '1rem', color: 'var(--color-text-bright)' }}>{t('auth.loginTitle')}</h2>
                </div>
                <button className="btn btn--ghost btn--sm" onClick={() => setShowLogin(false)} style={{ minWidth: 28, minHeight: 28, padding: 0, fontSize: '0.8rem' }}>✕</button>
              </div>
              <form style={{ display: 'grid', gap: 10 }} onSubmit={handleLogin}>
                <label className="field-stack">
                  <span className="field-stack__label">{t('auth.username')}</span>
                  <input className="input" value={loginForm.username} onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })} type="text" autoComplete="username" />
                </label>
                <label className="field-stack">
                  <span className="field-stack__label">{t('auth.password')}</span>
                  <input className="input" value={loginForm.password} onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })} type="password" autoComplete="current-password" />
                </label>
                {loginError && <p style={{ margin: 0, color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>{loginError}</p>}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, paddingTop: 4 }}>
                  <button type="button" className="btn btn--ghost" onClick={() => setShowLogin(false)}>{t('auth.cancel')}</button>
                  <button type="submit" className="btn btn--accent" disabled={authLoading}>{t('auth.login')}</button>
                </div>
              </form>
            </div>
          </section>
        </div>
      )}
    </>
  )
}
