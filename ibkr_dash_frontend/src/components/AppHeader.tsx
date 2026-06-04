import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { useAccountOverview } from '@/hooks/useAccountOverview'
import { formatNumber, pnlClass } from '@/utils/format'

const baseNavItems = [
  { label: 'Dashboard', to: '/' },
  { label: 'Positions', to: '/positions' },
]

const protectedNavItems = [
  { label: 'Trades', to: '/trades' },
  { label: 'Cash Flows', to: '/cash-flows' },
  { label: 'Dividends', to: '/dividends' },
  { label: 'AI Decision', to: '/trade-decision' },
  { label: 'AI Review', to: '/trade-review' },
  { label: 'Copilot', to: '/copilot' },
  { label: 'Admin', to: '/admin/system' },
]

export default function AppHeader() {
  const location = useLocation()
  const navigate = useNavigate()
  const { authenticated, username, loading: authLoading, ensureAuth, loginWithCredentials, logout } = useAuth()
  const { overview, ensureLoaded } = useAccountOverview()
  const [showLogin, setShowLogin] = useState(false)
  const [loginForm, setLoginForm] = useState({ username: '', password: '' })
  const [loginError, setLoginError] = useState('')

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
      setLoginError(err instanceof Error ? err.message : 'Login failed')
    }
  }

  async function handleLogout() {
    await logout()
    if (location.pathname !== '/') navigate('/')
  }

  return (
    <>
      <header className="surface-panel">
        <div className="surface-panel__content" style={{ display: 'grid', gap: 'var(--space-4)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 'var(--space-4)', alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div>
              <p className="eyebrow">IBKR DASHBOARD</p>
              <h1 style={{ margin: 0, fontSize: 'clamp(2rem, 4vw, 3rem)', letterSpacing: '-0.04em' }}>
                Portfolio Analytics
              </h1>
            </div>
            <div style={{ display: 'grid', gap: 14, justifyItems: 'end' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                <span className="tag tag--accent">LIVE API</span>
                {!authenticated ? (
                  <button className="btn btn--ghost" onClick={() => setShowLogin(true)}>Login</button>
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span className="terminal-note">Logged in: {username}</span>
                    <button className="btn btn--ghost" onClick={handleLogout}>Logout</button>
                  </div>
                )}
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 14, justifyContent: 'flex-end' }}>
                <div style={{ display: 'grid', gap: 4, minWidth: 116, padding: '0.3rem 0.7rem', border: '1px solid rgba(74, 196, 255, 0.16)', borderRadius: 14, background: 'rgba(10, 21, 44, 0.22)' }}>
                  <span className="terminal-note">Report Date</span>
                  <strong style={{ fontSize: '1.05rem' }}>{overview?.report_date ?? '--'}</strong>
                </div>
                <div style={{ display: 'grid', gap: 4, minWidth: 116, padding: '0.3rem 0.7rem', border: '1px solid rgba(74, 196, 255, 0.16)', borderRadius: 14, background: 'rgba(10, 21, 44, 0.22)' }}>
                  <span className="terminal-note">Total Equity</span>
                  <strong style={{ fontSize: '1.05rem' }}>{formatNumber(overview?.total_equity ?? null)}</strong>
                </div>
                <div style={{ display: 'grid', gap: 4, minWidth: 116, padding: '0.3rem 0.7rem', border: '1px solid rgba(74, 196, 255, 0.16)', borderRadius: 14, background: 'rgba(10, 21, 44, 0.22)' }}>
                  <span className="terminal-note">Total P&L</span>
                  <strong className={pnlClass(overview?.fifo_total_pnl)} style={{ fontSize: '1.05rem' }}>
                    {formatNumber(overview?.fifo_total_pnl ?? null)}
                  </strong>
                </div>
              </div>
            </div>
          </div>

          <nav style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {navItems.map((item) => (
              <button
                key={item.to}
                className={`btn terminal-nav__button ${isActive(item.to) ? 'is-active' : ''}`}
                onClick={() => navigate(item.to)}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {showLogin && (
        <div className="modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget) setShowLogin(false) }}>
          <section className="modal-dialog" style={{ width: 'min(460px, 100%)' }}>
            <div style={{ display: 'grid', gap: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
                <div>
                  <p className="eyebrow">ACCESS</p>
                  <h2 style={{ margin: 0, fontSize: '1.65rem' }}>Login to view trades and cash flows</h2>
                </div>
                <button className="btn btn--ghost" onClick={() => setShowLogin(false)} style={{ minWidth: 44, minHeight: 44 }}>✕</button>
              </div>
              <form style={{ display: 'grid', gap: 16 }} onSubmit={handleLogin}>
                <label className="field-stack">
                  <span className="field-stack__label">Username</span>
                  <input className="input" value={loginForm.username} onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })} type="text" autoComplete="username" />
                </label>
                <label className="field-stack">
                  <span className="field-stack__label">Password</span>
                  <input className="input" value={loginForm.password} onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })} type="password" autoComplete="current-password" />
                </label>
                {loginError && <p style={{ margin: 0, color: 'var(--color-negative)' }}>{loginError}</p>}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
                  <button type="button" className="btn btn--ghost" onClick={() => setShowLogin(false)}>Cancel</button>
                  <button type="submit" className="btn btn--accent" disabled={authLoading}>Login</button>
                </div>
              </form>
            </div>
          </section>
        </div>
      )}
    </>
  )
}
