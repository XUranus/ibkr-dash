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
      <header className="surface-panel" style={{ animation: 'slideUp 0.5s ease' }}>
        <div className="surface-panel__content" style={{ display: 'grid', gap: 'var(--space-4)' }}>
          {/* Top row: title + account info + auth */}
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 'var(--space-4)', alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div>
              <p className="eyebrow" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: 'var(--color-accent)', boxShadow: '0 0 8px rgba(212,168,67,0.4)' }} />
                {t('app.title')}
              </p>
              <h1 style={{
                margin: 0,
                fontSize: 'clamp(1.8rem, 3.5vw, 2.6rem)',
                letterSpacing: '-0.04em',
                fontWeight: 700,
                color: 'var(--color-text-bright)',
              }}>
                {t('app.subtitle')}
              </h1>
            </div>

            <div style={{ display: 'grid', gap: 12, justifyItems: 'end' }}>
              {/* Auth row */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                <button className="btn btn--ghost btn--sm" onClick={toggleLanguage} style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)' }}>
                  {i18n.language === 'zh-CN' ? 'EN' : '中文'}
                </button>
                <span className="tag" style={{ fontSize: '0.62rem' }}>LIVE</span>
                {!authenticated ? (
                  <button className="btn btn--ghost btn--sm" onClick={() => setShowLogin(true)}>{t('auth.login')}</button>
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.75rem',
                      color: 'var(--color-text-muted)',
                    }}>
                      {username}
                    </span>
                    <button className="btn btn--ghost btn--sm" onClick={handleLogout}>{t('auth.logout')}</button>
                  </div>
                )}
              </div>

              {/* Account metrics strip */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'flex-end' }}>
                {[
                  { label: t('header.date'), value: overview?.report_date ?? '--' },
                  { label: t('header.equity'), value: formatNumber(overview?.total_equity ?? null) },
                  {
                    label: t('header.pnl'),
                    value: formatNumber(overview?.fifo_total_pnl ?? null),
                    className: pnlClass(overview?.fifo_total_pnl),
                  },
                ].map((item) => (
                  <div key={item.label} style={{
                    display: 'flex', alignItems: 'baseline', gap: 8,
                    padding: '6px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--color-border-subtle)',
                    background: 'rgba(10, 14, 26, 0.4)',
                  }}>
                    <span style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.62rem',
                      color: 'var(--color-text-muted)',
                      letterSpacing: '0.1em',
                      textTransform: 'uppercase',
                    }}>
                      {item.label}
                    </span>
                    <strong style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.88rem',
                      fontWeight: 600,
                      color: item.className ? undefined : 'var(--color-text-bright)',
                    }}
                    className={item.className}
                    >
                      {item.value}
                    </strong>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav style={{ display: 'flex', flexWrap: 'wrap', gap: 4, borderTop: '1px solid var(--color-border-subtle)', paddingTop: 'var(--space-3)' }}>
            {navItems.map((item) => (
              <button
                key={item.to}
                className={`btn terminal-nav__button ${isActive(item.to) ? 'is-active' : ''}`}
                onClick={() => navigate(item.to)}
                style={{
                  borderRadius: 'var(--radius-sm)',
                  minHeight: 36,
                  padding: '0 14px',
                  fontSize: '0.82rem',
                  fontWeight: isActive(item.to) ? 600 : 400,
                  color: isActive(item.to) ? 'var(--color-accent-strong)' : 'var(--color-text-secondary)',
                  background: isActive(item.to) ? 'rgba(212,168,67,0.06)' : 'transparent',
                  border: '1px solid transparent',
                  borderColor: isActive(item.to) ? 'rgba(212,168,67,0.2)' : 'transparent',
                }}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Login modal */}
      {showLogin && (
        <div className="modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget) setShowLogin(false) }}>
          <section className="modal-dialog" style={{ width: 'min(400px, 100%)' }}>
            <div style={{ display: 'grid', gap: 24 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
                <div>
                  <p className="eyebrow">ACCESS</p>
                  <h2 style={{ margin: 0, fontSize: '1.4rem', color: 'var(--color-text-bright)' }}>{t('auth.loginTitle')}</h2>
                </div>
                <button className="btn btn--ghost btn--sm" onClick={() => setShowLogin(false)} style={{ minWidth: 36, minHeight: 36, padding: 0 }}>✕</button>
              </div>
              <form style={{ display: 'grid', gap: 14 }} onSubmit={handleLogin}>
                <label className="field-stack">
                  <span className="field-stack__label">{t('auth.username')}</span>
                  <input className="input" value={loginForm.username} onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })} type="text" autoComplete="username" />
                </label>
                <label className="field-stack">
                  <span className="field-stack__label">{t('auth.password')}</span>
                  <input className="input" value={loginForm.password} onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })} type="password" autoComplete="current-password" />
                </label>
                {loginError && <p style={{ margin: 0, color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>{loginError}</p>}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, paddingTop: 4 }}>
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
